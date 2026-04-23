import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.models import DocumentChunk, Document
import json
import numpy as np
import requests
import os
from app.services.ollama_client import generate_with_ollama
from app.services.deepseek_client import generate_with_deepseek
from app.services.openrouter_client import generate_with_openrouter
from app.services.advanced_retriever import AdvancedRetriever

logger = logging.getLogger(__name__)

# New imports for advanced tools


# Optional dependency flags and imports
try:
    from anthropic import Anthropic  # type: ignore[import-unresolved]
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None
    ANTHROPIC_AVAILABLE = False

try:
    import cohere  # type: ignore[import-unresolved]
    COHERE_AVAILABLE = True
except ImportError:
    cohere = None
    COHERE_AVAILABLE = False

try:
    from langchain.tools import DuckDuckGoSearchRun, WolframAlphaQueryRun  # type: ignore[import-unresolved]
    TOOLS_AVAILABLE = True
except ImportError:
    DuckDuckGoSearchRun = None
    WolframAlphaQueryRun = None
    TOOLS_AVAILABLE = False


from typing import Optional

def load_vector_store(db: Session, tenant_id: int, document_id: Optional[int] = None):
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
        emb = None
        try:
            emb_candidate = json.loads(str(chunk.embedding))
            # Only treat as embedding if it's a list of floats
            if isinstance(emb_candidate, list) and all(isinstance(x, (float, int)) for x in emb_candidate):
                emb = np.array(emb_candidate, dtype=float)
        except Exception:
            emb = None
        docs.append(SimpleDoc(chunk.chunk_text, emb))

    class SimpleRetriever:
        def __init__(self, docs):
            self.docs = docs

        def as_retriever(self):
            return self

        def get_relevant_documents(self, query_embedding=None, k: int = 999):
            # Handle token-based text fallback when query_embedding is a plain string or None
            if query_embedding is None or isinstance(query_embedding, str):
                # Fallback: simple token overlap scoring - return top matching chunks
                def score(text, q):
                    q_tokens = set(q.lower().split())
                    tokens = set(text.lower().split())
                    overlap = len(q_tokens & tokens)
                    return overlap if overlap > 0 else 0

                def get_top_k(q, k=999):
                    scored = [(d, score(d.page_content, q)) for d in self.docs]
                    relevant = [d for d, s in scored if s > 0]
                    relevant_sorted = sorted(relevant, key=lambda d: score(d.page_content, q), reverse=True)
                    return relevant_sorted[:k] if relevant_sorted else sorted([d for d, s in scored], key=lambda d: score(d.page_content, q), reverse=True)[:max(10, k)]

                if isinstance(query_embedding, str):
                    return get_top_k(query_embedding, k)
                return get_top_k

            # Embedding-based similarity lookup
            if isinstance(query_embedding, (list, tuple)):
                query_embedding = np.array(query_embedding, dtype=float)
            elif not isinstance(query_embedding, np.ndarray):
                try:
                    query_embedding = np.array(query_embedding, dtype=float)
                except Exception:
                    return self.get_relevant_documents(None, k=k)

            scores = []
            for d in self.docs:
                if d.embedding is None or not isinstance(d.embedding, np.ndarray):
                    scores.append(-1.0)
                    continue
                v = d.embedding
                # Cosine similarity
                denom = (np.linalg.norm(v) * np.linalg.norm(query_embedding))
                sim = float(np.dot(v, query_embedding) / denom) if denom > 0 else 0.0
                scores.append(sim)
            idx = np.argsort(scores)[::-1]
            # Return top-scored docs, but include all with positive similarity
            relevant = [self.docs[i] for i in idx if scores[i] > 0.1][:k]
            return relevant if relevant else [self.docs[i] for i in idx[:max(10, k)]]

    return SimpleRetriever(docs)

