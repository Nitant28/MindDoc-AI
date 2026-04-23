"""
llm_reasoning.py
Enhanced LLM explainability and reasoning logic for tax compliance.
"""

from typing import Dict, Any
import openai
import markdown2
from tabulate import tabulate

OPENAI_MODEL = "gpt-4"

EXPLAIN_PROMPT = """
You are a professional Chartered Accountant and tax compliance expert.
Given the following extracted fields from a tax notice and law sections, respond in a highly structured format:

### Section Applicability
- For each law section, explain why it applies in bullet points.

### Required Actions
- List all compliance actions as bullet points, grouped by topic.

### Best Practices & Tips
- Provide actionable best practices and compliance tips as bullet points.

### Relevant Case Laws
- Cite relevant case laws, each with a short summary and bullet points.

### Summary Table
- End with a summary table of key deadlines, penalties, and payment instructions.

Fields:
{fields}

Law Sections:
{sections}

Respond in a clear, actionable, and professional manner. Use markdown headings, bullet points, and tables for readability.
"""

def explain_compliance(fields: Dict[str, Any], law_sections: str) -> str:
    prompt = EXPLAIN_PROMPT.format(fields=fields, sections=law_sections)
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=1200,
        temperature=0.2,
    )
    raw = response.choices[0].message["content"]
    # Convert markdown to HTML for frontend, keep markdown for API
    html = markdown2.markdown(raw)
    # Optionally, extract summary table and format with tabulate
    # (Assume summary table is in markdown table format)
    return raw  # For API, return markdown for best readability

# Example usage:
# print(explain_compliance(fields, "Section 143(1), Section 234A"))
