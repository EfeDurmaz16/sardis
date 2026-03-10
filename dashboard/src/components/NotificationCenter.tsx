import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Info, AlertTriangle, AlertOctagon, X, CheckCheck, ExternalLink } from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'

const API_URL = import.meta.env.VITE_API_URL || ''
const STORAGE_KEY = 'sardis_read_alerts'
const MAX_ALERTS = 20
const POLL_INTERVAL_MS = 30_000

export interface Alert {
  id: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  timestamp: string
  /** Optional link target — e.g. '/events', '/agents' */
  href?: string
}

// ── helpers ──────────────────────────────────────────────────────────────────

function getReadIds(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? new Set(JSON.parse(raw) as string[]) : new Set()
  } catch {
    return new Set()
  }
}

function persistReadIds(ids: Set<string>) {
  try {
    // Only keep the last 200 IDs to avoid unbounded growth
    const arr = [...ids].slice(-200)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(arr))
  } catch {
    // localStorage unavailable — ignore
  }
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function severityHref(alert: Alert): string {
  if (alert.href) return alert.href
  if (alert.severity === 'critical') return '/anomaly'
  if (alert.severity === 'warning') return '/events'
  return '/events'
}

// ── sub-components ────────────────────────────────────────────────────────────

function SeverityIcon({ severity }: { severity: Alert['severity'] }) {
  if (severity === 'critical')
    return <AlertOctagon className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
  if (severity === 'warning')
    return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
  return <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
}

function AlertRow({
  alert,
  isRead,
  onClick,
}: {
  alert: Alert
  isRead: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-dark-200 transition-colors border-b border-dark-100 last:border-0',
        !isRead && 'bg-dark-200/40'
      )}
    >
      <SeverityIcon severity={alert.severity} />
      <div className="flex-1 min-w-0">
        <p
          className={clsx(
            'text-sm leading-snug break-words',
            isRead ? 'text-gray-400' : 'text-gray-100'
          )}
        >
          {alert.message}
        </p>
        <p className="text-xs text-gray-600 mt-1">{relativeTime(alert.timestamp)}</p>
      </div>
      {!isRead && (
        <span className="w-2 h-2 rounded-full bg-sardis-400 flex-shrink-0 mt-1.5" />
      )}
    </button>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function NotificationCenter() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [readIds, setReadIds] = useState<Set<string>>(getReadIds)

  const wsRef = useRef<WebSocket | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const mountedRef = useRef(true)

  const unreadCount = alerts.filter((a) => !readIds.has(a.id)).length

  // ── fetch REST fallback ───────────────────────────────────────────────────

  const fetchAlerts = useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(`${API_URL}/api/v2/alerts`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return
      const data = await res.json()
      const items: Alert[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.alerts)
        ? data.alerts
        : []
      if (!mountedRef.current) return
      setAlerts((prev) => {
        const existing = new Set(prev.map((a) => a.id))
        const fresh = items.filter((a) => !existing.has(a.id))
        return [...fresh, ...prev].slice(0, MAX_ALERTS)
      })
    } catch {
      // Network unavailable — silently ignore
    }
  }, [token])

  // ── start polling ─────────────────────────────────────────────────────────

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return
    fetchAlerts()
    pollTimerRef.current = setInterval(fetchAlerts, POLL_INTERVAL_MS)
  }, [fetchAlerts])

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  // ── WebSocket connection ──────────────────────────────────────────────────

  const connectWs = useCallback(() => {
    if (!token || !mountedRef.current) return

    // Derive ws URL from API_URL
    const wsBase = API_URL
      ? API_URL.replace(/^http/, 'ws')
      : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

    const url = `${wsBase}/api/v2/ws/alerts?token=org_default`

    let ws: WebSocket
    try {
      ws = new WebSocket(url)
    } catch {
      // WebSocket construction failed (e.g. bad URL) — use polling
      startPolling()
      return
    }

    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      // WebSocket connected — stop polling if it was running
      stopPolling()
    }

    ws.onmessage = (evt) => {
      if (!mountedRef.current) return
      try {
        const alert: Alert = JSON.parse(evt.data as string)
        if (!alert.id || !alert.message) return
        setAlerts((prev) => {
          const exists = prev.some((a) => a.id === alert.id)
          if (exists) return prev
          return [alert, ...prev].slice(0, MAX_ALERTS)
        })
      } catch {
        // Malformed message — ignore
      }
    }

    ws.onerror = () => {
      // On error the close event will fire next — handled there
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      wsRef.current = null
      // Fall back to polling and schedule reconnect after 10 s
      startPolling()
      reconnectTimerRef.current = setTimeout(() => {
        if (!mountedRef.current) return
        stopPolling()
        connectWs()
      }, 10_000)
    }
  }, [token, startPolling, stopPolling])

  // ── lifecycle ─────────────────────────────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true
    // Initial REST fetch for history
    fetchAlerts()
    // Attempt WebSocket
    connectWs()

    return () => {
      mountedRef.current = false
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
      stopPolling()
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }
  }, [token]) // re-run if token changes (login/logout)

  // ── close on outside click ────────────────────────────────────────────────

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  // ── actions ───────────────────────────────────────────────────────────────

  function handleAlertClick(alert: Alert) {
    const next = new Set(readIds)
    next.add(alert.id)
    setReadIds(next)
    persistReadIds(next)
    setOpen(false)
    navigate(severityHref(alert))
  }

  function markAllRead() {
    const next = new Set(readIds)
    alerts.forEach((a) => next.add(a.id))
    setReadIds(next)
    persistReadIds(next)
  }

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 text-gray-400 hover:text-white transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[1rem] h-4 px-0.5 rounded-full bg-red-500 text-white text-[10px] font-bold leading-none">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-dark-300 border border-dark-100 shadow-xl z-50 flex flex-col max-h-[480px]">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-dark-100 flex-shrink-0">
            <span className="text-sm font-semibold text-gray-100">Notifications</span>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="text-gray-500 hover:text-gray-300 transition-colors"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Alert list */}
          <div className="overflow-y-auto flex-1">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                <Bell className="w-8 h-8 mb-3 opacity-40" />
                <p className="text-sm">No notifications yet</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  isRead={readIds.has(alert.id)}
                  onClick={() => handleAlertClick(alert)}
                />
              ))
            )}
          </div>

          {/* Footer */}
          {alerts.length > 0 && (
            <div className="border-t border-dark-100 flex-shrink-0">
              <button
                onClick={() => {
                  setOpen(false)
                  navigate('/events')
                }}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-3 text-xs text-sardis-400 hover:text-sardis-300 hover:bg-dark-200 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View all events
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
