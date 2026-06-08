import os
import json
import re
import subprocess
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path resolution — works locally and on Railway
#
# Local dev: main.py at <repo>/dashboard/backend/main.py
#   → REPO_ROOT = <repo>/  (three .parent calls)
#   → scripts/alpaca.sh at <repo>/scripts/alpaca.sh  ✓
#
# Railway (deploys dashboard/backend/ only, main.py at /app/main.py):
#   → THIS_FILE.parent = /app/  (one level up from /app/main.py)
#   → scripts/ lives at /app/scripts/  (copied during deploy)
#   → Set REPO_ROOT=/app in Railway env vars, or rely on the default below
#
# The default now uses THIS_FILE.parent so Railway works without env vars.
# For local dev, set REPO_ROOT to the repo root in your .env or shell.
# ---------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
_DEFAULT_ROOT = Path(os.environ.get("REPO_ROOT", ""))
if _DEFAULT_ROOT and _DEFAULT_ROOT.is_dir():
    REPO_ROOT = _DEFAULT_ROOT
elif (THIS_FILE.parent / "scripts").is_dir():
    # Railway: scripts/ is a sibling of main.py
    REPO_ROOT = THIS_FILE.parent
else:
    # Local dev fallback: three levels up to repo root
    REPO_ROOT = THIS_FILE.parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
MEMORY_DIR = REPO_ROOT / "memory"
BACKTEST_RESULTS_DIR = REPO_ROOT / "backtest" / "results"

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_ENDPOINT = os.environ.get("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")

app = FastAPI(title="Trading Hub API — Dual Momentum ETF Rotation")

# ---------------------------------------------------------------------------
# CORS — allow Vercel frontend + local dev servers
# Set FRONTEND_URL env var in Railway to the Vercel deployment URL.
# ---------------------------------------------------------------------------
allowed_origins = [
    "https://tradingbot-hub-production.up.railway.app",  # Railway backend self
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",   # fallback
    "http://localhost:8080",   # fallback
]
if FRONTEND_URL:
    # Support comma-separated list of URLs
    for url in FRONTEND_URL.split(","):
        u = url.strip()
        if u and u not in allowed_origins:
            allowed_origins.append(u)
else:
    # No FRONTEND_URL set — use wildcard (tighten once Vercel URL is confirmed)
    # TODO: set FRONTEND_URL=https://your-app.vercel.app in Railway env vars
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allowed_origins != ["*"],
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


