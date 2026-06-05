import { useApi } from '../hooks/useApi'
import { CheckCircle, Clock, Pause, Play, Database, AlertTriangle, Heart } from 'lucide-react'

function RoutineRow({ label, done, lastRun }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div>
        <span className="text-sm text-slate-300">{label}</span>
        {lastRun && (
          <div className="text-xs text-slate-600 mt-0.5">Last: {lastRun}</div>
        )}
      </div>
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

function HeartbeatRow({ lastCommit }) {
  if (!lastCommit) return null

  // Parse the commit timestamp and compute age
  const commitDate = new Date(lastCommit)
  const ageMs = Date.now() - commitDate.getTime()
  const ageH  = ageMs / 1000 / 3600
  const ageStr = ageH < 1
    ? `${Math.round(ageMs / 60000)}m ago`
    : ageH < 24
    ? `${Math.round(ageH)}h ago`
    : `${Math.round(ageH / 24)}d ago`

  // Go red if last commit was more than 26 hours ago on a weekday
  const now = new Date()
  const isWeekday = now.getDay() >= 1 && now.getDay() <= 5
  const stale = isWeekday && ageH > 26

  return (
    <div className={`flex items-center justify-between px-3 py-2 rounded-lg border ${
      stale
        ? 'border-red-500/40 bg-red-500/10'
        : 'border-green-500/30 bg-green-500/10'
    }`}>
      <div className="flex items-center gap-1.5">
        <Heart className={`w-3.5 h-3.5 ${stale ? 'text-red-400' : 'text-green-400'}`} />
        <span className={`text-xs font-medium ${stale ? 'text-red-400' : 'text-green-400'}`}>
          {stale ? 'Stale — no recent commit' : 'Heartbeat OK'}
        </span>
      </div>
      <span className="text-xs text-slate-500 font-mono">{ageStr}</span>
    </div>
  )
}

export default function BotStatusPanel() {
  const { data, loading } = useApi('/api/status', 30000)

  const paused       = data?.paused ?? false
  const routines     = data?.routines ?? {}
  const backtest     = data?.backtest ?? {}
  const lastCommit   = data?.last_commit ?? null

  const routineList = [
    { key: 'pre_market', label: 'Pre-Market Research' },
    { key: 'market_open', label: 'Market Open' },
    { key: 'midday', label: 'Midday Check' },
    { key: 'eod', label: 'EOD Summary' },
  ]

  const backtestPct = Math.min(100, Math.round((backtest.count || 0) / 10 * 100))
  const verdict     = backtest.verdict  // 'PASS' | 'FAIL' | null

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
          {/* Heartbeat */}
          <HeartbeatRow lastCommit={lastCommit} />

          {/* Routine rows */}
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Today's Routines</div>
            {routineList.map(r => (
              <RoutineRow
                key={r.key}
                label={r.label}
                done={routines[r.key]?.done_today ?? false}
                lastRun={routines[r.key]?.last_run ?? null}
              />
            ))}
          </div>

          {/* Backtest */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-xs text-slate-500 uppercase tracking-wider">Backtest</span>
              </div>
              <div className="flex items-center gap-2">
                {verdict && (
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    verdict === 'PASS'
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : 'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}>
                    {verdict}
                  </span>
                )}
                <span className="text-xs font-mono text-slate-300">{backtest.count || 0} runs</span>
              </div>
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
            {verdict === 'FAIL' && (
              <div className="mt-2 flex items-start gap-1.5 text-xs text-orange-400">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>Strategy has not passed OOS validation — ORB not live</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
