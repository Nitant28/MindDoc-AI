import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    
    print(f"Testing OpenRouter with model: {model}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "How many r's are in the word 'strawberry'?"}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        data = response.json()
        print("Response received successfully!")
        print(f"Answer: {data['choices'][0]['message']['content']}")
        if "usage" in data:
            print(f"Usage: {data['usage']}")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_openrouter()
