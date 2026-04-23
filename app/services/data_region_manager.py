"""
data_region_manager.py
Multi-region data storage and residency logic.
"""

from typing import Dict, Any

class DataRegionManager:
    def __init__(self):
        self.regions = ["India", "EU", "US"]
        self.user_region: Dict[str, str] = {}

    def set_region(self, user_id: str, region: str):
        if region in self.regions:
            self.user_region[user_id] = region

    def get_region(self, user_id: str) -> str:
        return self.user_region.get(user_id, "India")

    def store_data(self, user_id: str, data: Any):
        region = self.get_region(user_id)
        print(f"Storing data for {user_id} in {region} region.")
        # Integrate with cloud storage APIs for region
        return True

data_region_manager = DataRegionManager()

# Example usage:
# data_region_manager.set_region("user1", "EU")
# data_region_manager.store_data("user1", {"file": "notice.pdf"})
