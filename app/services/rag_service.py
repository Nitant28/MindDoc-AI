from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.models import DocumentChunk, Document
import json
import numpy as np
import requests
import os
from app.services.ollama_client import generate_with_ollama
from app.services.deepseek_client import generate_with_deepseek

# New imports for advanced tools
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

try:
    from langchain.tools import DuckDuckGoSearchRun, WolframAlphaQueryRun
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False


def load_vector_store(db: Session, tenant_id: int, document_id: int = None):
    """Load stored document chunks and their embeddings from the DB.

    Returns a simple retriever object with documents and embeddings (numpy arrays).
    This avoids FAISS/native dependencies and remains stable on Windows.
    """
    if not document_id:
        return None
    query = db.query(DocumentChunk).join(Document).filter(Document.tenant_id == tenant_id)
    if document_id:
        query = query.filter(Document.id == document_id)
    chunks = query.all()
    if not chunks:
        return None

    class SimpleDoc:
        def __init__(self, text, emb):
            self.page_content = text
            self.embedding = emb

    docs = []
    for chunk in chunks:
        try:
            emb = np.array(json.loads(chunk.embedding))
        except Exception:
            emb = None
        docs.append(SimpleDoc(chunk.chunk_text, emb))

    class SimpleRetriever:
        def __init__(self, docs):
            self.docs = docs

        def as_retriever(self):
            return self

        def get_relevant_documents(self, query_embedding=None, k: int = 999):
            # Retrieve ALL relevant documents for comprehensive context (k=999 means get all)
            if query_embedding is not None:
                scores = []
                for d in self.docs:
                    if d.embedding is None:
                        scores.append(-1.0)
                        continue
                    v = d.embedding
                    # cosine similarity
                    denom = (np.linalg.norm(v) * np.linalg.norm(query_embedding))
                    sim = float(np.dot(v, query_embedding) / denom) if denom > 0 else 0.0
                    scores.append(sim)
                idx = np.argsort(scores)[::-1]
                # Return top-scored docs, but include all with positive similarity
                relevant = [self.docs[i] for i in idx if scores[i] > 0.1][:k]
                return relevant if relevant else [self.docs[i] for i in idx[:max(10, k)]]

            # Fallback: simple token overlap scoring - return ALL matching chunks
            def score(text, q):
                q_tokens = set(q.lower().split())
                tokens = set(text.lower().split())
                overlap = len(q_tokens & tokens)
                return overlap if overlap > 0 else 0

            def get_top_k(q, k=999):
                scored = [(d, score(d.page_content, q)) for d in self.docs]
                # Filter to chunks with at least 1 token overlap, then sort by score
                relevant = [d for d, s in scored if s > 0]
                relevant_sorted = sorted(relevant, key=lambda d: score(d.page_content, q), reverse=True)
                return relevant_sorted[:k] if relevant_sorted else sorted([d for d, s in scored], key=lambda d: score(d.page_content, q), reverse=True)[:max(10, k)]

            return get_top_k

    return SimpleRetriever(docs)

def _call_llm(context: str, query: str, model: str = None, max_tokens: int = 2048) -> str:
    prompt = f"""You are an expert AI assistant with deep domain knowledge. Your task is to provide comprehensive, accurate answers based on the document context provided.

**CRITICAL INSTRUCTIONS:**
1. You have been given COMPLETE access to ALL relevant document sections.
2. Base your answer ENTIRELY on the provided document context.
3. Reference specific sections and quotes from the document when answering.
4. If asked about something in the document, provide a detailed answer using all available sections.
5. Do NOT say "the document doesn't mention" without checking ALL sections provided.
6. Use all context sections to provide the most complete and accurate answer.
7. Structure your answer with clear references to document sections.

Document Context (COMPLETE ACCESS):
{context}

User Question: {query}

Provide a thorough, detailed answer using ALL available document information:""" if context else f"""You are an expert AI assistant with extensive knowledge across all domains. Answer the following question comprehensively and accurately, drawing from your general knowledge.

Question: {query}

Answer:"""

    # Prioritize the strongest available model
    # Claude Opus for best reasoning
    if ANTHROPIC_AVAILABLE and os.getenv('ANTHROPIC_API_KEY'):
        try:
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception:
            pass

    # GPT-4 for strong performance
    if os.getenv('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception:
            pass

    # Cohere for good quality
    if COHERE_AVAILABLE and os.getenv('COHERE_API_KEY'):
        try:
            co = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
            response = co.generate(
                model='command-xlarge-nightly',
                prompt=prompt,
                max_tokens=max_tokens
            )
            return response.generations[0].text
        except Exception:
            pass

    # DeepSeek as fallback
    try:
        return generate_with_deepseek(prompt, model="deepseek-chat", max_tokens=max_tokens)
    except Exception:
        pass

    # Ollama as last resort
    try:
        return generate_with_ollama(prompt, model=model, max_tokens=max_tokens)
    except Exception:
        pass

    return "No advanced LLM available. Please check API keys."


def query_rag(vector_store, query: str, use_tools: bool = False) -> str:
    """Query the RAG pipeline with FULL document access for complete understanding."""
    try:
        # If we have a vector store, retrieve ALL relevant chunks
        retriever = None
        top_docs = []
        if vector_store:
            retriever = vector_store.as_retriever()
            try:
                # Lazy import sentence-transformers for embeddings
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                q_emb = model.encode([query])[0]
                # Retrieve ALL chunks (k=999) instead of limiting to 6
                docs = retriever.get_relevant_documents(q_emb, k=999)
                top_docs = docs
            except Exception:
                # fallback to token-overlap retriever
                docs_fn = retriever.get_relevant_documents(query, k=999)
                # if get_relevant_documents returned a function, call it
                if callable(docs_fn):
                    top_docs = docs_fn(query)
                else:
                    top_docs = docs_fn

        # Build context string with metadata and full content
        context_parts = []
        if top_docs:
            context_parts.append(f"=== COMPLETE DOCUMENT CONTEXT ({len(top_docs)} sections) ===\n")
            for i, d in enumerate(top_docs, 1):
                context_parts.append(f"[Section {i}]\n{d.page_content}\n")
        
        context = "\n".join(context_parts) if context_parts else ""

        # If tools are enabled and no context, try tools
        if use_tools and not context:
            tool_results = _use_tools(query)
            if tool_results:
                context = f"Tool results: {tool_results}"

        # Call LLM with full document context
        return _call_llm(context, query)

    except Exception as e:
        return f"Error during RAG query: {e}"


def _use_tools(query: str) -> str:
    """Use integrated tools like web search and calculator for enhanced responses."""
    if not TOOLS_AVAILABLE:
        return ""

    results = []
    try:
        search = DuckDuckGoSearchRun()
        search_result = search.run(query)
        results.append(f"Web search: {search_result}")
    except Exception:
        pass

    try:
        if os.getenv('WOLFRAM_ALPHA_APPID'):
            wolfram = WolframAlphaQueryRun()
            calc_result = wolfram.run(query)
            results.append(f"Calculation: {calc_result}")
    except Exception:
        pass

    return " | ".join(results) if results else ""