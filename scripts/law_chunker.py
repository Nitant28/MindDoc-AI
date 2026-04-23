"""
law_chunker.py
Detects law sections, subsections, and chunks text into rules with metadata.
Outputs intermediate JSON for dataset generation.
"""

import os
import re
import json

os.makedirs("law_chunks", exist_ok=True)

SECTION_PATTERN = re.compile(r"Section\s+(\d+[A-Za-z]*)")

for fname in os.listdir("parsed_docs"):
    with open(os.path.join("parsed_docs", fname), "r", encoding="utf-8") as f:
        text = f.read()
    # Split by section
    chunks = []
    for match in SECTION_PATTERN.finditer(text):
        start = match.start()
        end = match.end()
        section = match.group(1)
        next_match = SECTION_PATTERN.search(text, end)
        chunk_text = text[end:next_match.start()] if next_match else text[end:]
        chunks.append({
            "section": section,
            "law_name": fname.split(".")[0],
            "text": chunk_text.strip(),
            "source": fname
        })
    # Save chunks
    with open(os.path.join("law_chunks", fname.replace(".txt", ".json")), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
