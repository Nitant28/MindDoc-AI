"""Model-agnostic LLM gateway.

One interface over Anthropic, OpenAI (and any OpenAI-compatible endpoint), Google Gemini,
NVIDIA NIM, DeepSeek and local Ollama. Providers are tried in ``LLM_PROVIDER_ORDER``; a failing
provider is skipped automatically (circuit-breaker style), so the app degrades instead of breaking.

Everything is plain HTTP via httpx, so no vendor SDK version drift can break the app.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NoLLMAvailable(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int


@dataclass
class StreamState:
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(self.text_parts)


@dataclass
class Image:
    data: bytes
    media_type: str = "image/png"

    @property
    def b64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name.upper()) or getattr(settings, name.lower(), default) or default


# --------------------------------------------------------------------------------------------
# Provider definitions
# --------------------------------------------------------------------------------------------

def _provider_config(name: str, fast: bool = False) -> Optional[dict]:
    """Return connection info for a provider, or None if it is not configured."""
    if name == "anthropic":
        key = _env("anthropic_api_key")
        if not key:
            return None
        model = _env("anthropic_fast_model") if fast else _env("anthropic_model")
        return {"kind": "anthropic", "key": key, "model": model, "url": "https://api.anthropic.com/v1/messages"}
    if name == "openai":
        key = _env("openai_api_key")
        if not key:
            return None
        base = (_env("openai_base_url") or "https://api.openai.com/v1").rstrip("/")
        return {"kind": "openai", "key": key, "model": _env("openai_model"), "url": f"{base}/chat/completions"}
    if name == "nvidia":
        key = os.getenv("NVIDIA_API_KEY", "")
        if not key:
            return None
        return {"kind": "openai", "key": key, "model": os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
                "url": "https://integrate.api.nvidia.com/v1/chat/completions"}
    if name == "deepseek":
        key = _env("deepseek_api_key")
        if not key:
            return None
        return {"kind": "openai", "key": key, "model": _env("deepseek_model"),
                "url": "https://api.deepseek.com/v1/chat/completions"}
    if name == "gemini":
        key = _env("gemini_api_key") or os.getenv("GOOGLE_API_KEY", "")
        if not key:
            return None
        return {"kind": "gemini", "key": key, "model": _env("gemini_model"),
                "url": "https://generativelanguage.googleapis.com/v1beta/models"}
    if name == "ollama":
        if not _ollama_alive():
            return None
        base = _env("ollama_api_url").split("/api/")[0]
        return {"kind": "ollama", "key": "", "model": os.getenv("OLLAMA_MODEL") or settings.ollama_model,
                "url": f"{base}/api/chat"}
    return None


_ollama_cache: dict = {"t": 0.0, "ok": False}


def _ollama_alive() -> bool:
    now = time.time()
    if now - _ollama_cache["t"] < 60:
        return _ollama_cache["ok"]
    base = _env("ollama_api_url").split("/api/")[0]
    try:
        ok = httpx.get(f"{base}/api/tags", timeout=1.0).status_code == 200
    except Exception:
        ok = False
    _ollama_cache.update(t=now, ok=ok)
    return ok


# Providers that recently failed are skipped for a cool-down window (simple circuit breaker).
_breaker: dict[str, float] = {}
_BREAKER_COOLDOWN_S = 60


def _breaker_open(name: str) -> bool:
    return time.time() - _breaker.get(name, 0) < _BREAKER_COOLDOWN_S


# --------------------------------------------------------------------------------------------
# Request builders
# --------------------------------------------------------------------------------------------

def _messages(prompt: str, history: Optional[list[dict]]) -> list[dict]:
    msgs = []
    for m in (history or [])[-8:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "content": str(m["content"])[:4000]})
    msgs.append({"role": "user", "content": prompt})
    return msgs


def _build_request(cfg: dict, prompt: str, system: Optional[str], history, max_tokens: int,
                   temperature: float, json_mode: bool, images: Optional[list[Image]], stream: bool):
    kind = cfg["kind"]
    msgs = _messages(prompt, history)

    if kind == "anthropic":
        if images:
            msgs[-1]["content"] = [
                *({"type": "image", "source": {"type": "base64", "media_type": im.media_type, "data": im.b64}} for im in images),
                {"type": "text", "text": prompt},
            ]
        body = {"model": cfg["model"], "max_tokens": max_tokens, "messages": msgs, "temperature": temperature}
        if system:
            body["system"] = system
        if stream:
            body["stream"] = True
        headers = {"x-api-key": cfg["key"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
        return cfg["url"], headers, body

    if kind == "openai":
        if images:
            msgs[-1]["content"] = [
                {"type": "text", "text": prompt},
                *({"type": "image_url", "image_url": {"url": f"data:{im.media_type};base64,{im.b64}"}} for im in images),
            ]
        if system:
            msgs.insert(0, {"role": "system", "content": system})
        body = {"model": cfg["model"], "messages": msgs, "max_tokens": max_tokens, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if stream:
            body["stream"] = True
        headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
        return cfg["url"], headers, body

    if kind == "gemini":
        contents = []
        for m in msgs:
            contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]})
        if images:
            contents[-1]["parts"] = [*({"inline_data": {"mime_type": im.media_type, "data": im.b64}} for im in images),
                                     {"text": prompt}]
        body = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature}}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        action = "streamGenerateContent?alt=sse" if stream else "generateContent"
        url = f"{cfg['url']}/{cfg['model']}:{action}"
        headers = {"x-goog-api-key": cfg["key"], "Content-Type": "application/json"}
        return url, headers, body

    if kind == "ollama":
        if system:
            msgs.insert(0, {"role": "system", "content": system})
        if images:
            msgs[-1]["images"] = [im.b64 for im in images]
        body = {"model": cfg["model"], "messages": msgs, "stream": stream,
                "options": {"temperature": temperature, "num_predict": max_tokens}}
        if json_mode:
            body["format"] = "json"
        return cfg["url"], {"Content-Type": "application/json"}, body

    raise ValueError(f"unknown provider kind {kind}")


def _parse_response(kind: str, data: dict) -> str:
    if kind == "anthropic":
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    if kind == "openai":
        return data["choices"][0]["message"]["content"] or ""
    if kind == "gemini":
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    if kind == "ollama":
        return data.get("message", {}).get("content", "")
    return ""


def _parse_stream_line(kind: str, line: str) -> Optional[str]:
    if kind == "ollama":
        try:
            obj = json.loads(line)
        except ValueError:
            return None
        return obj.get("message", {}).get("content") or None
    if not line.startswith("data:"):
        return None
    payload = line[5:].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        obj = json.loads(payload)
    except ValueError:
        return None
    if kind == "anthropic":
        if obj.get("type") == "content_block_delta":
            return obj.get("delta", {}).get("text")
        if obj.get("type") == "error":
            raise RuntimeError(obj.get("error", {}).get("message", "anthropic stream error"))
        return None
    if kind == "openai":
        choices = obj.get("choices") or [{}]
        return (choices[0].get("delta") or {}).get("content")
    if kind == "gemini":
        parts = (obj.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts) or None
    return None


# --------------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------------

def _candidates(fast: bool, need_vision: bool = False):
    order = settings.provider_order
    if "nvidia" not in order and os.getenv("NVIDIA_API_KEY"):
        order = order + ["nvidia"]
    for name in order:
        if _breaker_open(name):
            continue
        if need_vision and name in ("deepseek",):
            continue
        cfg = _provider_config(name, fast=fast)
        if cfg:
            yield name, cfg


KNOWN_PROVIDERS = ("anthropic", "openai", "gemini", "nvidia", "deepseek", "ollama")


def available_providers() -> list[dict]:
    out = []
    names = [n for n in dict.fromkeys(settings.provider_order + list(KNOWN_PROVIDERS)) if n in KNOWN_PROVIDERS]
    for name in names:
        cfg = _provider_config(name)
        out.append({"name": name, "available": bool(cfg) and name in settings.provider_order + ["nvidia"],
                    "model": cfg["model"] if cfg else None, "cooling_down": _breaker_open(name)})
    return out


def has_llm() -> bool:
    return any(True for _ in _candidates(fast=False))


def has_vision_llm() -> bool:
    return any(True for _ in _candidates(fast=False, need_vision=True))


def generate(prompt: str, system: Optional[str] = None, *, history: Optional[list[dict]] = None,
             max_tokens: int = 1500, temperature: float = 0.2, json_mode: bool = False, fast: bool = False,
             images: Optional[list[Image]] = None) -> LLMResult:
    errors = []
    for name, cfg in _candidates(fast, need_vision=bool(images)):
        url, headers, body = _build_request(cfg, prompt, system, history, max_tokens, temperature,
                                            json_mode, images, stream=False)
        t0 = time.perf_counter()
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=settings.llm_timeout_s)
            r.raise_for_status()
            text = _parse_response(cfg["kind"], r.json())
            if not text.strip():
                raise RuntimeError("empty completion")
            return LLMResult(text=text, provider=name, model=cfg["model"],
                             latency_ms=int((time.perf_counter() - t0) * 1000))
        except Exception as e:  # try the next provider
            detail = getattr(getattr(e, "response", None), "text", "")[:300]
            logger.warning("LLM provider %s failed: %s %s", name, e, detail)
            errors.append(f"{name}: {e}")
            _breaker[name] = time.time()
    raise NoLLMAvailable("; ".join(errors) or "no LLM provider configured")


def stream(prompt: str, system: Optional[str] = None, *, history: Optional[list[dict]] = None,
           max_tokens: int = 1500, temperature: float = 0.2, fast: bool = False,
           state: Optional[StreamState] = None) -> Iterator[str]:
    """Yield text deltas. Falls over to the next provider only if nothing was emitted yet."""
    state = state if state is not None else StreamState()
    errors = []
    for name, cfg in _candidates(fast):
        url, headers, body = _build_request(cfg, prompt, system, history, max_tokens, temperature,
                                            False, None, stream=True)
        t0 = time.perf_counter()
        emitted = False
        try:
            with httpx.stream("POST", url, headers=headers, json=body, timeout=settings.llm_timeout_s) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    delta = _parse_stream_line(cfg["kind"], line)
                    if delta:
                        emitted = True
                        state.text_parts.append(delta)
                        yield delta
            state.provider, state.model = name, cfg["model"]
            state.latency_ms = int((time.perf_counter() - t0) * 1000)
            if emitted:
                return
            raise RuntimeError("empty stream")
        except Exception as e:
            logger.warning("LLM stream provider %s failed: %s", name, e)
            errors.append(f"{name}: {e}")
            _breaker[name] = time.time()
            if emitted:  # partial answer already shown to the user; stop here
                state.provider, state.model = name, cfg["model"]
                return
    raise NoLLMAvailable("; ".join(errors) or "no LLM provider configured")


_JSON_RE = re.compile(r"\{.*\}|\[.*\]", re.S)


def parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        m = _JSON_RE.search(text)
        if m:
            return json.loads(m.group(0))
        raise


def generate_json(prompt: str, system: Optional[str] = None, *, max_tokens: int = 1500, fast: bool = True):
    """Generate and parse a JSON object. Retries once with a repair instruction."""
    res = generate(prompt, system, max_tokens=max_tokens, temperature=0.0, json_mode=True, fast=fast)
    try:
        return parse_json(res.text), res
    except ValueError:
        res2 = generate(f"Return ONLY valid JSON, no prose. Fix this into valid JSON:\n{res.text[:6000]}",
                        max_tokens=max_tokens, temperature=0.0, json_mode=True, fast=True)
        return parse_json(res2.text), res2
