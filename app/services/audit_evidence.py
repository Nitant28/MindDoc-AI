"""
audit_evidence.py
Audit trail and evidence locker for compliance actions and uploads.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

EVIDENCE_DIR = "evidence_locker"
os.makedirs(EVIDENCE_DIR, exist_ok=True)

def log_action(user_id: str, action: str, details: Dict[str, Any]):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details,
    }
    with open(os.path.join(EVIDENCE_DIR, f"{user_id}_audit.log"), "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def store_evidence(user_id: str, filename: str, filedata: bytes):
    path = os.path.join(EVIDENCE_DIR, f"{user_id}_{filename}")
    with open(path, "wb") as f:
        f.write(filedata)
    log_action(user_id, "upload_evidence", {"filename": filename})

# Example usage:
# log_action("user1", "file_notice", {"notice_id": "123"})
# store_evidence("user1", "notice.pdf", b"PDFDATA")
