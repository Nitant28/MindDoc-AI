# LLM Generator: strict prompt using Ollama
import os
from llm.llm_interface import LLMInterface

OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gpt-oss:120b-cloud')  # Change to your preferred Ollama model name
llm = LLMInterface(model_name=OLLAMA_MODEL)

def generate_answer(context_chunks, query):
    """
    Generate answer using strict prompt and context via Ollama LLM.
    """
    result = llm.generate_response(context_chunks, query)
    return result["answer"]
