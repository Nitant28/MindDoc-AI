"""
role_access_manager.py
Granular role-based access and audit controls for users and staff.
"""

from typing import Dict, List

class RoleAccessManager:
    def __init__(self):
        self.roles: Dict[str, str] = {}  # user_id -> role
        self.permissions: Dict[str, List[str]] = {}  # role -> [permissions]

    def assign_role(self, user_id: str, role: str):
        self.roles[user_id] = role

    def set_permissions(self, role: str, perms: List[str]):
        self.permissions[role] = perms

    def check_access(self, user_id: str, perm: str) -> bool:
        role = self.roles.get(user_id, "user")
        return perm in self.permissions.get(role, [])

role_access_manager = RoleAccessManager()

# Example usage:
# role_access_manager.assign_role("user1", "admin")
# role_access_manager.set_permissions("admin", ["view_dashboard", "edit_client"])
# print(role_access_manager.check_access("user1", "edit_client"))
