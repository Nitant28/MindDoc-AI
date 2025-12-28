import requests
import os
from typing import Optional

class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def chat_completion(self, messages: list, model: str = "deepseek-chat", max_tokens: int = 1024, temperature: float = 0.7) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

def generate_with_deepseek(prompt: str, model: str = "deepseek-chat", max_tokens: int = 1024) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise Exception("DEEPSEEK_API_KEY not set")
    client = DeepSeekClient(api_key)
    messages = [{"role": "user", "content": prompt}]
    return client.chat_completion(messages, model, max_tokens)