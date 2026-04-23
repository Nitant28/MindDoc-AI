"""
auto_learning_manager.py
Auto-learning modules: Interactive tutorials, quizzes, and simulations for law, tax, and compliance.
"""

from typing import Dict, List, Any

class AutoLearningManager:
    def __init__(self):
        self.tutorials: List[Dict[str, Any]] = []
        self.quizzes: List[Dict[str, Any]] = []
        self.simulations: List[Dict[str, Any]] = []

    def add_tutorial(self, title: str, content: str):
        self.tutorials.append({"title": title, "content": content})

    def add_quiz(self, title: str, questions: List[Dict[str, Any]]):
        self.quizzes.append({"title": title, "questions": questions})

    def add_simulation(self, title: str, scenario: str):
        self.simulations.append({"title": title, "scenario": scenario})

    def get_tutorials(self) -> List[Dict[str, Any]]:
        return self.tutorials

    def get_quizzes(self) -> List[Dict[str, Any]]:
        return self.quizzes

    def get_simulations(self) -> List[Dict[str, Any]]:
        return self.simulations

auto_learning_manager = AutoLearningManager()

# Example usage:
# auto_learning_manager.add_tutorial("Income Tax Basics", "Learn the fundamentals of income tax...")
# auto_learning_manager.add_quiz("GST Quiz", [{"q": "What is GST?", "a": "Goods and Services Tax"}])
# print(auto_learning_manager.get_tutorials())
