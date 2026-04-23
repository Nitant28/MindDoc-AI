"""
report_generator.py
Professional report and advisory generation for clients and compliance.
"""

from typing import Dict, Any
from datetime import datetime

REPORT_TEMPLATE = """
Compliance Report
=================
Client: {client}
PAN: {pan}
Assessment Year: {ay}
Notice Section(s): {sections}
Demand Amount: {demand}
Deadline: {deadline}

Tax Computation:
  Tax: {tax}
  Interest: {interest}
  Penalty: {penalty}

Checklist:
{checklist}

Advisory:
{advisory}

Generated on: {date}
"""

def generate_report(fields: Dict[str, Any], computation: Dict[str, Any], checklist: Dict[str, Any], advisory: str) -> str:
    return REPORT_TEMPLATE.format(
        client=fields.get("Client", "-"),
        pan=fields.get("PAN", "-"),
        ay=fields.get("AssessmentYear", "-"),
        sections=", ".join(fields.get("Sections", [])),
        demand=fields.get("DemandAmount", "-"),
        deadline=computation.get("Deadline", "-"),
        tax=computation.get("Tax", "-"),
        interest=computation.get("Interest", "-"),
        penalty=computation.get("Penalty", "-"),
        checklist="\n".join(f"- {k}: {v}" for k, v in checklist.items()),
        advisory=advisory,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )

# Example usage:
# print(generate_report(fields, computation, checklist, "Pay before deadline to avoid penalty."))
