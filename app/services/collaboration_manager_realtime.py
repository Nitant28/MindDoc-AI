"""
collaboration_manager_realtime.py
Real-time collaboration: Multiple users work on the same case, chat, and resolve together.
"""

from typing import Dict, List, Any

class CollaborationManagerRealtime:
    def __init__(self):
        self.sessions: Dict[str, List[str]] = {}  # case_id -> [user_ids]
        self.chats: Dict[str, List[str]] = {}     # case_id -> chat messages

    def join_session(self, case_id: str, user_id: str):
        self.sessions.setdefault(case_id, []).append(user_id)

    def send_message(self, case_id: str, user_id: str, message: str):
        self.chats.setdefault(case_id, []).append(f"{user_id}: {message}")

    def get_chat(self, case_id: str) -> List[str]:
        return self.chats.get(case_id, [])

collaboration_manager_realtime = CollaborationManagerRealtime()

# Example usage:
# collaboration_manager_realtime.join_session("case123", "user1")
# collaboration_manager_realtime.send_message("case123", "user1", "Let's resolve this notice together!")
# print(collaboration_manager_realtime.get_chat("case123"))
