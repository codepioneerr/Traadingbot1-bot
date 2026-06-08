import { useState, useEffect, useCallback } from 'react'
import { Shield, RefreshCw, TrendingUp, Clock, Activity, CheckCircle } from 'lucide-react'
import TopBar from './components/TopBar'
import { useApi, apiFetch, getPassword } from './hooks/useApi'
import { fmt$, fmtPct, pnlColor } from './utils/market'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const TICKER_NAMES = {
  SPY: 'SPDR S&P 500 ETF',
  QQQ: 'Invesco Nasdaq-100 ETF',
  IWM: 'iShares Russell 2000 ETF',
  TLT: 'iShares 20+ Year Treasury ETF',
  GLD: 'SPDR Gold Shares',
  SHY: 'iShares 1-3 Year Treasury ETF (Cash)',
}

const STARTING_EQUITY = 100_000
const POLL_INTERVAL = 60_000  // 60 seconds

// ---------------------------------------------------------------------------
// Shared UI primitives
// ---------------------------------------------------------------------------
function Card({ children, className = '' }) {
  return (
    <div className={`bg-card border border-border rounded-2xl p-5 flex flex-col gap-3 ${className}`}>
      {children}
    </div>
  )
}

function CardTitle({ children, icon: Icon }) {
  return (
    <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {children}
    </div>
  )
}

