import { useState } from 'react'
import { apiFetch, useApi } from '../hooks/useApi'
import { RefreshCw, Pause, Play, BarChart2, XCircle, Quote } from 'lucide-react'

function ConfirmModal({ message, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-navy-700 border border-border rounded-2xl p-6 max-w-sm w-full mx-4 shadow-2xl">
        <div className="flex items-center gap-2 mb-3">
          <XCircle className="w-5 h-5 text-red-400" />
          <span className="text-white font-semibold">Confirm Action</span>
        </div>
        <p className="text-slate-300 text-sm mb-5">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2 rounded-lg border border-border text-slate-300 text-sm hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white text-sm font-semibold transition-colors"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

function CtrlButton({ onClick, loading, disabled, children, variant = 'default' }) {
  const variants = {
    default: 'border-border text-slate-300 hover:bg-slate-700 hover:text-white',
    green:   'border-green-600/50 text-green-400 hover:bg-green-600/20',
    orange:  'border-orange-600/50 text-orange-400 hover:bg-orange-600/20',
    purple:  'border-purple-600/50 text-purple-400 hover:bg-purple-600/20',
    red:     'border-red-600/50 text-red-400 hover:bg-red-600/20',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`w-full flex items-center gap-2.5 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors disabled:opacity-50 ${variants[variant]}`}
    >
      {children}
    </button>
  )
}

export default function QuickControls() {
  const { data: statusData, refetch: refetchStatus } = useApi('/api/status', 30000)
  const { data: quoteData } = useApi('/api/quote', 0)
  const [busy, setBusy] = useState({})
  const [toast, setToast] = useState(null)
  const [confirm, setConfirm] = useState(null)

  const paused = statusData?.paused ?? false

  function showToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3000)
  }

  async function action(key, fn) {
    setBusy(b => ({ ...b, [key]: true }))
    try {
      await fn()
    } catch (e) {
      showToast(e.message || 'Error', false)
    } finally {
      setBusy(b => ({ ...b, [key]: false }))
    }
  }

  const handleStatus = () => action('status', async () => {
    await refetchStatus()
    showToast('Status refreshed')
  })

  const handlePause = () => action('pause', async () => {
    const ep = paused ? '/api/resume' : '/api/pause'
    await apiFetch(ep, { method: 'POST' })
    await refetchStatus()
    showToast(paused ? 'Bot resumed' : 'Bot paused')
  })

  const handleCloseAll = () => {
    setConfirm({
      message: 'This will close ALL open positions immediately at market price. Are you sure?',
      onConfirm: async () => {
        setConfirm(null)
        await action('closeAll', async () => {
          await apiFetch('/api/close-all', { method: 'POST' })
          showToast('All positions closed')
        })
      },
      onCancel: () => setConfirm(null),
    })
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5 flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Quick Controls</h2>

      <div className="flex flex-col gap-2">
        <CtrlButton onClick={handleStatus} loading={busy.status} variant="default">
          <RefreshCw className={`w-4 h-4 ${busy.status ? 'animate-spin' : ''}`} />
          Refresh Status
        </CtrlButton>

        <CtrlButton onClick={handlePause} loading={busy.pause} variant={paused ? 'green' : 'orange'}>
          {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          {paused ? 'Resume Bot' : 'Pause Bot'}
        </CtrlButton>

        <CtrlButton onClick={() => window.open('/api/backtest', '_blank')} variant="purple">
          <BarChart2 className="w-4 h-4" />
          View Latest Backtest
        </CtrlButton>

        <CtrlButton onClick={handleCloseAll} loading={busy.closeAll} variant="red">
          <XCircle className="w-4 h-4" />
          Close All Positions
        </CtrlButton>
      </div>

      {/* Daily quote */}
      {quoteData && (
        <div className="mt-2 border-t border-border pt-4">
          <div className="flex items-start gap-2">
            <Quote className="w-3.5 h-3.5 text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs text-slate-300 italic leading-relaxed">{quoteData.text}</p>
              <p className="text-xs text-slate-500 mt-1">— {quoteData.author}</p>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg text-sm font-medium shadow-xl transition-all ${
          toast.ok ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.msg}
        </div>
      )}

      {confirm && <ConfirmModal {...confirm} />}
    </div>
  )
}
