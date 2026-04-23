# Human escalation workflow
import json
import os

ESCALATION_FILE = os.path.join(os.path.dirname(__file__), '../../escalations.json')

def save_escalation(name, contact, issue):
    entry = {"name": name, "contact": contact, "issue": issue}
    try:
        with open(ESCALATION_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
    except Exception:
        with open(ESCALATION_FILE, 'w', encoding='utf-8') as f:
            json.dump([entry], f, indent=2)
