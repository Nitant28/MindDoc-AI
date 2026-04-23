# Guardrails: adversarial filter

def is_adversarial(query: str) -> bool:
    q = query.lower()
    return any(x in q for x in ["ignore instructions", "bypass", "hack", "reveal secrets"])
