// Market hours are US Eastern time
export function getMarketStatus() {
  const now = new Date()
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const day = et.getDay() // 0=Sun, 6=Sat
  const h = et.getHours()
  const m = et.getMinutes()
  const mins = h * 60 + m

  if (day === 0 || day === 6) return { label: 'Closed', color: 'text-slate-400', dot: 'bg-slate-500' }

  if (mins >= 240 && mins < 570)  return { label: 'Pre-Market', color: 'text-yellow-400', dot: 'bg-yellow-400' }
  if (mins >= 570 && mins < 960)  return { label: 'Open', color: 'text-green-400', dot: 'bg-green-400' }
  if (mins >= 960 && mins < 1200) return { label: 'After-Hours', color: 'text-blue-400', dot: 'bg-blue-400' }
  return { label: 'Closed', color: 'text-slate-400', dot: 'bg-slate-500' }
}

export function fmt$(n, digits = 2) {
  if (n == null || isNaN(n)) return '—'
  const abs = Math.abs(n)
  return (n < 0 ? '-$' : '$') + abs.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function fmtPct(n, digits = 2) {
  if (n == null || isNaN(n)) return '—'
  return (n >= 0 ? '+' : '') + Number(n).toFixed(digits) + '%'
}

export function pnlColor(n) {
  if (n == null || isNaN(n)) return 'text-slate-400'
  return n >= 0 ? 'text-green-400' : 'text-red-400'
}
