"""
user_manager.py
User login, email-based reminders, deadlines, and record management.
"""

from typing import Dict, Any, List
from app.services.notification_manager import send_email

class UserManager:
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}  # email -> user info
        self.reminders: Dict[str, List[Dict[str, Any]]] = {}  # email -> reminders

    def register_user(self, email: str, info: Dict[str, Any]):
        self.users[email] = info

    def add_reminder(self, email: str, reminder: Dict[str, Any]):
        self.reminders.setdefault(email, []).append(reminder)
        send_email(email, "Reminder", reminder.get("message", ""))

    def get_user(self, email: str) -> Dict[str, Any]:
        return self.users.get(email, {})

    def get_reminders(self, email: str) -> List[Dict[str, Any]]:
        return self.reminders.get(email, [])

user_manager = UserManager()

# Example usage:
# user_manager.register_user("client@example.com", {"name": "Client"})
# user_manager.add_reminder("client@example.com", {"message": "Your deadline is tomorrow!"})
# print(user_manager.get_reminders("client@example.com"))