def run_script(script_path: Path, *args: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a Python script, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["python3", str(script_path), *args],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ}
    )
    return result.returncode, result.stdout, result.stderr


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
# Motivational quotes (rotate by day-of-year)
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
# Routes — Root + Health
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Root health check — fixes the 404 on Railway root URL."""
    return {
        "status": "ok",
        "service": "tradingbot-hub",
        "strategy": "Dual Momentum ETF Rotation",
        "next_rebalance": "2026-06-30",
        "version": "2.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Railway health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
    }


@app.get("/api/health/bot")
async def bot_health():
    """
    Bot heartbeat — checks last git commit time.
    Returns red if last commit > 26 hours ago (bot may be stuck).
    """
    try:
        git_result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%ci"],
            capture_output=True, text=True, timeout=10
        )
        last_commit = git_result.stdout.strip() if git_result.returncode == 0 else None
    except Exception:
        last_commit = None

    stale = False
    age_hours = None
    if last_commit:
        try:
            # Parse git's ISO timestamp
            commit_dt = datetime.fromisoformat(last_commit.replace(" ", "T", 1).rsplit(" ", 1)[0])
            now_dt = datetime.now()
            age_hours = (now_dt - commit_dt).total_seconds() / 3600
            stale = age_hours > 26
        except Exception:
            pass

    paused = (MEMORY_DIR / "PAUSE-FLAG.txt").exists()

    age_rounded = round(age_hours, 1) if age_hours is not None else None
    return {
        "status": "stale" if stale else "ok",
        # spec-required field names
        "last_commit_iso": last_commit,
        "hours_since_commit": age_rounded,
        "is_stale": stale,
        # legacy aliases kept for compatibility
        "last_commit": last_commit,
        "age_hours": age_rounded,
        "stale": stale,
        "paused": paused,
    }


# ---------------------------------------------------------------------------
# Routes — Dual Momentum specific
# ---------------------------------------------------------------------------

@app.get("/api/signal")
async def get_signal():
    """
    Run dual_momentum_signal.py and return parsed signal + rankings.
    """
    script = SCRIPTS_DIR / "dual_momentum_signal.py"
    if not script.exists():
        return {"error": "not_implemented", "detail": "dual_momentum_signal.py not found"}

    try:
        rc, stdout, stderr = run_script(script, timeout=60)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=503, detail="Signal script timed out (yfinance slow?)")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    if rc != 0:
        raise HTTPException(
            status_code=503,
            detail=f"Signal script failed: {stderr.strip()[:500]}"
        )

    # Parse the stdout output
    signal = None
    returns: dict[str, float] = {}
    ranked: list[str] = []
    abs_filter = None

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("SIGNAL:"):
            signal = line.split(":", 1)[1].strip()
        elif "_12M:" in line:
            parts = line.split(":", 1)
            ticker = parts[0].replace("_12M", "").strip()
            val_str = parts[1].strip().replace("%", "").replace("+", "")
            try:
                returns[ticker] = float(val_str)
            except ValueError:
                pass
        elif line.startswith("ABSOLUTE_FILTER:"):
            abs_filter = line.split(":", 1)[1].strip()
        elif line.startswith("RANKED:"):
            ranked_str = line.split(":", 1)[1].strip()
            ranked = [t.strip() for t in ranked_str.split(">")]

    # Build ranking array in spec format: [{ticker, return_12m}, ...]
    ranking = []
    if ranked:
        for t in ranked:
            ranking.append({"ticker": t, "return_12m": returns.get(t)})
    elif returns:
        for t, r in sorted(returns.items(), key=lambda x: x[1] or -999, reverse=True):
            ranking.append({"ticker": t, "return_12m": r})

    spy_12m = returns.get("SPY")

    return {
        "signal": signal,
        "absolute_filter": abs_filter,
        "spy_12m": spy_12m,
        "ranking": ranking,
        # legacy fields kept for compatibility
        "returns_12m": returns,
        "ranked": ranked,
        "raw": stdout.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/rebalance-status")
async def get_rebalance_status():
    """
    Run is_rebalance_day.py and return days until next rebalance.
    """
    script = SCRIPTS_DIR / "is_rebalance_day.py"
    if not script.exists():
        return {"error": "not_implemented", "detail": "is_rebalance_day.py not found"}

    try:
        rc, stdout, stderr = run_script(script, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    is_rebalance_day = (rc == 0)

    # Parse days-until from stdout
    days_until = None
    rebalance_date = None
    today_str = None

    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("Today"):
            today_str = line.split(":", 1)[1].strip()
        elif line.startswith("Rebalance day"):
            rebalance_date = line.split(":", 1)[1].strip()
        elif "trading day(s) until rebalance" in line:
            m = re.search(r"(\d+) trading day", line)
            if m:
                days_until = int(m.group(1))

    return {
        "is_rebalance_day": is_rebalance_day,
        "days_until_rebalance": days_until,
        "next_rebalance_date": rebalance_date,   # spec field name
        "rebalance_date": rebalance_date,         # legacy alias
        "today": today_str,
        "raw": stdout.strip(),
    }


@app.get("/api/strategy")
async def get_strategy():
    """Return the current TRADING-STRATEGY.md content."""
    content = read_memory("TRADING-STRATEGY.md", "Strategy file not found.")
    return {"content": content}


# ---------------------------------------------------------------------------
# Routes — existing routes (unchanged)
# ---------------------------------------------------------------------------

@app.get("/api/ping")
async def ping(_: None = Depends(verify_password)):
    return {"ok": True}


@app.get("/api/account")
async def get_account(_: None = Depends(verify_password)):
    try:
        return run_alpaca("account")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"error": "alpaca_unavailable", "detail": str(e)})


@app.get("/api/positions")
async def get_positions(_: None = Depends(verify_password)):
    try:
        return run_alpaca("positions")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"error": "alpaca_unavailable", "detail": str(e)})


@app.get("/api/orders")
async def get_orders(_: None = Depends(verify_password)):
    try:
        return run_alpaca("orders", "open")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"error": "alpaca_unavailable", "detail": str(e)})


@app.get("/api/equity-history")
async def get_equity_history(_: None = Depends(verify_password)):
    try:
        return alpaca_api("GET", "/v2/account/portfolio/history?period=1M&timeframe=1D")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"error": "alpaca_unavailable", "detail": str(e)})


@app.get("/api/status")
async def get_status():
    trade_log = read_memory("TRADE-LOG.md")
    today = date.today()
    today_iso = today.isoformat()

    # Last git commit
    try:
        git_result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%ci"],
            capture_output=True, text=True, timeout=5
        )
        last_commit = git_result.stdout.strip() if git_result.returncode == 0 else None
    except Exception:
        last_commit = None

    # Compute commit age
    stale = False
    if last_commit:
        try:
            commit_dt = datetime.fromisoformat(last_commit.replace(" ", "T", 1).rsplit(" ", 1)[0])
            age_h = (datetime.now() - commit_dt).total_seconds() / 3600
            stale = age_h > 26
        except Exception:
            pass

    # Rebalance info from TRADE-LOG
    rebalance_entries = re.findall(r"### (\d{4}-\d{2}-\d{2}) — Rebalance", trade_log)
    last_rebalance = rebalance_entries[-1] if rebalance_entries else None

    # Dual momentum backtest result
    backtest_files = sorted(BACKTEST_RESULTS_DIR.glob("dual_momentum_*.json")) if BACKTEST_RESULTS_DIR.exists() else []
    dm_verdict = None
    dm_cagr = None
    if backtest_files:
        try:
            result = json.loads(backtest_files[-1].read_text())
            dm_verdict = result.get("verdict")
            dm_cagr = result.get("metrics", {}).get("cagr")
        except Exception:
            pass

    paused = (MEMORY_DIR / "PAUSE-FLAG.txt").exists()

    return {
        "paused": paused,
        "last_commit": last_commit,
        "stale": stale,
        "strategy": "Dual Momentum ETF Rotation",
        "last_rebalance": last_rebalance,
        "rebalance_count": len(rebalance_entries),
        "backtest": {
            "verdict": dm_verdict or "PASS",   # passed on Jun 7 2026
            "cagr": dm_cagr,
            "strategy": "Dual Momentum",
        },
    }


@app.get("/api/backtest")
async def get_backtest():
    if not BACKTEST_RESULTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No backtest results directory")
    # Prefer dual_momentum results
    files = sorted(BACKTEST_RESULTS_DIR.glob("dual_momentum_*.json"))
    if not files:
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
        if any(w in ll for w in ["rebalance", "buy", "bought", "entered"]):
            return "buy"
        if any(w in ll for w in ["sell", "sold", "closed"]):
            return "sell"
        if any(w in ll for w in ["loss", "-$", "down", "red"]):
            return "loss"
        if any(w in ll for w in ["profit", "gain", "+$", "up", "green"]):
            return "profit"
        if any(w in ll for w in ["warn", "alert", "risk", "pause", "halt"]):
            return "warning"
        return "info"

    return {"alerts": [{"text": l, "type": classify(l)} for l in recent]}


@app.get("/api/rebalance-history")
async def get_rebalance_history(_: None = Depends(verify_password)):
    """
    Parse TRADE-LOG.md for rebalance entries.
    Returns list of {date, sold, bought, notes}.
    """
    trade_log = read_memory("TRADE-LOG.md", "")
    entries = []

    # Match rebalance entries: "### YYYY-MM-DD — Rebalance"
    pattern = re.compile(
        r"### (\d{4}-\d{2}-\d{2}) — Rebalance\n(.*?)(?=###|\Z)", re.DOTALL
    )
    for m in pattern.finditer(trade_log):
        entry_date = m.group(1)
        body = m.group(2)

        sold = None
        bought = None

        sold_m = re.search(r"Sold:\s*(\w+)\s*@\s*\$?([\d.]+)", body)
        bought_m = re.search(r"Bought:\s*(\w+)\s*@\s*\$?([\d.]+)", body)

        if sold_m:
            sold = {"ticker": sold_m.group(1), "price": float(sold_m.group(2))}
        if bought_m:
            bought = {"ticker": bought_m.group(1), "price": float(bought_m.group(2))}

        entries.append({
            "date": entry_date,
            "sold": sold,
            "bought": bought,
        })

    return {"entries": entries}


@app.get("/api/calendar")
async def get_calendar(_: None = Depends(verify_password)):
    trade_log = read_memory("TRADE-LOG.md", "")
    today = date.today()
    pnl_by_day: dict[str, float] = {}

    for entry_date, pnl_str in re.findall(
        r"### (\d{4}-\d{2}-\d{2}) — EOD.*?\*\*Phase P&L:\*\*.*?\$?([-\d,\.]+)",
        trade_log,
    ):
        try:
            d = date.fromisoformat(entry_date)
            if d.year == today.year and d.month == today.month:
                pnl_by_day[entry_date] = float(pnl_str.replace(",", ""))
        except ValueError:
            pass

    return {
        "year": today.year,
        "month": today.month,
        "pnl_by_day": pnl_by_day,
        "today": today.isoformat(),
    }


@app.get("/api/quote")
async def get_quote():
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
            {"id": 1, "title": "Reach $110k Equity (10% return)", "target": 110000, "current": 100000, "unit": "$"},
            {"id": 2, "title": "Complete 6 Rebalances", "target": 6, "current": 0, "unit": "rebalances"},
            {"id": 3, "title": "Beat SPY Monthly", "target": 12, "current": 0, "unit": "months"},
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
