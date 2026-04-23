"""
collaboration_manager.py
Multi-entity, multi-user, multi-role collaboration for CA firms.
"""

from typing import Dict, List, Any
from app.services.user_client_manager import client_manager

class CollaborationManager:
    def __init__(self):
        self.teams: Dict[str, List[str]] = {}  # team_id -> [user_ids]
        self.roles: Dict[str, str] = {}        # user_id -> role (admin, staff, reviewer, etc.)

    def add_team(self, team_id: str, user_ids: List[str]):
        self.teams[team_id] = user_ids

    def assign_role(self, user_id: str, role: str):
        self.roles[user_id] = role

    def get_team_users(self, team_id: str) -> List[str]:
        return self.teams.get(team_id, [])

    def get_user_role(self, user_id: str) -> str:
        return self.roles.get(user_id, "user")

collab_manager = CollaborationManager()

# Example usage:
# collab_manager.add_team("team1", ["user1", "user2"])
# collab_manager.assign_role("user1", "admin")
# print(collab_manager.get_team_users("team1"))
# print(collab_manager.get_user_role("user1"))
