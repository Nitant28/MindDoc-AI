import re
from typing import List, Dict

class FallbackAnalyzer:
    def analyze(self, text: str) -> Dict:
        names = self._extract_names(text)
        dates = self._extract_dates(text)
        amounts = self._extract_amounts(text)
        clauses = self._extract_clauses(text)
        risk_flags = self._extract_risks(text)
        summary = self._generate_summary(text)
        confidence = 0.5  # Lower confidence for fallback

        return {
            "summary": summary,
            "key_entities": {
                "names": names,
                "dates": dates,
                "amounts": amounts
            },
            "important_clauses": clauses,
            "risk_flags": risk_flags,
            "confidence_score": confidence
        }

    def _extract_names(self, text: str) -> List[str]:
        # Simple regex for capitalized words (potential names)
        names = re.findall(r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b', text)
        return list(set(names))[:10]  # Limit to 10

    def _extract_dates(self, text: str) -> List[str]:
        # Regex for dates like DD/MM/YYYY or MM/DD/YYYY
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b', text)
        return list(set(dates))

    def _extract_amounts(self, text: str) -> List[str]:
        # Regex for money amounts
        amounts = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s?(?:dollars?|USD|EUR|GBP)\b', text, re.IGNORECASE)
        return list(set(amounts))

    def _extract_clauses(self, text: str) -> List[str]:
        # Look for sentences with keywords
        sentences = re.split(r'[.!?]', text)
        clauses = [s.strip() for s in sentences if any(word in s.lower() for word in ['clause', 'section', 'article', 'paragraph'])]
        return clauses[:5]

    def _extract_risks(self, text: str) -> List[str]:
        risk_keywords = ['penalty', 'fine', 'breach', 'termination', 'liability', 'missing', 'incomplete']
        risks = []
        for keyword in risk_keywords:
            if keyword in text.lower():
                risks.append(f"Potential {keyword} mentioned")
        return list(set(risks))

    def _generate_summary(self, text: str) -> str:
        # Simple summary: first 200 characters
        return text[:200] + "..." if len(text) > 200 else text