import { useApi } from '../hooks/useApi'
import { fmt$, fmtPct, pnlColor } from '../utils/market'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

function EquityChart() {
  const { data, loading } = useApi('/api/equity-history', 30000)

  if (loading) return <div className="h-28 flex items-center justify-center text-slate-500 text-xs">Loading chart…</div>
  if (!data?.timestamp?.length) return <div className="h-28 flex items-center justify-center text-slate-500 text-xs">No equity data today</div>

  const base = data.base_value || data.equity?.[0] || 0
  const chartData = data.timestamp.map((ts, i) => ({
    t: new Date(ts * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),
    equity: data.equity?.[i] ?? null,
  })).filter(d => d.equity !== null)

  const min = Math.min(...chartData.map(d => d.equity))
  const max = Math.max(...chartData.map(d => d.equity))
  const last = chartData[chartData.length - 1]?.equity ?? base
  const color = last >= base ? '#4ade80' : '#f87171'

  return (
    <div className="h-32">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="t"
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[min * 0.9995, max * 1.0005]}
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={v => `$${(v / 1000).toFixed(1)}k`}
            width={48}
          />
          <Tooltip
            contentStyle={{ background: '#131f35', border: '1px solid #1e2f4a', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={v => [fmt$(v), 'Equity']}
          />
          <ReferenceLine y={base} stroke="#475569" strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="equity"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function PositionsPanel() {
  const { data: positions, loading } = useApi('/api/positions', 30000)
  const rows = Array.isArray(positions) ? positions : []

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Open Positions</h2>

      {loading && <div className="text-slate-500 text-sm">Loading…</div>}

      {!loading && rows.length === 0 && (
        <div className="text-slate-500 text-sm">No open positions</div>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-border">
                {['Symbol', 'Qty', 'Avg Cost', 'Current', 'Day Chg', 'Unreal. P&L'].map(h => (
                  <th key={h} className="pb-2 text-left font-medium pr-3 last:pr-0">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(p => {
                const unreal = parseFloat(p.unrealized_pl || 0)
                const dayChg = parseFloat(p.change_today || 0)
                return (
                  <tr key={p.symbol} className="border-b border-border/50 last:border-0">
                    <td className="py-2 pr-3 font-bold text-purple-300">{p.symbol}</td>
                    <td className="py-2 pr-3 font-mono text-slate-300">{parseFloat(p.qty).toFixed(0)}</td>
                    <td className="py-2 pr-3 font-mono text-slate-300">{fmt$(parseFloat(p.avg_entry_price))}</td>
                    <td className="py-2 pr-3 font-mono text-slate-300">{fmt$(parseFloat(p.current_price))}</td>
                    <td className={`py-2 pr-3 font-mono ${pnlColor(dayChg)}`}>{fmtPct(parseFloat(p.change_today_pct) * 100)}</td>
                    <td className={`py-2 font-mono font-semibold ${pnlColor(unreal)}`}>{fmt$(unreal)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div>
        <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Equity Curve — Today</div>
        <EquityChart />
      </div>
    </div>
  )
}
