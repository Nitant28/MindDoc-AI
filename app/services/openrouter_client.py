import os
import requests
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def generate_with_openrouter(prompt: str, model: str = None, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """
    Generate a response using OpenRouter API.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not found in environment")
        return ""

    model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://minddoc-ai.com", # Optional, for OpenRouter rankings
        "X-Title": "MindDoc AI", # Optional
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
            # Log usage if available
            if "usage" in data:
                logger.info(f"OpenRouter Usage: {data['usage']}")
            return content
        else:
            logger.warning(f"Unexpected OpenRouter response format: {data}")
            return ""
            
    except Exception as e:
        logger.error(f"OpenRouter call failed: {e}")
        return ""
