"""Quick test for the local LLM helper.

Will load the model defined by LOCAL_LLM_MODEL or default to gpt2-medium.
"""
import os
import time
from app.services.local_llm import LocalLLM


def main():
    model = os.environ.get('LOCAL_LLM_MODEL', 'gpt2-medium')
    print('Using model:', model)
    llm = LocalLLM(model_name=model)
    start = time.time()
    llm.load()
    print('Loaded in', time.time() - start, 'seconds')
    prompt = 'Write a short, friendly greeting and one-sentence description of Paris.'
    out = llm.generate(prompt, max_new_tokens=60)
    print('\n=== OUTPUT ===\n')
    print(out)


if __name__ == '__main__':
    main()
