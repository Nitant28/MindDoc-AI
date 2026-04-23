"""
end_to_end_notice_resolution.py
Automates the journey from notice upload to compliance, draft response, filing, and tracking.
Integrates parsing, computation, LLM reasoning, report generation, evidence logging, and reminders.
"""

from app.services.notice_parser import parse_notice
from app.services.tax_computation import compute_tax, compliance_checklist
from app.services.deadline_manager import add_reminder
from app.services.report_generator import generate_report
from app.services.llm_reasoning import explain_compliance
from app.services.audit_evidence import log_action, store_evidence
from app.services.gov_portal_mock import fetch_case_status
from app.services.law_auto_update import fetch_latest_amendments
from datetime import datetime
from typing import Dict, Any


def resolve_notice(user_id: str, pdf_path: str, client: str = "-") -> Dict[str, Any]:
    # 1. Parse notice
    fields = parse_notice(pdf_path)
    fields["Client"] = client
    # 2. Compute tax/compliance
    computation = compute_tax(fields.get("DemandAmount"), fields.get("Sections")[0] if fields.get("Sections") else None)
    checklist = compliance_checklist(fields)
    # 3. LLM reasoning/advisory
    law_sections = ", ".join(fields.get("Sections", []))
    advisory = explain_compliance(fields, law_sections)
    # 4. Generate report
    report = generate_report(fields, computation, checklist, advisory)
    # 5. Log evidence
    with open(pdf_path, "rb") as f:
        store_evidence(user_id, f"notice_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf", f.read())
    log_action(user_id, "notice_resolved", {"fields": fields, "computation": computation, "advisory": advisory})
    # 6. Add reminder
    add_reminder("File response to notice", computation.get("Deadline", "-"), lambda: print(f"Reminder for {user_id}: File response!"))
    # 7. Fetch case status (mock)
    case_status = fetch_case_status(fields.get("PAN", "-"), fields.get("AssessmentYear", "-"))
    # 8. Fetch latest amendments
    amendments = fetch_latest_amendments()
    return {
        "fields": fields,
        "computation": computation,
        "checklist": checklist,
        "advisory": advisory,
        "report": report,
        "case_status": case_status,
        "amendments": amendments,
    }

# Example usage:
# result = resolve_notice("user1", "/path/to/notice.pdf", client="ACME Ltd.")
# print(result["report"])
