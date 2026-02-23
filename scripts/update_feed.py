import json, os, time, subprocess
from datetime import datetime, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "feed.json")

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def ping(host="1.1.1.1", count=1, timeout=2):
    try:
        subprocess.check_output(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stderr=subprocess.STDOUT,
            text=True,
        )
        return True
    except Exception:
        return False

def build_feed():
    items = []

    online = ping()
    items.append({
        "title": "Internet",
        "status": "ok" if online else "bad",
        "detail": "Online" if online else "No ping to 1.1.1.1",
        "ts": now_iso(),
    })

    # Placeholder items you can extend later:
    items.append({
        "title": "Updater",
        "status": "ok",
        "detail": "Feed updated successfully",
        "ts": now_iso(),
    })

    return {
        "updated_at": now_iso(),
        "items": items
    }

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    feed = build_feed()
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

if __name__ == "__main__":
    main()
