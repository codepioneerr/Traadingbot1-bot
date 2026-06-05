export default function StatCard({ title, value, sub, valueClass = 'text-white', icon: Icon }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">{title}</span>
        {Icon && <Icon className="w-4 h-4 text-slate-500" />}
      </div>
      <div className={`text-2xl font-bold font-mono tabular-nums ${valueClass}`}>{value ?? '—'}</div>
      {sub && <div className="text-xs text-slate-400">{sub}</div>}
    </div>
  )
}
