"""
doc_parser.py
Extracts and cleans text from PDFs and HTML files in kaggle_datasets/ and gov_law_docs/.
Outputs cleaned text files for further processing.
"""

import os
import pdfplumber
from bs4 import BeautifulSoup

os.makedirs("parsed_docs", exist_ok=True)

# Parse PDFs
def parse_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"PDF parse failed: {pdf_path} {e}")
    return text

# Parse HTML
def parse_html(html_path):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
        return soup.get_text(separator=" ", strip=True)

# Process all files
def process_all():
    for folder in ["kaggle_datasets", "gov_law_docs"]:
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            if fname.lower().endswith(".pdf"):
                text = parse_pdf(fpath)
            elif fname.lower().endswith(".html") or fname.lower().endswith(".htm"):
                text = parse_html(fpath)
            else:
                continue
            outname = fname.rsplit(".", 1)[0] + ".txt"
            with open(os.path.join("parsed_docs", outname), "w", encoding="utf-8") as f:
                f.write(text)

if __name__ == "__main__":
    process_all()
