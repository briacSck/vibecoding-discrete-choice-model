"""Relaunches collect_panel_data.py until it logs "All done".
Something on this machine silently kills long-running python processes;
the collector's (repo, quarter) resume logic makes restarts cheap."""
import os
import subprocess
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG  = os.path.join(HERE, "_collector_stdout.log")
SLOG = os.path.join(HERE, "_supervisor.log")

def slog(msg):
    with open(SLOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")

def finished():
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            return "All done" in f.read()
    except FileNotFoundError:
        return False

for attempt in range(1, 31):
    slog(f"attempt {attempt}")
    with open(LOG, "a", encoding="utf-8") as out:
        subprocess.run(
            ["python", os.path.join(HERE, "collect_panel_data.py")],
            stdout=out, stderr=subprocess.STDOUT, cwd=HERE)
    if finished():
        slog(f"COMPLETE after attempt {attempt}")
        break
    time.sleep(15)
else:
    slog("GAVE UP after 30 attempts")
