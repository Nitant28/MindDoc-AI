"""
community_qa_manager.py
Community Q&A: In-app forum for compliance, law, and tax topics.
"""

from typing import List, Dict, Any

class CommunityQAManager:
    def __init__(self):
        self.questions: List[Dict[str, Any]] = []
        self.answers: List[Dict[str, Any]] = []

    def post_question(self, user_id: str, question: str):
        self.questions.append({"user_id": user_id, "question": question})

    def post_answer(self, user_id: str, question_idx: int, answer: str):
        self.answers.append({"user_id": user_id, "question_idx": question_idx, "answer": answer})

    def get_questions(self) -> List[Dict[str, Any]]:
        return self.questions

    def get_answers(self, question_idx: int) -> List[Dict[str, Any]]:
        return [a for a in self.answers if a["question_idx"] == question_idx]

community_qa_manager = CommunityQAManager()

# Example usage:
# community_qa_manager.post_question("user1", "How to file a GST return?")
# community_qa_manager.post_answer("user2", 0, "Use the GST portal and follow these steps...")
# print(community_qa_manager.get_questions())
# print(community_qa_manager.get_answers(0))
