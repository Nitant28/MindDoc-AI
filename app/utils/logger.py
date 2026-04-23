# Logger: print and save logs
import datetime
import os

LOG_FILE = os.path.join(os.path.dirname(__file__), '../../logs/interaction.log')

def log_event(event: dict):
    line = f"[{datetime.datetime.now()}] " + " ".join([f"[{k.upper()}] {v}" for k, v in event.items()])
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
