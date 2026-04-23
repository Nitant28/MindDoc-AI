"""
client_portal.py
Client self-service portal logic for uploads, status, and reports.
"""

from typing import Dict, Any, List

class ClientPortal:
    def __init__(self):
        self.uploads: Dict[str, List[str]] = {}  # client_id -> [file paths]
        self.status: Dict[str, Any] = {}         # client_id -> status info
        self.reports: Dict[str, List[str]] = {}  # client_id -> [report paths]

    def upload_notice(self, client_id: str, file_path: str):
        self.uploads.setdefault(client_id, []).append(file_path)

    def set_status(self, client_id: str, status: Any):
        self.status[client_id] = status

    def add_report(self, client_id: str, report_path: str):
        self.reports.setdefault(client_id, []).append(report_path)

    def get_portal(self, client_id: str) -> Dict[str, Any]:
        return {
            "uploads": self.uploads.get(client_id, []),
            "status": self.status.get(client_id, {}),
            "reports": self.reports.get(client_id, []),
        }

client_portal = ClientPortal()

# Example usage:
# client_portal.upload_notice("clientA", "/path/to/notice.pdf")
# client_portal.set_status("clientA", {"compliance": "pending"})
# print(client_portal.get_portal("clientA"))
