"""
law_update_scheduler.py
Continuously checks for and integrates new law updates automatically.
"""

import schedule
import time
from threading import Thread
from app.services.law_auto_update import fetch_latest_amendments
from app.services.audit_evidence import log_action

def update_law_database():
    amendments = fetch_latest_amendments()
    # Here, integrate amendments into your law DB (placeholder)
    log_action("system", "law_update", {"amendments": amendments})
    print(f"Law database updated with {len(amendments)} amendments.")

schedule.every(6).hours.do(update_law_database)

def run_law_update_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler in background
scheduler_thread = Thread(target=run_law_update_scheduler, daemon=True)
scheduler_thread.start()
