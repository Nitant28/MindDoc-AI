# Query Classifier: keyword rules + LLM fallback

def classify_query(query: str) -> str:
    """
    Classify query as one of: DOC_QUERY, SMALL_TALK, ESCALATION, ADVERSARIAL
    """
    # Keyword rules
    q = query.lower()
    if any(x in q for x in ["ignore instructions", "bypass", "hack", "reveal secrets"]):
        return "ADVERSARIAL"
    if any(x in q for x in ["talk to human", "escalate", "representative"]):
        return "ESCALATION"
    if any(x in q for x in ["hi", "hello", "how are you", "good morning", "good evening"]):
        return "SMALL_TALK"
    # Fallback: default to DOC_QUERY
    return "DOC_QUERY"
