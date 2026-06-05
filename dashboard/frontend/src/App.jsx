import { useState, useEffect } from 'react'
import { TrendingUp, DollarSign, BarChart2, Activity, Shield } from 'lucide-react'

import TopBar from './components/TopBar'
import StatCard from './components/StatCard'
import PositionsPanel from './components/PositionsPanel'
import BotStatusPanel from './components/BotStatusPanel'
import CalendarPanel from './components/CalendarPanel'
import AlertsFeed from './components/AlertsFeed'
import QuickControls from './components/QuickControls'
import LifeHub from './components/LifeHub'
import { useApi, getPassword, apiFetch } from './hooks/useApi'
import { fmt$, fmtPct, pnlColor } from './utils/market'

// ---------------------------------------------------------------------------
// Password Gate
// ---------------------------------------------------------------------------
function PasswordGate({ onAuth }) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const API_PW = import.meta.env.VITE_DASHBOARD_PASSWORD

  const attempt = async () => {
    setLoading(true)
    setError('')
    try {
      localStorage.setItem('dashboard_password', pw)
      const res = await apiFetch('/api/ping')
      if (res?.ok) {
        onAuth()
      } else {
        localStorage.removeItem('dashboard_password')
        setError('Wrong password — try again')
      }
    } catch {
      // If no password is configured on backend, /api/ping still returns ok
      onAuth()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-card border border-border rounded-2xl p-8 shadow-2xl">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="p-3 rounded-full bg-purple-500/20 border border-purple-500/30">
            <Shield className="w-7 h-7 text-purple-400" />
          </div>
          <h1 className="text-white font-bold text-xl">Nick's Trading Hub</h1>
          <span className="text-xs text-slate-500 uppercase tracking-wider">Paper Trading Dashboard</span>
        </div>

        <div className="flex flex-col gap-3">
          <input
            type="password"
            value={pw}
            onChange={e => setPw(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && attempt()}
            placeholder="Enter dashboard password"
            autoFocus
            className="w-full bg-navy-800 border border-border rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 text-sm"
          />
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            onClick={attempt}
            disabled={loading}
            className="w-full py-3 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-semibold text-sm transition-colors disabled:opacity-50"
          >
            {loading ? 'Checking…' : 'Enter'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Stat row — account + positions data
// ---------------------------------------------------------------------------
function StatsRow() {
  const { data: account } = useApi('/api/account', 30000)
  const { data: positions } = useApi('/api/positions', 30000)

  const equity = parseFloat(account?.equity ?? 0)
  const lastEq  = parseFloat(account?.last_equity ?? equity)
  const dayPnl  = equity - lastEq
  const dayPct  = lastEq > 0 ? (dayPnl / lastEq) * 100 : 0
  const posCount = Array.isArray(positions) ? positions.length : 0
  const dtCount  = parseInt(account?.daytrade_count ?? 0)

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        title="Portfolio Equity"
        value={fmt$(equity)}
        sub="Total account value"
        icon={DollarSign}
      />
      <StatCard
        title="Day P&L"
        value={fmt$(dayPnl)}
        sub={fmtPct(dayPct)}
        valueClass={pnlColor(dayPnl)}
        icon={TrendingUp}
      />
      <StatCard
        title="Open Positions"
        value={posCount}
        sub={`${6 - posCount} slots remaining`}
        valueClass="text-purple-300"
        icon={BarChart2}
      />
      <StatCard
        title="Day Trades Used"
        value={`${dtCount}/3`}
        sub="Rolling 5-day window"
        valueClass={dtCount >= 3 ? 'text-red-400' : dtCount >= 2 ? 'text-yellow-400' : 'text-white'}
        icon={Activity}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Last-refresh indicator
// ---------------------------------------------------------------------------
function RefreshBadge() {
  const [t, setT] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setT(new Date()), 30000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className="text-xs text-slate-600 select-none">
      Auto-refreshes every 30s · Last: {t.toLocaleTimeString()}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main layout
// ---------------------------------------------------------------------------
export default function App() {
  const [authed, setAuthed] = useState(!!getPassword())

  useEffect(() => {
    const handler = () => setAuthed(false)
    window.addEventListener('auth-required', handler)
    return () => window.removeEventListener('auth-required', handler)
  }, [])

  if (!authed) return <PasswordGate onAuth={() => setAuthed(true)} />

  return (
    <div className="min-h-screen bg-navy-900 text-white">
      <TopBar />

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-6 flex flex-col gap-6">
        {/* Row 1 — Stat cards */}
        <StatsRow />

        {/* Row 2 — Positions + Bot status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <PositionsPanel />
          <BotStatusPanel />
        </div>

        {/* Row 3 — Calendar + Alerts + Controls */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <CalendarPanel />
          <AlertsFeed />
          <QuickControls />
        </div>

        {/* Life Hub */}
        <LifeHub />

        {/* Footer */}
        <div className="flex justify-end pb-2">
          <RefreshBadge />
        </div>
      </main>
    </div>
  )
}
