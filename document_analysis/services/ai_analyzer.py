import os
from typing import Dict, Optional
import json

try:
    from groq import Groq
except ImportError:
    Groq = None

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if Groq and api_key:
            try:
                self.client = Groq(api_key=api_key)
            except Exception:
                self.client = None
        self.model = "mixtral-8x7b-32768"

    def analyze(self, text: str) -> Optional[Dict]:
        if not self.client:
            return None
        prompt = f"""
Analyze the following document text and extract the following information in JSON format:

- summary: A concise summary of the document (max 300 words)
- key_entities: 
  - names: List of person names mentioned
  - dates: List of dates mentioned
  - amounts: List of monetary amounts mentioned
- important_clauses: List of important clauses or sections (max 5)
- risk_flags: List of potential risks or issues (like penalties, missing data) (max 5)
- confidence_score: A float between 0 and 1 indicating confidence in the analysis

Return only valid JSON.

Document text:
{text}
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                max_tokens=2000
            )
            content = response.choices[0].message.content.strip()
            # Try to parse JSON
            result = json.loads(content)
            # Validate structure
            if all(key in result for key in ["summary", "key_entities", "important_clauses", "risk_flags", "confidence_score"]):
                return result
            else:
                return None
        except Exception as e:
            print(f"AI Analysis failed: {e}")
            return None