import { useApi } from '../hooks/useApi'
import { TrendingUp, TrendingDown, ShoppingCart, DollarSign, AlertTriangle, Info } from 'lucide-react'

const TYPE_CONFIG = {
  buy:     { color: 'text-green-400',  border: 'border-green-500/40',  bg: 'bg-green-500/10',  Icon: ShoppingCart },
  sell:    { color: 'text-yellow-300', border: 'border-yellow-500/40', bg: 'bg-yellow-500/10', Icon: TrendingDown },
  profit:  { color: 'text-green-300',  border: 'border-green-500/30',  bg: 'bg-green-500/8',   Icon: TrendingUp },
  loss:    { color: 'text-red-400',    border: 'border-red-500/40',    bg: 'bg-red-500/10',    Icon: TrendingDown },
  warning: { color: 'text-orange-400', border: 'border-orange-500/40', bg: 'bg-orange-500/10', Icon: AlertTriangle },
  info:    { color: 'text-slate-300',  border: 'border-slate-600',     bg: 'bg-slate-700/30',  Icon: Info },
}

export default function AlertsFeed() {
  const { data, loading } = useApi('/api/alerts', 30000)
  const alerts = data?.alerts ?? []

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Recent Alerts</h2>
        <span className="text-xs text-slate-500">{alerts.length} entries</span>
      </div>

      {loading && <div className="text-slate-500 text-sm">Loading…</div>}

      {!loading && alerts.length === 0 && (
        <div className="text-slate-500 text-sm py-4 text-center">
          No alerts yet — check back after the bot runs
        </div>
      )}

      <div className="flex flex-col gap-2 overflow-y-auto max-h-64">
        {alerts.map((alert, i) => {
          const cfg = TYPE_CONFIG[alert.type] || TYPE_CONFIG.info
          const { color, border, bg, Icon } = cfg
          return (
            <div key={i} className={`flex items-start gap-2.5 p-2.5 rounded-lg border ${border} ${bg}`}>
              <Icon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${color}`} />
              <span className={`text-xs leading-relaxed ${color}`}>{alert.text}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
