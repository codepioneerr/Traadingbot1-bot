import { useApi } from '../hooks/useApi'

const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']
const DAY_NAMES = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate()
}
function firstDayOfMonth(year, month) {
  return new Date(year, month - 1, 1).getDay()
}

export default function CalendarPanel() {
  const { data, loading } = useApi('/api/calendar', 60000)

  if (loading || !data) {
    return (
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="text-slate-500 text-sm">Loading calendar…</div>
      </div>
    )
  }

  const { year, month, pnl_by_day = {}, trade_days = [], today } = data
  const numDays = daysInMonth(year, month)
  const startDay = firstDayOfMonth(year, month)
  const tradeSet = new Set(trade_days)

  const cells = []
  for (let i = 0; i < startDay; i++) cells.push(null)
  for (let d = 1; d <= numDays; d++) cells.push(d)

  function dayKey(d) {
    return `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
  }

  function dayClass(d) {
    if (!d) return ''
    const key = dayKey(d)
    const pnl = pnl_by_day[key]
    const isToday = key === today
    let bg = ''
    if (pnl != null) bg = pnl >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'
    const border = isToday ? 'ring-2 ring-purple-500' : 'border border-border/50'
    return `${bg} ${border} rounded-lg`
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Monthly P&L</h2>
        <span className="text-sm text-slate-400 font-medium">{MONTH_NAMES[month - 1]} {year}</span>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-1">
        {DAY_NAMES.map(d => (
          <div key={d} className="text-center text-xs text-slate-500 pb-1">{d}</div>
        ))}
        {cells.map((d, i) => {
          if (!d) return <div key={`e-${i}`} />
          const key = dayKey(d)
          const pnl = pnl_by_day[key]
          const hasTrade = tradeSet.has(key)
          return (
            <div
              key={key}
              className={`relative flex flex-col items-center justify-center h-9 text-xs ${dayClass(d)}`}
              title={pnl != null ? `P&L: ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}` : ''}
            >
              <span className={`font-mono ${pnl != null ? (pnl >= 0 ? 'text-green-300' : 'text-red-300') : 'text-slate-400'}`}>
                {d}
              </span>
              {hasTrade && (
                <span className="absolute bottom-0.5 w-1 h-1 rounded-full bg-purple-400" />
              )}
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 pt-1 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded bg-green-500/30" /> Profit</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded bg-red-500/30" /> Loss</span>
        <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full bg-purple-400" /> Trade day</span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded ring-2 ring-purple-500" /> Today</span>
      </div>
    </div>
  )
}
