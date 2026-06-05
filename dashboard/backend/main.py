import os
import json
import re
import subprocess
import urllib.request
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path resolution — works locally and on Railway
# main.py lives at: <repo>/dashboard/backend/main.py
# Three .parent calls → repo root
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = Path(os.environ.get("REPO_ROOT", THIS_FILE.parent.parent.parent))
SCRIPTS_DIR = REPO_ROOT / "scripts"
MEMORY_DIR = REPO_ROOT / "memory"
BACKTEST_RESULTS_DIR = REPO_ROOT / "backtest" / "results"

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_ENDPOINT = os.environ.get("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")

app = FastAPI(title="Trading Hub API")

origins = [FRONTEND_URL] if FRONTEND_URL != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def verify_password(x_password: Optional[str] = Header(None)):
    if DASHBOARD_PASSWORD and x_password != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_alpaca(subcommand: str, *args: str):
    script = str(SCRIPTS_DIR / "alpaca.sh")
    cmd = ["bash", script, subcommand, *args]
    env = {**os.environ}
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
    if result.returncode != 0:
        raise HTTPException(status_code=502, detail=result.stderr.strip() or "Alpaca error")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw": result.stdout.strip()}


def read_memory(filename: str, default: str = "") -> str:
    p = MEMORY_DIR / filename
    return p.read_text() if p.exists() else default


def alpaca_api(method: str, path: str, body: Optional[dict] = None):
    url = f"{ALPACA_ENDPOINT.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "APCA-API-KEY-ID": ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise HTTPException(status_code=e.code, detail=body_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


