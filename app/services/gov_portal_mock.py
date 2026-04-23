"""
gov_portal_mock.py
Mock/demo integration with government portals (Income Tax, GST, MCA).
"""

import random
from typing import Dict, Any

def fetch_case_status(pan: str, ay: str) -> Dict[str, Any]:
    """Mock fetching case status from e-filing portal."""
    statuses = ["Pending", "Resolved", "Under Review", "Action Required"]
    return {
        "PAN": pan,
        "AssessmentYear": ay,
        "Status": random.choice(statuses),
        "LastUpdated": "2026-03-06",
    }

def fetch_gst_status(gstin: str) -> Dict[str, Any]:
    statuses = ["Active", "Suspended", "Cancelled"]
    return {
        "GSTIN": gstin,
        "Status": random.choice(statuses),
        "LastUpdated": "2026-03-06",
    }

# Example usage:
# print(fetch_case_status("ABCDE1234F", "2025-26"))
# print(fetch_gst_status("22AAAAA0000A1Z5"))
