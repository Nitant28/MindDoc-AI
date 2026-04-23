import re

def clean_text(text: str) -> str:
    # Remove extra whitespaces and newlines
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    return text.strip()