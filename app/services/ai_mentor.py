"""
ai_mentor.py
AI-powered mentor/advisor for personalized guidance, study tips, and career advice.
"""

import openai
from typing import Dict, Any

OPENAI_MODEL = "gpt-4"

MENTOR_PROMPT = """
You are an expert mentor for law, tax, and compliance students and professionals. Provide personalized guidance, study tips, and career advice based on the user's profile and goals.

User Profile:
{profile}

Goals:
{goals}

Respond with actionable advice, resources, and encouragement.
"""

def get_mentor_advice(profile: Dict[str, Any], goals: str) -> str:
    prompt = MENTOR_PROMPT.format(profile=profile, goals=goals)
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=600,
        temperature=0.7,
    )
    return response.choices[0].message["content"]

# Example usage:
# print(get_mentor_advice({"name": "Shubh", "interest": "Income Tax"}, "Become a top CA"))
