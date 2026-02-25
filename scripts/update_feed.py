import json, os, subprocess
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import sqlite3, time
import psutil
import subprocess

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(APP_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "feed.json")

# Repo root where your .git is (APP_DIR is usually correct)
REPO_DIR = APP_DIR

# REQUIRED by MET Norway ToS. Put something real here.
# Example: "pi-dashboard/1.0 (https://example.com) you@email.com"
WEATHER_USER_AGENT = "pi-dashboard/1.0 gahoa005@osloskolen.no"

OSLO_LAT = 59.91
OSLO_LON = 10.75

DB_FILE = os.path.join(DATA_DIR, "stats.sqlite")

def get_temp_c():
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return None

def log_stats_point():
    ts = int(time.time())
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    temp = get_temp_c()

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS stats (
        ts INTEGER PRIMARY KEY,
        cpu REAL,
        ram REAL,
        disk REAL,
        temp REAL
      )
    """)
    cur.execute("INSERT OR REPLACE INTO stats(ts,cpu,ram,disk,temp) VALUES(?,?,?,?,?)",
                (ts, cpu, ram, disk, temp))
    # keep last ~7 days if you log every minute: 7*24*60 = 10080
    cur.execute("DELETE FROM stats WHERE ts < ?", (ts - 7*24*60*60,))
    con.commit()
    con.close()

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def run_git(args, check=True):
    return subprocess.check_output(["git", "-C", REPO_DIR, *args], text=True, stderr=subprocess.STDOUT).strip()

def git_status_item():
    try:
        # Update remote tracking info
        run_git(["fetch", "--prune"], check=False)

        dirty = run_git(["status", "--porcelain"], check=False)
        is_dirty = len(dirty.strip()) > 0

        # Ahead/behind vs upstream if tracking is set
        try:
            ahead_behind = run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"])
            # output: "<left> <right>" where left=behind, right=ahead (depending on direction)
            behind_str, ahead_str = ahead_behind.split()
            behind = int(behind_str)
            ahead = int(ahead_str)
            track_msg = f"{'dirty' if is_dirty else 'clean'}, ahead {ahead}, behind {behind}"
            status = "ok" if (not is_dirty and ahead == 0 and behind == 0) else ("warn" if behind == 0 else "bad")
        except Exception:
            # No upstream configured
            track_msg = f"{'dirty' if is_dirty else 'clean'}, no upstream"
            status = "warn" if is_dirty else "ok"

        return {
            "title": "Git repo",
            "status": status,
            "detail": track_msg,
            "ts": now_iso(),
        }
    except Exception as e:
        return {
            "title": "Git repo",
            "status": "bad",
            "detail": f"Git error: {e}",
            "ts": now_iso(),
        }

def fetch_met_oslo():
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={OSLO_LAT}&lon={OSLO_LON}"
    req = Request(url, headers={"User-Agent": WEATHER_USER_AGENT})
    with urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))

    ts0 = data["properties"]["timeseries"][0]
    instant = ts0["data"]["instant"]["details"]
    temp = instant.get("air_temperature")
    wind = instant.get("wind_speed")

    # Optional next hour details
    next1 = ts0["data"].get("next_1_hours", {})
    summary = next1.get("summary", {})
    details = next1.get("details", {})
    symbol = summary.get("symbol_code")
    precip = details.get("precipitation_amount")

    return temp, wind, symbol, precip

def weather_item():
    try:
        temp, wind, symbol, precip = fetch_met_oslo()
        bits = []
        if temp is not None:
            bits.append(f"{temp}°C")
        if wind is not None:
            bits.append(f"wind {wind} m/s")
        if precip is not None:
            bits.append(f"next 1h {precip} mm")
        if symbol:
            bits.append(symbol)

        return {
            "title": "Weather (Oslo)",
            "status": "ok",
            "detail": ", ".join(bits) if bits else "No data parsed",
            "ts": now_iso(),
        }
    except Exception as e:
        return {
            "title": "Weather (Oslo)",
            "status": "bad",
            "detail": f"Weather error: {e}",
            "ts": now_iso(),
        }

def build_feed():
    items = []
    items.append(git_status_item())
    items.append(weather_item())
    items.append({
        "title": "Updater",
        "status": "ok",
        "detail": "Feed updated successfully",
        "ts": now_iso(),
    })
    return {"updated_at": now_iso(), "items": items}

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    log_stats_point()
    feed = build_feed()
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

if __name__ == "__main__":
    main()
