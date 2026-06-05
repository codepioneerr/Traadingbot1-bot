import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function getPassword() {
  return localStorage.getItem('dashboard_password') || ''
}

export function clearPassword() {
  localStorage.removeItem('dashboard_password')
}

export async function apiFetch(path, options = {}) {
  const pw = getPassword()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(pw ? { 'X-Password': pw } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    clearPassword()
    window.dispatchEvent(new Event('auth-required'))
    return null
  }
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText)
    throw new Error(err || `HTTP ${res.status}`)
  }
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

// Hook: fetches once on mount, then re-fetches every `interval` ms
export function useApi(path, interval = 30000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const pathRef = useRef(path)
  pathRef.current = path

  const fetch_ = useCallback(async () => {
    try {
      const d = await apiFetch(pathRef.current)
      if (d !== null) { setData(d); setError(null) }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch_()
    if (!interval) return
    const id = setInterval(fetch_, interval)
    return () => clearInterval(id)
  }, [fetch_, interval])

  return { data, loading, error, refetch: fetch_ }
}
