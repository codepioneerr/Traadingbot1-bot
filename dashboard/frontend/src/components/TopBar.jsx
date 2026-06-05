import { useState, useEffect } from 'react'
import { getMarketStatus } from '../utils/market'
import { TrendingUp } from 'lucide-react'

export default function TopBar() {
  const [now, setNow] = useState(new Date())
  const status = getMarketStatus()

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  const dateStr = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-border bg-navy-800">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <TrendingUp className="text-purple-400 w-6 h-6" />
        <span className="text-white font-bold text-lg tracking-tight">Nick's Trading Hub</span>
        <span className="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 uppercase tracking-wider">
          Paper Trading
        </span>
      </div>

      {/* Market status + clock */}
      <div className="flex items-center gap-5 text-sm">
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full animate-pulse ${status.dot}`} />
          <span className={`font-medium ${status.color}`}>{status.label}</span>
        </div>
        <span className="font-mono text-white text-base tabular-nums">{timeStr}</span>
        <span className="text-slate-400 hidden sm:block">{dateStr}</span>
      </div>
    </header>
  )
}
