"""
dataset_generator.py
Generates the final tax_law_knowledge_base.csv from law_chunks/ with all required fields.
"""

import os
import json
import csv

FIELDS = [
    "section",
    "law_name",
    "chapter",
    "topic",
    "tax_category",
    "compliance_requirement",
    "benefit_or_deduction",
    "penalty",
    "amendment_reference",
    "key_rule_summary",
    "taxpayer_type",
    "source_document",
    "source_page"
]

with open("tax_law_knowledge_base.csv", "w", newline='', encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
    writer.writeheader()
    for fname in os.listdir("law_chunks"):
        with open(os.path.join("law_chunks", fname), "r", encoding="utf-8") as f:
            chunks = json.load(f)
        for chunk in chunks:
            row = {field: "" for field in FIELDS}
            row["section"] = chunk.get("section", "")
            row["law_name"] = chunk.get("law_name", "")
            row["key_rule_summary"] = chunk.get("text", "")[:500]
            row["source_document"] = chunk.get("source", "")
            writer.writerow(row)
print("tax_law_knowledge_base.csv generated.")
