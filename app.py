from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import psutil, time, json, os, socket, subprocess

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "data", "feed.json")

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")

def read_feed():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"updated_at": None, "items": []}
    except Exception:
        return {"updated_at": None, "items": [{"title": "Feed error", "status": "bad", "detail": "Could not read feed.json"}]}

def get_temp_c():
    # Works on Raspberry Pi
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()
        # format: temp=48.3'C
        return float(out.split("=")[1].split("'")[0])
    except Exception:
        return None

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def stats():
    boot = psutil.boot_time()
    uptime_s = int(time.time() - boot)

    cpu = psutil.cpu_percent(interval=0.2)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "cpu_percent": cpu,
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / (1024**3), 2),
        "ram_total_gb": round(vm.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "temp_c": get_temp_c(),
        "uptime_s": uptime_s,
        "ip": get_ip(),
    }

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stats": stats(),
            "feed": read_feed(),
        },
    )
