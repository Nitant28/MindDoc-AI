"""
gamification_manager.py
Gamification: Achievements, badges, and leaderboards for compliance actions and learning.
"""

from typing import Dict, List, Any

class GamificationManager:
    def __init__(self):
        self.achievements: Dict[str, List[str]] = {}  # user_id -> [achievements]
        self.leaderboard: Dict[str, int] = {}         # user_id -> points

    def add_achievement(self, user_id: str, achievement: str):
        self.achievements.setdefault(user_id, []).append(achievement)
        self.leaderboard[user_id] = self.leaderboard.get(user_id, 0) + 10

    def get_leaderboard(self) -> Dict[str, int]:
        return dict(sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True))

gamification_manager = GamificationManager()

# Example usage:
# gamification_manager.add_achievement("user1", "Filed first notice")
# print(gamification_manager.get_leaderboard())
