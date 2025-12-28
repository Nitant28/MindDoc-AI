import os
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LocalLLM:
    """A thin local LLM wrapper supporting Hugging Face transformers and optional llama.cpp backend.

    Usage:
      llm = LocalLLM(model_name=os.environ.get('LOCAL_LLM_MODEL', 'gpt2-medium'))
      llm.load()
      text = llm.generate('Hello')
    """

    def __init__(self, model_name: Optional[str] = None, model_path: Optional[str] = None, device: str = 'cpu'):
        self.model_name = model_name or os.environ.get('LOCAL_LLM_MODEL', 'gpt2-medium')
        self.model_path = model_path or os.environ.get('LOCAL_LLM_PATH')
        self.device = device
        self._lock = threading.Lock()
        self._loaded = False
        self._backend = None
        self._model = None
        self._tokenizer = None
        self._pipeline = None

    def load(self):
        with self._lock:
            if self._loaded:
                return

            try:
                # Prefer llama.cpp backend if available and a ggml model path provided
                if self.model_path and self.model_path.lower().endswith('.ggml'):
                    try:
                        from llama_cpp import Llama

                        logger.info('Loading llama.cpp model from %s', self.model_path)
                        self._model = Llama(model_path=self.model_path)
                        self._backend = 'llama_cpp'
                        self._loaded = True
                        return
                    except Exception:
                        logger.info('llama.cpp not available or failed, falling back to transformers')

                # Transformers backend
                from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

                logger.info('Loading transformers model %s', self.model_name)
                # If a local path exists, prefer it
                model_source = self.model_path or self.model_name
                self._tokenizer = AutoTokenizer.from_pretrained(model_source, use_fast=True)
                model = AutoModelForCausalLM.from_pretrained(model_source)
                # Create text-generation pipeline
                self._pipeline = pipeline('text-generation', model=model, tokenizer=self._tokenizer, device_map='cpu')
                self._backend = 'transformers'
                self._loaded = True
            except Exception as e:
                logger.exception('Failed to load any local LLM backend: %s', e)
                raise

    def generate(self, prompt: str, max_new_tokens: int = 128, **kwargs) -> str:
        if not self._loaded:
            self.load()

        if self._backend == 'llama_cpp':
            # llama.cpp Llama instance generate
            try:
                out = self._model.create(prompt=prompt, max_tokens=max_new_tokens)
                return out.get('content') or out.get('text', '')
            except Exception:
                logger.exception('llama_cpp generation failed')
                raise

        if self._backend == 'transformers':
            try:
                out = self._pipeline(prompt, max_new_tokens=max_new_tokens, do_sample=True, **kwargs)
                if isinstance(out, list) and len(out) > 0 and 'generated_text' in out[0]:
                    return out[0]['generated_text']
                return str(out)
            except Exception:
                logger.exception('transformers generation failed')
                raise

        raise RuntimeError('No LLM backend loaded')


# Module-level singleton convenience
_SINGLETON: Optional[LocalLLM] = None


def get_local_llm() -> LocalLLM:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = LocalLLM()
    return _SINGLETON
from typing import Optional

_model = None
_tokenizer = None
_pipeline = None

def load_model(model_name: str = "gpt2-medium"):
    global _model, _tokenizer, _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch
    except Exception as e:
        raise RuntimeError(f"transformers/torch not installed: {e}")
    # Use CPU pipeline; model weights will be downloaded if not present
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _model = AutoModelForCausalLM.from_pretrained(model_name)
    _pipeline = pipeline("text-generation", model=_model, tokenizer=_tokenizer, device=-1)
    return _pipeline


def generate(prompt: str, max_new_tokens: int = 64) -> str:
    p = load_model()
    out = p(prompt, max_new_tokens=max_new_tokens, do_sample=False)
    if isinstance(out, list) and len(out) > 0:
        return out[0].get('generated_text', out[0].get('text', str(out[0])))
    return str(out)
