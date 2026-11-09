"""Responsible-AI guardrails.

- PII detection & redaction (emails, phones, cards with Luhn check, SSN, IBAN, IPs, India PAN/Aadhaar)
- Indirect prompt-injection detection in uploaded documents (OWASP LLM01) and sanitisation of
  retrieved context, so a malicious PDF cannot hijack the assistant.
"""
from __future__ import annotations

import re
from collections import Counter

PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "PHONE": re.compile(r"(?<![\w-])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?|\d{2,4}[\s.-])\d{3,4}[\s.-]\d{3,4}(?![\w-])"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "SSN": re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b"),
    "IP_ADDRESS": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "PAN_IN": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "AADHAAR_IN": re.compile(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b"),
}


def _luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_pii(text: str) -> list[tuple[str, int, int]]:
    spans = []
    for kind, pat in PII_PATTERNS.items():
        for m in pat.finditer(text):
            if kind == "CREDIT_CARD" and not _luhn_ok(m.group()):
                continue
            if kind == "PHONE":
                # reject if part of a longer digit run (card/account numbers), or too few digits
                s, e = m.start(), m.end()
                while s > 0 and (text[s - 1].isdigit() or text[s - 1] in " -."):
                    s -= 1
                while e < len(text) and (text[e].isdigit() or text[e] in " -."):
                    e += 1
                run_digits = sum(c.isdigit() for c in text[s:e])
                if sum(c.isdigit() for c in m.group()) < 9 or run_digits > 13:
                    continue
            spans.append((kind, m.start(), m.end()))
    spans.sort(key=lambda s: (s[1], -(s[2] - s[1])))
    merged, last_end = [], -1
    for s in spans:  # drop overlaps (keep the earliest/longest match)
        if s[1] >= last_end:
            merged.append(s)
            last_end = s[2]
    return merged


def pii_summary(text: str) -> dict:
    spans = find_pii(text)
    return {"count": len(spans), "types": dict(Counter(k for k, _, _ in spans))}


def redact(text: str) -> str:
    out, pos = [], 0
    for kind, s, e in find_pii(text):
        out.append(text[pos:s])
        out.append(f"[{kind}]")
        pos = e
    out.append(text[pos:])
    return "".join(out)


INJECTION_PATTERNS = [
    (r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|prompts|messages)", "high"),
    (r"disregard (?:all |the )?(?:previous|prior|above|system) (?:instructions|prompt)", "high"),
    (r"(?:reveal|print|show|leak) (?:your |the )?(?:system prompt|hidden instructions|api key)", "high"),
    (r"you are now (?:a|an|in) ", "medium"),
    (r"(?:new|updated) (?:system )?instructions\s*:", "medium"),
    (r"do not (?:tell|inform|mention to) the user", "high"),
    (r"<\s*/?\s*(?:system|assistant|instructions?)\s*>", "medium"),
    (r"\b(?:BEGIN|END) (?:SYSTEM|PROMPT|INSTRUCTIONS)\b", "medium"),
    (r"(?:send|exfiltrate|post) (?:the |all )?(?:data|conversation|documents?) to https?://", "high"),
    (r"!\[[^\]]*\]\(https?://[^)]*\?(?:q|data|d)=", "high"),  # markdown-image exfiltration
]
_INJ = [(re.compile(p, re.I), sev) for p, sev in INJECTION_PATTERNS]


def detect_injection(text: str, max_flags: int = 10) -> list[dict]:
    flags = []
    for pat, sev in _INJ:
        for m in pat.finditer(text):
            s = max(0, m.start() - 60)
            flags.append({"type": "prompt_injection", "severity": sev,
                          "snippet": text[s:m.end() + 60].replace("\n", " ").strip()})
            if len(flags) >= max_flags:
                return flags
    return flags


def sanitize_context(text: str) -> str:
    """Neutralise instruction-like spans inside retrieved document text."""
    for pat, _ in _INJ:
        text = pat.sub(lambda m: f"[neutralised instruction: {m.group()[:40]}]", text)
    return text
