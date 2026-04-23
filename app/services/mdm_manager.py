"""
mdm_manager.py
Mobile Device Management (MDM) support for enterprise control.
"""

from typing import Dict, Any, List

class MDMManager:
    def __init__(self):
        self.devices: List[Dict[str, Any]] = []

    def register_device(self, user_id: str, device_info: Dict[str, Any]):
        self.devices.append({"user_id": user_id, **device_info})
        print(f"Device registered for {user_id}: {device_info}")

    def get_devices(self, user_id: str) -> List[Dict[str, Any]]:
        return [d for d in self.devices if d["user_id"] == user_id]

mdm_manager = MDMManager()

# Example usage:
# mdm_manager.register_device("user1", {"device_id": "abc123", "type": "Android"})
# print(mdm_manager.get_devices("user1"))
