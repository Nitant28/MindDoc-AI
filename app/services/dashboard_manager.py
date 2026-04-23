"""
dashboard_manager.py
Interactive dashboard logic for compliance, deadlines, and client management.
"""

from typing import Dict, List, Any
import pandas as pd

class DashboardManager:
    def __init__(self):
        self.compliance_data: List[Dict[str, Any]] = []
        self.deadline_data: List[Dict[str, Any]] = []
        self.client_data: List[Dict[str, Any]] = []

    def add_compliance_record(self, record: Dict[str, Any]):
        self.compliance_data.append(record)

    def add_deadline(self, deadline: Dict[str, Any]):
        self.deadline_data.append(deadline)

    def add_client(self, client: Dict[str, Any]):
        self.client_data.append(client)

    def get_dashboard(self) -> Dict[str, Any]:
        return {
            "compliance": pd.DataFrame(self.compliance_data).to_dict(orient="records"),
            "deadlines": pd.DataFrame(self.deadline_data).to_dict(orient="records"),
            "clients": pd.DataFrame(self.client_data).to_dict(orient="records"),
        }

dashboard_manager = DashboardManager()

# Example usage:
# dashboard_manager.add_compliance_record({"user": "user1", "status": "pending", "section": "143(1)"})
# print(dashboard_manager.get_dashboard())
