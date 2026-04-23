import os
import shutil
import subprocess
import requests
import json
import logging

logger = logging.getLogger(__name__)


def _resolve_tags_url(api_url: str) -> str:
    api_url = api_url.rstrip('/')
    if api_url.endswith('/api/generate'):
        return api_url[:-len('/api/generate')] + '/api/tags'
    if api_url.endswith('/generate'):
        return api_url[:-len('/generate')] + '/tags'
    return api_url + '/api/tags'


def _get_available_models(api_url: str, timeout: int = 2) -> list:
    tags_url = _resolve_tags_url(api_url)
    try:
        response = requests.get(tags_url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and 'models' in data and isinstance(data['models'], list):
            return [m.get('name') for m in data['models'] if isinstance(m, dict) and 'name' in m]
        if isinstance(data, list):
            return [m.get('name') for m in data if isinstance(m, dict) and 'name' in m]
    except Exception as e:
        logger.debug('Failed to fetch available Ollama models from %s: %s', tags_url, e)
    return []


def _http_generate(prompt: str, model: str, max_tokens: int = 512, temperature: float = 0.4, timeout: int = 120, api_url: str | None = None) -> str:
    api_url = api_url or os.environ.get('OLLAMA_API_URL', 'http://127.0.0.1:11434/api/generate')
    payload = {
        'model': model,
        'prompt': prompt,
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    try:
        # Ollama may stream newline-delimited JSON objects. Try normal JSON first,
        # otherwise accumulate streamed responses.
        r = requests.post(api_url, json=payload, timeout=timeout, stream=True)
        r.raise_for_status()
        try:
            j = r.json()
            if isinstance(j, dict):
                if 'text' in j:
                    return j['text']
                if 'choices' in j and isinstance(j['choices'], list) and len(j['choices']) > 0:
                    c = j['choices'][0]
                    return c.get('text') or c.get('message', {}).get('content', '')
            return str(j)
        except ValueError:
            # Streamed NDJSON: combine `response` fields in order
            parts = []
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    # not a JSON line, append raw
                    parts.append(line)
                    continue
                # Ollama stream uses `response` or `thinking`, with `done`/`done_reason`
                if isinstance(obj, dict):
                    if 'response' in obj and obj.get('response'):
                        parts.append(obj.get('response', ''))
                    elif 'thinking' in obj and obj.get('thinking'):
                        parts.append(obj.get('thinking', ''))
                    elif 'text' in obj and obj.get('text'):
                        parts.append(obj.get('text', ''))
                if obj.get('done'):
                    break
            output = ''.join(parts).strip()
            return output if output else ''
    except Exception as e:
        logger.debug('HTTP ollama generate failed: %s', e)
        raise


def _cli_generate(prompt: str, model: str, max_tokens: int = 512, temperature: float = 0.4, timeout: int = 120) -> str:
    # Prefer `ollama` on PATH
    exe = shutil.which('ollama')
    if not exe:
        # Look for a local ollama.exe in repo root or current directory
        possible = [os.path.join(os.getcwd(), 'ollama.exe'), os.path.join(os.getcwd(), 'ollama', 'ollama.exe')]
        for p in possible:
            if os.path.exists(p):
                exe = p
                break
    if not exe:
        raise FileNotFoundError('ollama executable not found on PATH or project')

    # Try a few CLI invocation variants; capture stdout
    cmds = [
        [exe, 'generate', model, '--prompt', prompt, '--json'],
        [exe, 'generate', model, '--prompt', prompt],
        [exe, 'run', model, '--prompt', prompt],
    ]
    for cmd in cmds:
        try:
            p = subprocess.run(cmd, input=None, capture_output=True, text=True, timeout=timeout)
            out = (p.stdout or p.stderr or '').strip()
            if p.returncode == 0 and out:
                # try to parse json
                try:
                    j = json.loads(out)
                    if isinstance(j, dict):
                        if 'text' in j:
                            return j['text']
                        if 'choices' in j and len(j['choices']) > 0:
                            return j['choices'][0].get('text', '')
                    # fallback to raw
                    return out
                except Exception:
                    return out
        except Exception as e:
            logger.debug('CLI ollama attempt failed (%s): %s', cmd, e)
            continue

    raise RuntimeError('All ollama CLI attempts failed')


def generate_with_ollama(prompt: str, model: str = 'gpt-oss:120b-cloud', max_tokens: int = 512, temperature: float = 0.4, timeout: int = 120) -> str:
    # Default model can be overridden via OLLAMA_MODEL env var or function arg
    api_url = os.environ.get('OLLAMA_API_URL', 'http://127.0.0.1:11434/api/generate')
    model = model or os.environ.get('OLLAMA_MODEL', 'gpt-oss:120b-cloud')

    available_models = _get_available_models(api_url)
    if available_models:
        if model not in available_models:
            logger.warning('Configured Ollama model %s is not available. Falling back to first available model: %s', model, available_models[0])
            model = available_models[0]
        else:
            logger.debug('Configured Ollama model %s is available', model)
    else:
        logger.debug('Could not retrieve available Ollama models from %s; using configured model %s', api_url, model)

    # Try HTTP API first (recommended if `ollama serve` is running)
    try:
        return _http_generate(prompt, model, max_tokens=max_tokens, temperature=temperature, timeout=timeout, api_url=api_url)
    except Exception as e:
        logger.warning('HTTP generate failed, falling back to CLI: %s', e)
    # Then try CLI
    return _cli_generate(prompt, model, max_tokens=max_tokens, temperature=temperature, timeout=timeout)

    # Then try CLI
    try:
        return _cli_generate(prompt, model, max_tokens=max_tokens, timeout=timeout)
    except Exception as e:
        logger.exception('Ollama generation failed: %s', e)
        raise

def verify_ollama_available() -> bool:
    """Check if Ollama is available via HTTP API or CLI"""
    api_url = os.environ.get('OLLAMA_API_URL', 'http://127.0.0.1:11434/api/tags')
    
    # Try HTTP first - check /api/tags endpoint
    try:
        r = requests.get(api_url, timeout=2)
        if r.status_code == 200:
            logger.info("Ollama HTTP API is available")
            return True
    except Exception as e:
        logger.debug(f"Ollama HTTP check failed: {e}")
    
    # Try CLI
    try:
        exe = shutil.which('ollama')
        if exe:
            p = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=2)
            if p.returncode == 0:
                logger.info("Ollama CLI is available")
                return True
    except Exception as e:
        logger.debug(f"Ollama CLI check failed: {e}")
    
    return False