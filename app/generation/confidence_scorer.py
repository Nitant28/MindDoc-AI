# Confidence Scorer: retrieval + LLM self-eval

def score_confidence(similarity_scores, llm_score=None):
    """
    Compute confidence from retrieval and optional LLM self-eval.
    """
    conf = max(similarity_scores) if similarity_scores else 0.0
    if llm_score is not None:
        conf = (conf + llm_score) / 2
    return conf
