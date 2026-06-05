import { useState, useEffect } from 'react'
import { apiFetch, useApi } from '../hooks/useApi'
import { ChevronDown, ChevronUp, Target, FileText, Calendar, Save } from 'lucide-react'

function GoalBar({ goal, onUpdate }) {
  const pct = Math.min(100, Math.round((goal.current / goal.target) * 100)) || 0
  const color = pct >= 100 ? 'bg-green-500' : pct >= 60 ? 'bg-purple-500' : 'bg-blue-500'

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-300 font-medium">{goal.title}</span>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={goal.current}
            onChange={e => onUpdate({ ...goal, current: parseFloat(e.target.value) || 0 })}
            className="w-20 text-xs text-right bg-navy-700 border border-border rounded px-2 py-1 text-slate-300 font-mono focus:outline-none focus:border-purple-500"
          />
          <span className="text-xs text-slate-500">/ {goal.target} {goal.unit}</span>
        </div>
      </div>
      <div className="w-full bg-slate-700/50 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-slate-500 text-right">{pct}% complete</div>
    </div>
  )
}

function GoalsSection() {
  const { data: initialGoals } = useApi('/api/goals', 0)
  const [goals, setGoals] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (initialGoals && !goals) setGoals(initialGoals)
  }, [initialGoals])

  const updateGoal = updated => {
    setGoals(prev => prev.map(g => g.id === updated.id ? updated : g))
    setSaved(false)
  }

  const saveGoals = async () => {
    setSaving(true)
    try {
      await apiFetch('/api/goals', { method: 'POST', body: JSON.stringify({ goals }) })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  if (!goals) return <div className="text-slate-500 text-sm">Loading goals…</div>

  return (
    <div className="flex flex-col gap-4">
      {goals.map(g => <GoalBar key={g.id} goal={g} onUpdate={updateGoal} />)}
      <button
        onClick={saveGoals}
        disabled={saving}
        className="self-end flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
      >
        <Save className="w-3.5 h-3.5" />
        {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Goals'}
      </button>
    </div>
  )
}

function NotesSection() {
  const { data } = useApi('/api/notes', 0)
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data?.content != null) setContent(data.content)
  }, [data])

  const save = async () => {
    setSaving(true)
    try {
      await apiFetch('/api/notes', { method: 'POST', body: JSON.stringify({ content }) })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={content}
        onChange={e => { setContent(e.target.value); setSaved(false) }}
        rows={6}
        placeholder="Write your daily notes, observations, trade thesis…"
        className="w-full bg-navy-800 border border-border rounded-lg p-3 text-sm text-slate-300 placeholder-slate-600 resize-none focus:outline-none focus:border-purple-500 leading-relaxed"
      />
      <button
        onClick={save}
        disabled={saving}
        className="self-end flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
      >
        <Save className="w-3.5 h-3.5" />
        {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Notes'}
      </button>
    </div>
  )
}

export default function LifeHub() {
  const [open, setOpen] = useState(false)

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      {/* Collapse toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 bg-navy-800 hover:bg-navy-700 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Life Hub</span>
          <span className="text-xs text-slate-500">Goals · Notes · Upcoming</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {open && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 p-6 bg-card">
          {/* Goals */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 mb-1">
              <Target className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-semibold text-slate-300">Personal Goals</h3>
            </div>
            <GoalsSection />
          </div>

          {/* Daily Notes */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-slate-300">Daily Notes</h3>
            </div>
            <NotesSection />
          </div>

          {/* Upcoming placeholder */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 mb-1">
              <Calendar className="w-4 h-4 text-green-400" />
              <h3 className="text-sm font-semibold text-slate-300">Upcoming</h3>
            </div>
            <div className="flex-1 bg-navy-800 border border-border/50 rounded-lg p-4 flex items-center justify-center text-slate-600 text-sm italic">
              Future expansion — earnings dates, macro events, reminders
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