function Skeleton({ className = 'h-4 w-2/3' }) {
  return <div className={`bg-navy-700 animate-pulse rounded ${className}`} />
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center gap-2 py-4 text-center">
      <span className="text-slate-500 text-sm">Unable to load — backend unavailable</span>
      {message && <span className="text-slate-600 text-xs font-mono truncate max-w-full">{message}</span>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
        >
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Panel 1: Current Position
// ---------------------------------------------------------------------------
function CurrentPositionPanel() {
  const { data: positions, loading: pLoad, error: pErr, refetch: pRefetch } = useApi('/api/positions', POLL_INTERVAL)
  const { data: account, loading: aLoad, error: aErr, refetch: aRefetch } = useApi('/api/account', POLL_INTERVAL)

  const loading = pLoad || aLoad
  const error = pErr || aErr
  const refetch = useCallback(() => { pRefetch(); aRefetch() }, [pRefetch, aRefetch])

  const pos = Array.isArray(positions) ? positions[0] : null
  const ticker = pos?.symbol
  const fullName = ticker ? (TICKER_NAMES[ticker] || ticker) : null
  const entryPrice = pos ? parseFloat(pos.avg_entry_price || pos.avg_cost_basis || 0) : 0
  const currentPrice = pos ? parseFloat(pos.current_price || 0) : 0
  const qty = pos ? parseFloat(pos.qty || 0) : 0
  const marketValue = pos ? parseFloat(pos.market_value || 0) : 0
  const unrealizedPnl = pos ? parseFloat(pos.unrealized_pl || 0) : 0
  const unrealizedPct = entryPrice > 0 ? ((currentPrice - entryPrice) / entryPrice) * 100 : 0

  return (
    <Card>
      <CardTitle icon={TrendingUp}>Current Position</CardTitle>
      {loading ? (
        <div className="flex flex-col gap-2 mt-1">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-5 w-32" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : !pos ? (
        <div className="flex flex-col gap-1 py-2">
          <span className="text-slate-400 text-sm italic">No position held</span>
          <span className="text-slate-600 text-xs">Next rebalance will establish a position.</span>
        </div>
      ) : (
        <>
          <div className="flex items-end gap-3">
            <span className="text-4xl font-bold text-white font-mono">{ticker}</span>
            <span className="text-slate-400 text-sm mb-1">{fullName}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-1">
            <div>
              <div className="text-xs text-slate-500 mb-0.5">Entry price</div>
              <div className="text-white font-mono text-sm">{fmt$(entryPrice)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-0.5">Current price</div>
              <div className="text-white font-mono text-sm">{fmt$(currentPrice)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-0.5">Shares</div>
              <div className="text-white font-mono text-sm">{qty.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 mb-0.5">Market value</div>
              <div className="text-white font-mono text-sm">{fmt$(marketValue)}</div>
            </div>
          </div>
          <div className={`text-lg font-bold font-mono mt-1 ${pnlColor(unrealizedPnl)}`}>
            {fmtPct(unrealizedPct)} ({fmt$(unrealizedPnl)})
          </div>
        </>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Panel 2: Next Rebalance
// ---------------------------------------------------------------------------
function RebalanceCountdownPanel() {
  const { data, loading, error, refetch } = useApi('/api/rebalance-status', POLL_INTERVAL)

  const isRebalanceDay = data?.is_rebalance_day
  const daysUntil = data?.days_until_rebalance
  const nextDate = data?.next_rebalance_date

  const formattedDate = nextDate
    ? (() => {
        try {
          return new Date(nextDate + 'T12:00:00').toLocaleDateString('en-US', {
            month: 'long', day: 'numeric', year: 'numeric'
          })
        } catch { return nextDate }
      })()
    : null

  return (
    <Card>
      <CardTitle icon={Clock}>Next Rebalance</CardTitle>
      {loading ? (
        <div className="flex flex-col gap-2 mt-1">
          <Skeleton className="h-16 w-28" />
          <Skeleton className="h-4 w-36" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : isRebalanceDay ? (
        <div className="flex flex-col gap-2 py-2">
          <div className="text-amber-400 text-2xl font-bold animate-pulse">TODAY IS REBALANCE DAY</div>
          <div className="text-amber-300 text-sm">Run the rebalance routine now.</div>
        </div>
      ) : (
        <>
          <div className="flex items-end gap-2 mt-1">
            <span className="text-6xl font-bold text-white font-mono tabular-nums">
              {daysUntil ?? '—'}
            </span>
            <span className="text-slate-400 text-base mb-2">
              {daysUntil === 1 ? 'trading day' : 'trading days'}
            </span>
          </div>
          <div className="text-slate-300 text-sm">until rebalance</div>
          {formattedDate && (
            <div className="text-slate-400 text-xs mt-1">{formattedDate}</div>
          )}
        </>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Panel 3: Current Signal
// ---------------------------------------------------------------------------
function SignalPanel() {
  const { data, loading, error, refetch } = useApi('/api/signal', POLL_INTERVAL)

  const signal = data?.signal
  const absFilter = data?.absolute_filter
  const spy12m = data?.spy_12m
  const ranking = Array.isArray(data?.ranking) ? data.ranking : []

  const maxAbs = ranking.length
    ? Math.max(...ranking.map(r => Math.abs(r.return_12m ?? 0)), 1)
    : 1

  const absFilterPass = absFilter &&
    (absFilter === 'PASS' || absFilter.includes('PASS') || (spy12m != null && spy12m > 0))
  const absFilterColor = absFilterPass
    ? 'text-green-400 bg-green-400/10 border-green-500/30'
    : 'text-red-400 bg-red-400/10 border-red-500/30'

  return (
    <Card>
      <CardTitle icon={Activity}>Current Signal</CardTitle>
      {loading ? (
        <div className="flex flex-col gap-2 mt-1">
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-5 w-48" />
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-sm">Signal:</span>
              <span className="text-2xl font-bold text-amber-400 font-mono">{signal || '—'}</span>
            </div>
            {absFilter && (
              <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${absFilterColor}`}>
                SPY {absFilterPass ? '▲' : '▼'} {spy12m != null ? fmtPct(spy12m) : absFilter}
              </span>
            )}
          </div>

          {ranking.length > 0 && (
            <div className="flex flex-col gap-1.5 mt-1">
              {ranking.map(item => {
                const ret = item.return_12m
                const barPct = ret != null ? (Math.abs(ret) / maxAbs) * 100 : 0
                const isTop = item.ticker === signal
                const isPos = ret != null && ret >= 0
                return (
                  <div key={item.ticker} className="flex items-center gap-2">
                    <span className={`w-9 text-xs font-mono font-bold text-right ${isTop ? 'text-amber-400' : 'text-slate-300'}`}>
                      {item.ticker}
                    </span>
                    <div className="flex-1 h-4 bg-navy-700 rounded overflow-hidden">
                      <div
                        className={`h-full rounded ${isTop ? 'bg-amber-500/80' : isPos ? 'bg-green-500/60' : 'bg-red-500/60'}`}
                        style={{ width: `${barPct}%` }}
                      />
                    </div>
                    <span className={`w-14 text-right text-xs font-mono ${isPos ? 'text-green-400' : 'text-red-400'}`}>
                      {ret != null ? fmtPct(ret) : '—'}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Panel 4: Account Summary
// ---------------------------------------------------------------------------
function AccountSummaryPanel() {
  const { data, loading, error, refetch } = useApi('/api/account', POLL_INTERVAL)

  const equity = data ? parseFloat(data.equity || data.portfolio_value || 0) : 0
  const cash = data ? parseFloat(data.cash || 0) : 0
  const returnDollar = equity - STARTING_EQUITY
  const returnPct = STARTING_EQUITY > 0 ? (returnDollar / STARTING_EQUITY) * 100 : 0

  return (
    <Card>
      <CardTitle icon={TrendingUp}>Account Summary</CardTitle>
      {loading ? (
        <div className="flex flex-col gap-2 mt-1">
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-44" />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <>
          <div className="text-3xl font-bold text-white font-mono tabular-nums">{fmt$(equity)}</div>
          <div className="text-slate-400 text-sm">
            Cash: <span className="text-white font-mono">{fmt$(cash)}</span>
          </div>
          <div className={`text-sm font-semibold ${pnlColor(returnDollar)}`}>
            {fmtPct(returnPct)} ({fmt$(returnDollar)}) since deployment
          </div>
          <div className="text-slate-600 text-xs">Starting equity: {fmt$(STARTING_EQUITY)}</div>
        </>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Panel 5: Rebalance History
// ---------------------------------------------------------------------------
function RebalanceHistoryPanel() {
  const { data, loading, error, refetch } = useApi('/api/rebalance-history', POLL_INTERVAL)
  const entries = data?.entries || []

  return (
    <Card className="col-span-1 md:col-span-2">
      <CardTitle>Rebalance History</CardTitle>
      {loading ? (
        <div className="flex flex-col gap-2 mt-1">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : entries.length === 0 ? (
        <div className="flex flex-col gap-3 py-2">
          <p className="text-slate-400 text-sm">No rebalances yet. First rebalance scheduled June 30, 2026.</p>
          <div className="flex items-center gap-0 mt-2">
            <div className="flex flex-col items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500" />
              <span className="text-xs text-green-400 font-mono whitespace-nowrap">Jun 7</span>
              <span className="text-xs text-slate-500">Deployed</span>
            </div>
            <div className="flex-1 h-0.5 bg-gradient-to-r from-green-500 to-amber-500/40 mx-2" />
            <div className="flex flex-col items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-amber-500/60 border border-amber-400" />
              <span className="text-xs text-amber-400 font-mono whitespace-nowrap">Jun 30</span>
              <span className="text-xs text-slate-500">Rebalance</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs uppercase border-b border-border">
                <th className="text-left pb-2 pr-4">Date</th>
                <th className="text-left pb-2 pr-4">Sold</th>
                <th className="text-left pb-2 pr-4">Bought</th>
                <th className="text-right pb-2">Return on sold</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {entries.map(e => (
                <tr key={e.date} className="text-slate-300">
                  <td className="py-2 pr-4 font-mono text-xs">{e.date}</td>
                  <td className="py-2 pr-4">
                    <span className="font-mono font-bold text-red-400">{e.sold?.ticker || '—'}</span>
                    {e.sold?.price && <span className="text-slate-500 text-xs ml-1">@ {fmt$(e.sold.price)}</span>}
                  </td>
                  <td className="py-2 pr-4">
                    <span className="font-mono font-bold text-green-400">{e.bought?.ticker || '—'}</span>
                    {e.bought?.price && <span className="text-slate-500 text-xs ml-1">@ {fmt$(e.bought.price)}</span>}
                  </td>
                  <td className="py-2 text-right font-mono text-xs text-slate-400">—</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Panel 6: Bot Health strip
// ---------------------------------------------------------------------------
function BotHealthStrip() {
  const { data: botHealth, loading: bLoad, error: bErr } = useApi('/api/health/bot', POLL_INTERVAL)
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    const check = async () => {
      try {
        const r = await apiFetch('/health')
        setBackendOk(r?.status === 'ok')
      } catch {
        setBackendOk(false)
      }
    }
    check()
    const id = setInterval(check, POLL_INTERVAL)
    return () => clearInterval(id)
  }, [])

  const isStale = botHealth?.is_stale || botHealth?.stale
  const hoursAgo = botHealth?.hours_since_commit ?? botHealth?.age_hours
  const hoursStr = hoursAgo != null ? `${hoursAgo}h ago` : 'unknown'

  return (
    <div className="border-t border-border bg-navy-800 px-6 py-3 flex flex-wrap items-center gap-6 text-xs">
      <div className="flex items-center gap-2">
        {bLoad ? (
          <Skeleton className="h-3 w-32" />
        ) : bErr ? (
          <span className="text-slate-500">Bot status unavailable</span>
        ) : (
          <>
            <span className={`w-2 h-2 rounded-full ${isStale ? 'bg-red-500' : 'bg-green-500 animate-pulse'}`} />
            <span className={isStale ? 'text-red-400' : 'text-slate-300'}>
              {isStale ? `Bot stale — last commit ${hoursStr}` : `Bot healthy — last commit ${hoursStr}`}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${backendOk === null ? 'bg-slate-600' : backendOk ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className={backendOk ? 'text-slate-300' : 'text-red-400'}>
          Railway backend: {backendOk === null ? 'checking…' : backendOk ? 'online' : 'offline'}
        </span>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <CheckCircle className="w-3 h-3 text-green-400" />
        <span className="text-slate-400">Dual Momentum ETF Rotation</span>
        <span className="text-green-400 font-semibold">Backtested PASS (2005–2026)</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Password Gate
// ---------------------------------------------------------------------------
function PasswordGate({ onAuth }) {
  const [pw, setPw] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const attempt = async () => {
    setLoading(true)
    setError('')
    try {
      localStorage.setItem('dashboard_password', pw)
      await apiFetch('/api/ping')
      onAuth()
    } catch {
      // If backend has no password configured, still let through
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
          <span className="text-xs text-slate-500 uppercase tracking-wider">Dual Momentum ETF Rotation</span>
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
// Main Dashboard
// ---------------------------------------------------------------------------
function Dashboard() {
  return (
    <div className="min-h-screen bg-navy-900 flex flex-col">
      <TopBar />
      <main className="flex-1 p-4 md:p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-min">
        <CurrentPositionPanel />
        <RebalanceCountdownPanel />
        <SignalPanel />
        <AccountSummaryPanel />
        <RebalanceHistoryPanel />
      </main>
      <BotHealthStrip />
    </div>
  )
}

// ---------------------------------------------------------------------------
// App root
// ---------------------------------------------------------------------------
export default function App() {
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    if (getPassword()) setAuthed(true)
    const handler = () => setAuthed(false)
    window.addEventListener('auth-required', handler)
    return () => window.removeEventListener('auth-required', handler)
  }, [])

  if (!authed) return <PasswordGate onAuth={() => setAuthed(true)} />
  return <Dashboard />
}
