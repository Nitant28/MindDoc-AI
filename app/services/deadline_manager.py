"""
deadline_manager.py
Automated deadline, reminder, and task management for compliance.
"""

import schedule
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable, Dict, Any

reminders = []

def add_reminder(task: str, due_date: str, callback: Callable):
    reminders.append({"task": task, "due_date": due_date, "callback": callback})
    schedule_reminder(task, due_date, callback)

def schedule_reminder(task: str, due_date: str, callback: Callable):
    due = datetime.strptime(due_date, "%Y-%m-%d")
    delta = (due - datetime.now()).days
    if delta > 0:
        schedule.every(delta).days.do(callback)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start scheduler in background
scheduler_thread = Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# Example usage:
# add_reminder("File response to notice", "2026-04-01", lambda: print("Reminder: File your response!"))
