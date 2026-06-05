import { useApi } from '../hooks/useApi'
import { CheckCircle, Clock, Pause, Play, Database } from 'lucide-react'

function RoutineRow({ label, done }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <span className="text-sm text-slate-300">{label}</span>
      {done ? (
        <span className="flex items-center gap-1 text-green-400 text-xs font-medium">
          <CheckCircle className="w-3.5 h-3.5" /> Done
        </span>
      ) : (
        <span className="flex items-center gap-1 text-slate-500 text-xs">
          <Clock className="w-3.5 h-3.5" /> Pending
        </span>
      )}
    </div>
  )
}

export default function BotStatusPanel() {
  const { data, loading } = useApi('/api/status', 30000)

  const paused = data?.paused ?? false
  const routines = data?.routines ?? {}
  const backtest = data?.backtest ?? {}

  const routineList = [
    { key: 'pre_market', label: 'Pre-Market Research' },
    { key: 'market_open', label: 'Market Open' },
    { key: 'midday', label: 'Midday Check' },
    { key: 'eod', label: 'EOD Summary' },
  ]

  const backtestPct = Math.min(100, Math.round((backtest.count || 0) / 10 * 100))

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Bot Status</h2>
        <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
          paused
            ? 'bg-orange-500/15 text-orange-400 border border-orange-500/30'
            : 'bg-green-500/15 text-green-400 border border-green-500/30'
        }`}>
          {paused ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          {paused ? 'PAUSED' : 'RUNNING'}
        </span>
      </div>

      {loading && <div className="text-slate-500 text-sm">Loading…</div>}

      {!loading && (
        <>
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Today's Routines</div>
            {routineList.map(r => (
              <RoutineRow
                key={r.key}
                label={r.label}
                done={routines[r.key]?.done_today ?? false}
              />
            ))}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-xs text-slate-500 uppercase tracking-wider">Backtest Runs</span>
              </div>
              <span className="text-xs font-mono text-slate-300">{backtest.count || 0} runs</span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-2">
              <div
                className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${backtestPct}%` }}
              />
            </div>
            {backtest.latest_file && (
              <div className="mt-1.5 text-xs text-slate-500 truncate">Latest: {backtest.latest_file}</div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
