"""
draft_generator.py
Automated draft response generation for notices using LLM.
"""

import openai
from typing import Dict, Any

OPENAI_MODEL = "gpt-4"

DRAFT_PROMPT = """
You are a professional CA. Draft a response to the following tax notice, referencing the relevant law sections and compliance actions. Use a formal, professional tone and structure the response for direct submission to the Income Tax Department.

Notice Fields:
{fields}

Law Sections:
{sections}

Checklist:
{checklist}
"""

def generate_draft_response(fields: Dict[str, Any], law_sections: str, checklist: Dict[str, Any]) -> str:
    prompt = DRAFT_PROMPT.format(fields=fields, sections=law_sections, checklist=checklist)
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=800,
        temperature=0.2,
    )
    return response.choices[0].message["content"]

# Example usage:
# print(generate_draft_response(fields, "Section 143(1)", checklist))