# ---------------------------------------------------------------------------
# Motivational quotes (50 trading & success quotes, rotate by day-of-year)
# ---------------------------------------------------------------------------
QUOTES = [
    ("The stock market is a device for transferring money from the impatient to the patient.", "Warren Buffett"),
    ("Risk comes from not knowing what you're doing.", "Warren Buffett"),
    ("The four most dangerous words in investing are: 'This time it's different.'", "John Templeton"),
    ("In the short run, the market is a voting machine. In the long run, it is a weighing machine.", "Benjamin Graham"),
    ("It's not whether you're right or wrong, but how much money you make when you're right.", "George Soros"),
    ("The trend is your friend until the end when it bends.", "Ed Seykota"),
    ("Cut your losses short and let your winners run.", "Jesse Livermore"),
    ("Markets can remain irrational longer than you can remain solvent.", "John Maynard Keynes"),
    ("The goal of a successful trader is to make the best trades. Money is secondary.", "Alexander Elder"),
    ("The most important thing is to have a method for staying in the game.", "Paul Tudor Jones"),
    ("Do more of what works and less of what doesn't.", "Steve Clark"),
    ("I'm always thinking about losing money as opposed to making money.", "Paul Tudor Jones"),
    ("The biggest risk is not taking any risk.", "Mark Zuckerberg"),
    ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
    ("The stock market is filled with individuals who know the price of everything, but the value of nothing.", "Philip Fisher"),
    ("Wide diversification is only required when investors do not understand what they are doing.", "Warren Buffett"),
    ("The key to trading success is emotional discipline.", "Victor Sperandeo"),
    ("Be fearful when others are greedy and greedy when others are fearful.", "Warren Buffett"),
    ("The markets are unforgiving, and emotional trading always results in losses.", "Alexander Elder"),
    ("Don't try to buy at the bottom and sell at the top. It can't be done except by liars.", "Bernard Baruch"),
    ("Successful investing is about managing risk, not avoiding it.", "Benjamin Graham"),
    ("The disciplined trader is the successful trader.", "Mark Douglas"),
    ("Your number one job is to trade well, not to make money. The money will follow.", "Linda Raschke"),
    ("Every day I assume every position I have is wrong.", "Paul Tudor Jones"),
    ("Good investing is boring.", "George Soros"),
    ("The most consistent traders all have one thing in common: they don't fight the market.", "Unknown"),
    ("Trading is not about being right. It's about making money.", "Unknown"),
    ("The hard work in trading comes in the preparation, not the execution.", "Jack Schwager"),
    ("Plan your trade and trade your plan.", "Unknown"),
    ("Protect your capital. It's the only tool you have.", "Unknown"),
    ("Never let a winner turn into a loser.", "Unknown"),
    ("Amateurs want to be right. Professionals want to make money.", "Unknown"),
    ("If you personalize losses, you can't trade.", "Bruce Kovner"),
    ("Know what you own, and know why you own it.", "Peter Lynch"),
    ("One of the funny things about the stock market is that every time one person buys, another sells.", "William Feather"),
    ("You get recessions, you have stock market declines. If you don't understand that, you're not ready.", "Peter Lynch"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("Time in the market beats timing the market.", "Unknown"),
    ("Diversification is protection against ignorance.", "Warren Buffett"),
    ("Price is what you pay. Value is what you get.", "Warren Buffett"),
    ("Wall Street is the only place that people ride to in a Rolls Royce to get advice from subway riders.", "Warren Buffett"),
    ("Be greedy when others are fearful.", "Warren Buffett"),
    ("The more I practice, the luckier I get.", "Gary Player"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Opportunities don't happen. You create them.", "Chris Grosser"),
    ("Success usually comes to those who are too busy to be looking for it.", "Henry David Thoreau"),
    ("Don't be afraid to give up the good to go for the great.", "John D. Rockefeller"),
    ("The only limit to our realization of tomorrow is our doubts of today.", "Franklin D. Roosevelt"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "repo_root": str(REPO_ROOT)}


@app.get("/api/ping")
async def ping(_: None = Depends(verify_password)):
    return {"ok": True}


@app.get("/api/account")
async def get_account(_: None = Depends(verify_password)):
    return run_alpaca("account")


@app.get("/api/positions")
async def get_positions(_: None = Depends(verify_password)):
    return run_alpaca("positions")


@app.get("/api/orders")
async def get_orders(_: None = Depends(verify_password)):
    return run_alpaca("orders", "open")


@app.get("/api/equity-history")
async def get_equity_history(_: None = Depends(verify_password)):
    return alpaca_api("GET", "/v2/account/portfolio/history?period=1D&timeframe=5Min")


@app.get("/api/status")
async def get_status(_: None = Depends(verify_password)):
    trade_log = read_memory("TRADE-LOG.md")
    research_log = read_memory("RESEARCH-LOG.md")
    today = date.today().isoformat()

    pre_market_today = today in research_log
    eod_today = bool(re.search(rf"Day\s+\d+\s+[—\-]+\s+{re.escape(today)}", trade_log))

    backtest_files = sorted(BACKTEST_RESULTS_DIR.glob("*.json")) if BACKTEST_RESULTS_DIR.exists() else []
    latest_backtest = backtest_files[-1].name if backtest_files else None

    paused = (MEMORY_DIR / "PAUSE-FLAG.txt").exists()

    return {
        "paused": paused,
        "routines": {
            "pre_market": {"done_today": pre_market_today, "label": "Pre-Market Research"},
            "market_open": {"done_today": False, "label": "Market Open"},
            "midday": {"done_today": False, "label": "Midday Check"},
            "eod": {"done_today": eod_today, "label": "EOD Summary"},
        },
        "backtest": {
            "latest_file": latest_backtest,
            "count": len(backtest_files),
        },
    }


@app.get("/api/backtest")
async def get_backtest(_: None = Depends(verify_password)):
    if not BACKTEST_RESULTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No backtest results directory")
    files = sorted(BACKTEST_RESULTS_DIR.glob("*.json"))
    if not files:
        raise HTTPException(status_code=404, detail="No backtest results found")
    try:
        return json.loads(files[-1].read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/alerts")
async def get_alerts(_: None = Depends(verify_password)):
    log_text = read_memory("TELEGRAM-LOG.md", "")
    if not log_text:
        return {"alerts": []}
    lines = [l.strip() for l in log_text.splitlines() if l.strip() and not l.startswith("#")]
    recent = list(reversed(lines[-10:]))

    def classify(line: str) -> str:
        ll = line.lower()
        if any(w in ll for w in ["buy", "bought", "entered", "opening"]):
            return "buy"
        if any(w in ll for w in ["sell", "sold", "closed", "stop triggered"]):
            return "sell"
        if any(w in ll for w in ["loss", "-$", "down", "red"]):
            return "loss"
        if any(w in ll for w in ["profit", "gain", "+$", "up", "green"]):
            return "profit"
        if any(w in ll for w in ["warn", "alert", "risk", "pause"]):
            return "warning"
        return "info"

    return {"alerts": [{"text": l, "type": classify(l)} for l in recent]}


@app.get("/api/calendar")
async def get_calendar(_: None = Depends(verify_password)):
    trade_log = read_memory("TRADE-LOG.md", "")
    today = date.today()
    pnl_by_day: dict[str, float] = {}

    for entry_date, pnl_str in re.findall(
        r"##\s+Day\s+\d+\s+[—\-]+\s+(\d{4}-\d{2}-\d{2}).*?\*\*Day P&L:\*\*\s*\$?([-\d,\.]+)",
        trade_log,
    ):
        try:
            d = date.fromisoformat(entry_date)
            if d.year == today.year and d.month == today.month:
                pnl_by_day[entry_date] = float(pnl_str.replace(",", ""))
        except ValueError:
            pass

    all_trade_dates = re.findall(r"\d{4}-\d{2}-\d{2}", trade_log)

    return {
        "year": today.year,
        "month": today.month,
        "pnl_by_day": pnl_by_day,
        "trade_days": list(set(all_trade_dates)),
        "today": today.isoformat(),
    }


@app.get("/api/quote")
async def get_quote(_: None = Depends(verify_password)):
    idx = date.today().timetuple().tm_yday % len(QUOTES)
    text, author = QUOTES[idx]
    return {"text": text, "author": author}


@app.post("/api/pause")
async def pause_bot(_: None = Depends(verify_password)):
    MEMORY_DIR.mkdir(exist_ok=True)
    (MEMORY_DIR / "PAUSE-FLAG.txt").write_text(
        f"Paused at {datetime.now().isoformat()} via dashboard\n"
    )
    return {"status": "paused"}


@app.post("/api/resume")
async def resume_bot(_: None = Depends(verify_password)):
    flag = MEMORY_DIR / "PAUSE-FLAG.txt"
    if flag.exists():
        flag.unlink()
    return {"status": "running"}


@app.post("/api/close-all")
async def close_all_positions(_: None = Depends(verify_password)):
    return alpaca_api("DELETE", "/v2/positions?cancel_orders=true")


@app.get("/api/goals")
async def get_goals(_: None = Depends(verify_password)):
    p = MEMORY_DIR / "GOALS.json"
    if not p.exists():
        defaults = [
            {"id": 1, "title": "Grow Account P&L", "target": 1000, "current": 0, "unit": "$"},
            {"id": 2, "title": "Complete Backtest Runs", "target": 30, "current": 0, "unit": "runs"},
            {"id": 3, "title": "Win Rate Target", "target": 55, "current": 0, "unit": "%"},
        ]
        MEMORY_DIR.mkdir(exist_ok=True)
        p.write_text(json.dumps(defaults, indent=2))
        return defaults
    return json.loads(p.read_text())


class GoalsList(BaseModel):
    goals: list


@app.post("/api/goals")
async def update_goals(body: GoalsList, _: None = Depends(verify_password)):
    p = MEMORY_DIR / "GOALS.json"
    MEMORY_DIR.mkdir(exist_ok=True)
    p.write_text(json.dumps(body.goals, indent=2))
    return {"status": "saved"}


@app.get("/api/notes")
async def get_notes(_: None = Depends(verify_password)):
    p = MEMORY_DIR / "DAILY-NOTES.md"
    return {"content": p.read_text() if p.exists() else ""}


class NotesBody(BaseModel):
    content: str


@app.post("/api/notes")
async def save_notes(body: NotesBody, _: None = Depends(verify_password)):
    p = MEMORY_DIR / "DAILY-NOTES.md"
    MEMORY_DIR.mkdir(exist_ok=True)
    p.write_text(body.content)
    return {"status": "saved"}