def _call_llm(context: str, query: str, model: Optional[str] = None, max_tokens: int = 512) -> str:
    """Fast LLM call with smart prompt routing.
    
    SPEEDS:
    - DeepSeek: 1-2 seconds (FASTEST, best for RAG)
    - Ollama: 2-5 seconds (free, local)
    - OpenAI: 3-5 seconds (slower API)
    - Claude: 5-10 seconds (slowest)
    """
    
    # Smart prompt based on context
    if context and context.strip():
        # Document-aware prompt (has context)
        prompt = f"""You are answering based on SPECIFIC DOCUMENT information provided below. 
IMPORTANT: Use ONLY information from this document. Do NOT refer to general knowledge unless to clarify technical terms.

{context}

User Question: {query}

Answer based ONLY on the document above:"""
        temperature = 0.3  # Lower = more accurate extraction
        logger.info(f"LLM: Using document context ({len(context)} chars) - Temperature: 0.3 (accurate)")
    else:
        # General knowledge (NO document)
        prompt = f"""Answer this question using your general knowledge. 
You are NOT referencing any specific document - answer from general knowledge only.

Question: {query}

Answer:"""
    temperature = 0.5  # Higher = more natural conversation
        logger.info(f"LLM: Using general knowledge (NO document context) - Temperature: 0.5 (natural)")
    
    # 0. TRY OPENROUTER FIRST (User Requested, Free)
    try:
        result = generate_with_openrouter(prompt, max_tokens=max_tokens, temperature=temperature)
        if result and isinstance(result, str) and result.strip():
            logger.info(f"LLM response from OpenRouter")
            return result
    except Exception as e:
        logger.warning(f"OpenRouter failed: {e}")

    # 1. TRY DEEPSEEK SECOND (FASTEST for RAG, cheapest)
    try:
        result = generate_with_deepseek(prompt, model="deepseek-chat", max_tokens=max_tokens, temperature=temperature)
        if result and isinstance(result, str) and result.strip():
            logger.info(f"LLM response from DeepSeek (1-2s)")
            return result
    except Exception as e:
        logger.warning(f"DeepSeek failed: {e}")
    
    # 2. FALLBACK to Ollama (free, local, instant if running)
    try:
        result = generate_with_ollama(prompt, model=model, max_tokens=max_tokens, temperature=temperature)
        if result and isinstance(result, str) and result.strip():
            logger.info(f"LLM response from Ollama (2-5s)")
            return result
    except Exception as e:
        logger.warning(f"Ollama failed: {e}")
    
    # 3. Try OpenAI GPT-4 (slower, more expensive)
    if os.getenv('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response.choices[0].message.content
            logger.info(f"LLM response from GPT-4 (3-5s)")
            return content if content is not None else ""
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
    
    # 4. Try Claude (slowest)
    if ANTHROPIC_AVAILABLE and os.getenv('ANTHROPIC_API_KEY'):
        try:
            if Anthropic is not None:
                client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                logger.info(f"LLM response from Claude (5-10s)")
                return response.content[0].text
        except Exception as e:
            logger.warning(f"Claude failed: {e}")
    
    # 5. Last resort: Cohere
    if COHERE_AVAILABLE and os.getenv('COHERE_API_KEY'):
        try:
            if cohere is not None:
                co = cohere.Client(api_key=os.getenv('COHERE_API_KEY'))
                response = co.generate(
                    model='command-xlarge-nightly',
                    prompt=prompt,
                    max_tokens=max_tokens
                )
                logger.info(f"LLM response from Cohere")
                return response.generations[0].text
        except Exception as e:
            logger.warning(f"Cohere failed: {e}")
    
    return "Sorry, all LLM backends are unavailable. Please check API keys or Ollama server."


def query_rag(vector_store, query: str, use_tools: bool = False, db: Optional[Session] = None, tenant_id: Optional[int] = None, document_id: Optional[int] = None) -> str:
    """Query the RAG pipeline - smart document-aware with fast responses.
    
    - If document_id provided: Extract from that specific document only
    - If document_id is None: Answer from general knowledge (no document context)
    """
    try:
        context = ""
        
        # SMART BEHAVIOR: Only load document context if a specific document is attached
        if document_id is not None:
            # User attached a document - use RAG to extract from it
            top_docs = []
            
            if vector_store:
                retriever = vector_store.as_retriever() if hasattr(vector_store, 'as_retriever') else vector_store
                try:
                    # Retrieve only 5-8 most relevant chunks (FAST)
                    top_docs = retriever.get_relevant_documents(query, k=8)
                except Exception:
                    top_docs = []
            
            # If vector search failed, get from DB as fallback
            if not top_docs and db is not None and tenant_id is not None:
                try:
                    query_chunks = db.query(DocumentChunk).join(Document).filter(
                        Document.tenant_id == tenant_id,
                        Document.id == document_id
                    ).limit(8)
                    top_docs = query_chunks.all()
                except Exception:
                    top_docs = []
            
            # Build context from retrieved chunks only
            if top_docs:
                context_parts = []
                for d in top_docs:
                    text = None
                    if hasattr(d, 'page_content'):
                        text = getattr(d, 'page_content', None)
                    elif hasattr(d, 'chunk_text'):
                        text = getattr(d, 'chunk_text', None)
                    elif isinstance(d, dict):
                        text = d.get('text', None)
                    
                    if text is not None and str(text).strip():
                        context_parts.append(str(text))
                
                if context_parts:
                    context = "DOCUMENT INFORMATION:\n" + "\n---\n".join(context_parts)
        else:
            # No document attached - use GENERAL KNOWLEDGE ONLY
            logger.info(f"No document specified. Using general knowledge.")
        
        # Call LLM with smart context handling
        return _call_llm(context, query)

    except Exception as e:
        return f"Error during RAG query: {e}"


def _use_tools(query: str) -> str:
    """Use integrated tools like web search and calculator for enhanced responses."""
    if not TOOLS_AVAILABLE:
        return ""

    results = []
    try:
        if DuckDuckGoSearchRun is not None:
            search = DuckDuckGoSearchRun()
            search_result = search.run(query)
            results.append(f"Web search: {search_result}")
    except Exception:
        pass

    try:
        if os.getenv('WOLFRAM_ALPHA_APPID') and WolframAlphaQueryRun is not None:
            wolfram = WolframAlphaQueryRun()
            calc_result = wolfram.run(query)
            results.append(f"Calculation: {calc_result}")
    except Exception:
        pass

    return " | ".join(results) if results else ""