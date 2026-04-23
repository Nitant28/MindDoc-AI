"""
law_auto_update.py
Auto-update law database with latest amendments, notifications, and circulars.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any

LAW_UPDATE_URL = "https://incometaxindia.gov.in/pages/communications/circulars.aspx"  # Example


def fetch_latest_amendments() -> List[Dict[str, Any]]:
    """Scrape latest amendments/circulars from official portal."""
    resp = requests.get(LAW_UPDATE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    updates = []
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) >= 2:
            updates.append({
                "Title": cols[0].get_text(strip=True),
                "Date": cols[1].get_text(strip=True),
            })
    return updates

# Example usage:
# print(fetch_latest_amendments())
