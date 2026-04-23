"""
gov_law_scraper.py
Scrapes official Indian tax law sources (Income Tax Act, Finance Act, CBDT, GST, notifications).
Downloads PDFs and HTML for further processing.
"""

import os
import requests
from bs4 import BeautifulSoup

os.makedirs("gov_law_docs", exist_ok=True)

# Example: Scrape Income Tax Act (HTML)
INCOME_TAX_ACT_URL = "https://www.incometaxindia.gov.in/pages/acts/income-tax-act.aspx"

resp = requests.get(INCOME_TAX_ACT_URL)
soup = BeautifulSoup(resp.text, "html.parser")

# Find links to sections/chapters (HTML or PDF)
for link in soup.find_all("a", href=True):
    href = link["href"]
    if href.endswith(".pdf") or "/acts/" in href:
        url = href if href.startswith("http") else f"https://www.incometaxindia.gov.in{href}"
        fname = url.split("/")[-1]
        print(f"Downloading {url}")
        try:
            r = requests.get(url)
            with open(f"gov_law_docs/{fname}", "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Failed: {e}")

print("Government law document download complete.")
