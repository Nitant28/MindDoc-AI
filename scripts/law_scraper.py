"""
law_scraper.py
Scrapes Indian legal information from official government sites and structures it for RAG pipelines.
Sources: India Code (https://www.indiacode.nic.in/), Income Tax Department, etc.
"""

import requests
from bs4 import BeautifulSoup
import json
import time

# Additional sources for legal Q&A (e.g., Income Tax FAQ)
INCOME_TAX_FAQ_URL = "https://incometaxindia.gov.in/pages/tax-FAQs.aspx"

# Example: Scrape bare acts from India Code
INDIA_CODE_BASE = "https://www.indiacode.nic.in"
ACTS_LIST_URL = f"{INDIA_CODE_BASE}/handle/123456789/1362/browse?type=statute"


def get_acts_list():
    """Scrape list of acts from India Code."""
    acts = []
    resp = requests.get(ACTS_LIST_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if href and "/handle/123456789/" in href and link.text.strip():
            acts.append({
                "title": link.text.strip(),
                "url": INDIA_CODE_BASE + href
            })
    return acts


def get_act_sections(act_url):
    """Scrape sections of a given act."""
    resp = requests.get(act_url)
    soup = BeautifulSoup(resp.text, "html.parser")
    sections = []
    # Try to find sections by <h3> or <h4> tags, fallback to paragraphs
    for sec in soup.find_all(['h3', 'h4']):
        section_title = sec.text.strip()
        # Section content is usually in the next sibling or next few siblings
        content = []
        sib = sec.find_next_sibling()
        while sib and sib.name not in ['h3', 'h4']:
            if sib.name in ['p', 'div']:
                content.append(sib.get_text(strip=True))
            sib = sib.find_next_sibling()
        section_content = " ".join(content)
        if section_title:
            sections.append({
                "section_title": section_title,
                "section_content": section_content
            })
    return sections


def scrape_laws():
    acts = get_acts_list()
    all_laws = []
    for act in acts[:10]:  # Limit for demo; remove limit for full scrape
        print(f"Scraping: {act['title']}")
        sections = get_act_sections(act["url"])
        all_laws.append({
            "act_title": act["title"],
            "act_url": act["url"],
            "sections": sections
        })
        time.sleep(1)  # Be polite to the server

    # Scrape FAQs/Q&A
    faqs = scrape_income_tax_faq()

    # Save all data
    data = {
        "laws": all_laws,
        "faqs": faqs
    }
    with open("laws_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Scraping complete. Data saved to laws_data.json.")


def scrape_income_tax_faq():
    """Scrape FAQs from the Indian Income Tax Department site."""
    faqs = []
    try:
        resp = requests.get(INCOME_TAX_FAQ_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        # The FAQ page uses <div class="panel panel-default"> for each FAQ
        for panel in soup.find_all("div", class_="panel panel-default"):
            q = panel.find("div", class_="panel-heading")
            a = panel.find("div", class_="panel-body")
            if q and a:
                faqs.append({
                    "question": q.get_text(strip=True),
                    "answer": a.get_text(strip=True)
                })
    except Exception as e:
        print(f"FAQ scraping failed: {e}")
    return faqs


if __name__ == "__main__":
    scrape_laws()
