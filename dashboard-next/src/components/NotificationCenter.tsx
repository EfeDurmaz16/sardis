"use client";
import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Bell, Info, AlertTriangle, AlertOctagon, X, CheckCheck, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''
const STORAGE_KEY = 'sardis_read_alerts'
const MAX_ALERTS = 20
const POLL_INTERVAL_MS = 30_000

export interface Alert { id: string; severity: 'info' | 'warning' | 'critical'; message: string; timestamp: string; href?: string }

function getReadIds(): Set<string> { try { const raw = localStorage.getItem(STORAGE_KEY); return raw ? new Set(JSON.parse(raw) as string[]) : new Set() } catch { return new Set() } }
function saveReadIds(ids: Set<string>) { localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids])) }
function severityIcon(s: Alert['severity']) { if (s === 'critical') return <AlertOctagon className="w-4 h-4 text-red-400 flex-shrink-0" />; if (s === 'warning') return <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />; return <Info className="w-4 h-4 text-blue-400 flex-shrink-0" /> }

export default function NotificationCenter() {
  const router = useRouter()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const [open, setOpen] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)
  const fetchAlerts = useCallback(async () => { try { const res = await fetch(`${API_URL}/api/v2/alerts?limit=${MAX_ALERTS}`, { credentials: 'include' }); if (!res.ok) return; const data = await res.json(); setAlerts(Array.isArray(data) ? data : data.alerts ?? []) } catch {} }, [])
  useEffect(() => { setReadIds(getReadIds()); fetchAlerts(); const id = setInterval(fetchAlerts, POLL_INTERVAL_MS); return () => clearInterval(id) }, [fetchAlerts])
  useEffect(() => { function h(e: MouseEvent) { if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false) } document.addEventListener('mousedown', h); return () => document.removeEventListener('mousedown', h) }, [])
  const unreadCount = alerts.filter((a) => !readIds.has(a.id)).length
  function markAllRead() { const n = new Set(readIds); alerts.forEach((a) => n.add(a.id)); setReadIds(n); saveReadIds(n) }
  function handleAlertClick(alert: Alert) { const n = new Set(readIds); n.add(alert.id); setReadIds(n); saveReadIds(n); if (alert.href) { setOpen(false); router.push(alert.href) } }

  return (
    <div className="relative" ref={panelRef}>
      <button onClick={() => setOpen(!open)} className="relative p-2 text-gray-400 hover:text-white transition-colors">
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">{unreadCount > 9 ? '9+' : unreadCount}</span>}
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-dark-300 border border-dark-100 shadow-lg z-50 max-h-96 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between p-3 border-b border-dark-100">
            <h3 className="text-sm font-semibold text-white">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && <button onClick={markAllRead} className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"><CheckCheck className="w-3 h-3" /> Mark all read</button>}
              <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-300"><X className="w-4 h-4" /></button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {alerts.length === 0 ? <p className="p-4 text-sm text-gray-500 text-center">No notifications</p> : alerts.map((alert) => {
              const isRead = readIds.has(alert.id)
              return (
                <button key={alert.id} onClick={() => handleAlertClick(alert)} className={clsx('w-full text-left p-3 flex gap-3 border-b border-dark-100/40 transition-colors hover:bg-dark-200/50', !isRead && 'bg-dark-200/20')}>
                  {severityIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <p className={clsx('text-sm', isRead ? 'text-gray-400' : 'text-gray-200')}>{alert.message}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{new Date(alert.timestamp).toLocaleTimeString()}</p>
                  </div>
                  {alert.href && <ExternalLink className="w-3 h-3 text-gray-600 mt-1 flex-shrink-0" />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
