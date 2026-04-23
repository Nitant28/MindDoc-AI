"""
ai_document_summarizer.py
AI-powered document summarizer for notices, laws, and reports.
"""

import openai
from typing import Dict, Any

OPENAI_MODEL = "gpt-4"

SUMMARIZE_PROMPT = """
Summarize the following document in clear, concise bullet points and headings for easy understanding.

Document:
{document}
"""

def summarize_document(document: str) -> str:
    prompt = SUMMARIZE_PROMPT.format(document=document)
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].message["content"]

# Example usage:
# print(summarize_document("Income Tax Act Section 143(1)..."))
