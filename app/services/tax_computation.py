"""
tax_computation.py
Automated tax computation and compliance workflow logic.
Calculates tax, interest, penalty, deadlines, and generates compliance checklists.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Example tax rates and penalty rules (should be loaded from law DB/config)
TAX_RATES = {
    "default": 0.3,  # 30% for demonstration
}
INTEREST_RATE = 0.012,  # 1.2% per month
PENALTY_FLAT = 5000


def compute_tax(demand_amount: Optional[str], section: Optional[str]) -> Dict[str, Any]:
    """Compute tax, interest, penalty, and deadlines."""
    result = {}
    try:
        amount = float(demand_amount.replace(",", "")) if demand_amount else 0
    except Exception:
        amount = 0
    tax = amount * TAX_RATES.get(section, TAX_RATES["default"])
    interest = amount * INTEREST_RATE[0]
    penalty = PENALTY_FLAT if amount > 0 else 0
    deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result.update({
        "Tax": round(tax, 2),
        "Interest": round(interest, 2),
        "Penalty": penalty,
        "Deadline": deadline,
    })
    return result


def compliance_checklist(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a compliance checklist based on extracted fields."""
    checklist = {
        "PAN Verified": bool(fields.get("PAN")),
        "Assessment Year Present": bool(fields.get("AssessmentYear")),
        "Demand Amount Present": bool(fields.get("DemandAmount")),
        "Section(s) Referenced": bool(fields.get("Sections")),
        "Deadline(s) Detected": bool(fields.get("Dates")),
    }
    return checklist

# Example usage:
# fields = parse_notice("/path/to/notice.pdf")
# result = compute_tax(fields["DemandAmount"], fields["Sections"][0] if fields["Sections"] else None)
# print(result)
# print(compliance_checklist(fields))
