# FastAPI entry point for the RAG chatbot system
from fastapi import FastAPI, Request
from pydantic import BaseModel
from app.classification.query_classifier import classify_query
from app.classification.query_rewriter import rewrite_query
from app.retrieval.hybrid_retriever import hybrid_retrieve
from app.retrieval.context_builder import build_context
from app.generation.llm_generator import generate_answer
from app.generation.confidence_scorer import score_confidence
from app.utils.guardrails import is_adversarial
from app.utils.logger import log_event
from app.utils.cache import QueryCache
from app.utils.escalation import save_escalation
import json

app = FastAPI()
query_cache = QueryCache(size=100)

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def handle_query(req: QueryRequest):
    query = req.query.strip()
    log = {"QUERY": query}
    # Guardrails: adversarial filter
    if is_adversarial(query):
        log["TYPE"] = "ADVERSARIAL"
        log["RESPONSE_TYPE"] = "BLOCKED"
        log_event(log)
        return {"response": "I cannot assist with that request."}
    # Query classification
    qtype = classify_query(query)
    log["TYPE"] = qtype
    # Cost optimization: skip retrieval for small talk
    if qtype == "SMALL_TALK":
        log["RETRIEVAL"] = "NO"
        log["RESPONSE_TYPE"] = "SMALL_TALK"
        log_event(log)
        return {"response": "Hello! How can I help you today?"}
    # Human escalation
    if qtype == "ESCALATION":
        # In real system, would be multi-turn; here, simulate collection
        # For demo, use static values
        name = "User"
        contact = "user@example.com"
        issue = query
        save_escalation(name, contact, issue)
        log["RESPONSE_TYPE"] = "ESCALATION"
        log_event(log)
        return {"response": "Your request has been escalated. Our team will contact you soon."}
    # Check cache
    cached = query_cache.get(query)
    if cached:
        log["RETRIEVAL"] = "CACHE"
        log["RESPONSE_TYPE"] = "CACHED"
        log_event(log)
        return cached
    # Query rewriting
    rewritten = rewrite_query(query)
    # Retrieval (placeholder)
    docs = hybrid_retrieve(rewritten, None, None)
    log["RETRIEVAL"] = "YES"
    log["DOCS"] = "docs_placeholder"
    # Context building
    context = build_context(docs)
    # Generation
    answer = generate_answer(context, rewritten)
    # Confidence scoring (placeholder)
    confidence = score_confidence([0.8])
    log["SCORE"] = confidence
    log["CONFIDENCE"] = "HIGH" if confidence > 0.6 else "LOW"
    log["RESPONSE_TYPE"] = "RAG"
    log_event(log)
    response = {"response": answer}
    query_cache.set(query, response)
    return response
