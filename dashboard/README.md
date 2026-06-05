# Trading Hub Dashboard

Full-stack personal trading & life dashboard.

- **Backend:** FastAPI (Python) → Railway
- **Frontend:** React + Vite + Tailwind → Vercel

---

## Local Development

### Backend

```bash
cd dashboard/backend
pip install fastapi "uvicorn[standard]" pydantic

# Copy and fill in env vars (or just source the repo root .env)
uvicorn main:app --reload --port 8000
# API available at http://localhost:8000
```

### Frontend

```bash
cd dashboard/frontend
npm install

# Create .env.local:
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# Opens at http://localhost:3000
```

---

## Deployment

### 1 — Deploy Backend to Railway

**Prerequisites:** `npm install -g @railway/cli` and `railway login`

```bash
# From repo root — create a new Railway service pointing at dashboard/backend/
railway init          # link to existing project or create new
railway up            # deploys from current directory

# Or via Railway dashboard:
# New Service → Deploy from GitHub Repo → Root Directory: dashboard/backend
```

**Environment variables to set in Railway:**

| Variable | Value |
|----------|-------|
| `ALPACA_API_KEY` | Your Alpaca paper key |
| `ALPACA_SECRET_KEY` | Your Alpaca paper secret |
| `ALPACA_ENDPOINT` | `https://paper-api.alpaca.markets` |
| `ALPACA_DATA_ENDPOINT` | `https://data.alpaca.markets` |
| `DASHBOARD_PASSWORD` | A password of your choice |
| `FRONTEND_URL` | Your Vercel URL (e.g. `https://trading-hub.vercel.app`) |
| `REPO_ROOT` | `/app` (Railway clones the full repo here) |
| `PORT` | Set automatically by Railway |

> **REPO_ROOT note:** Railway clones the repo to `/app`. The backend is at
> `/app/dashboard/backend/main.py`, so `REPO_ROOT=/app` points correctly to
> `scripts/` and `memory/`.

---

### 2 — Deploy Frontend to Vercel

```bash
# Install Vercel CLI (optional — you can also connect via dashboard)
npm install -g vercel

cd dashboard/frontend
vercel --prod
# Follow prompts: Framework = Vite, Root = dashboard/frontend, Build = npm run build, Output = dist
```

**Environment variables to set in Vercel:**

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | Your Railway backend URL (no trailing slash) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/ping` | Auth check |
| GET | `/api/account` | Alpaca account data |
| GET | `/api/positions` | Open positions |
| GET | `/api/orders` | Open orders |
| GET | `/api/equity-history` | Today's equity curve (5-min bars) |
| GET | `/api/status` | Bot routine status + backtest info |
| GET | `/api/backtest` | Latest backtest JSON |
| GET | `/api/alerts` | Last 10 entries from TELEGRAM-LOG.md |
| GET | `/api/calendar` | Monthly P&L by day |
| GET | `/api/quote` | Daily motivational quote |
| POST | `/api/pause` | Write memory/PAUSE-FLAG.txt |
| POST | `/api/resume` | Delete memory/PAUSE-FLAG.txt |
| POST | `/api/close-all` | Close all Alpaca positions |
| GET | `/api/goals` | Read memory/GOALS.json |
| POST | `/api/goals` | Write memory/GOALS.json |
| GET | `/api/notes` | Read memory/DAILY-NOTES.md |
| POST | `/api/notes` | Write memory/DAILY-NOTES.md |

---

## Notes

- The dashboard is **read-only** except for pause/resume, close-all, goals, and notes.
- Backtest files in `backtest/` and trading routines are never modified.
- The frontend auto-refreshes every 30 seconds.
- Password is stored in `localStorage` after first successful login.
