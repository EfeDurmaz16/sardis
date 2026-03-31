"use client"

import { useEffect, useMemo, useState } from "react"
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/empty-state"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Lightning,
  Broadcast,
  Warning,
  Timer,
} from "@phosphor-icons/react"
import { dashboardApiFetch } from "@/utils/dashboard-client"

type StreamSeverity = "info" | "warning" | "error" | "success"

type DashboardMetrics = {
  api_calls_24h: number
  agent_events_24h: number
  active_sessions: number
  policy_blocked_24h: number
}

type RawEventEnvelope = {
  type?: string
  timestamp?: string
  data?: Record<string, unknown>
  [key: string]: unknown
}

type LiveEventsResponse = {
  metrics: DashboardMetrics
  recent: {
    events: unknown[]
    count: number
    message?: string
  }
  streamPath: string
}

type EventItem = {
  id: string
  timestamp: string
  type: string
  message: string
  chain: string
  severity: StreamSeverity
}

const severityConfig: Record<EventItem["severity"], { dot: string; label: string }> = {
  info: { dot: "bg-info", label: "Info" },
  warning: { dot: "bg-warning", label: "Warning" },
  error: { dot: "bg-destructive", label: "Error" },
  success: { dot: "bg-success", label: "Success" },
}

const typeVariant: Record<string, "default" | "secondary" | "outline" | "destructive" | "success" | "warning"> = {
  "payment.completed": "success",
  "payment.failed": "destructive",
  "payment.blocked": "warning",
  "policy.triggered": "warning",
  "session.created": "secondary",
  "session.closed": "outline",
  connected: "outline",
}

function inferSeverity(type: string, data: Record<string, unknown>): StreamSeverity {
  if (type.includes("failed") || type.includes("error") || data.status === "error") return "error"
  if (type.includes("blocked") || type.includes("triggered") || data.status === "warning") return "warning"
  if (type.includes("completed") || type.includes("released") || data.status === "success") return "success"
  return "info"
}

function formatTime(value: string | undefined): string {
  if (!value) return "--:--:--"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date)
}

function normalizeChain(data: Record<string, unknown>): string {
  const candidate = typeof data.chain === "string"
    ? data.chain
    : typeof data.network === "string"
      ? data.network
      : typeof data.environment === "string"
        ? data.environment
        : "n/a"

  return candidate
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function formatMessage(type: string, data: Record<string, unknown>): string {
  if (typeof data.message === "string" && data.message.trim()) {
    return data.message
  }

  const summary = Object.entries(data)
    .filter(([key]) => !["message", "org_id", "environment"].includes(key))
    .slice(0, 4)
    .map(([key, value]) => `${key}=${String(value)}`)
    .join(" • ")

  return summary || `Received ${type}`
}

function toEventItem(raw: unknown, fallbackId: string): EventItem {
  const envelope = (raw && typeof raw === "object" ? raw : {}) as RawEventEnvelope
  const type = typeof envelope.type === "string" ? envelope.type : "message"
  const data = envelope.data && typeof envelope.data === "object" ? envelope.data as Record<string, unknown> : {}
  const timestamp = formatTime(envelope.timestamp)

  return {
    id: typeof data.event_id === "string" ? data.event_id : fallbackId,
    timestamp,
    type,
    message: formatMessage(type, data),
    chain: normalizeChain(data),
    severity: inferSeverity(type, data),
  }
}

export default function LiveEventsPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [emptyMessage, setEmptyMessage] = useState<string | null>(null)
  const [streamStatus, setStreamStatus] = useState<"connecting" | "live" | "disconnected">("connecting")
  const [typeFilter, setTypeFilter] = useState("all")
  const [chainFilter, setChainFilter] = useState("all")
  const [severityFilter, setSeverityFilter] = useState("all")
  const [search, setSearch] = useState("")

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const response = await dashboardApiFetch<LiveEventsResponse>("/api/dashboard/live-events?limit=100")
        if (cancelled) return

        setMetrics(response.metrics)
        const initialEvents = (response.recent.events || []).map((event, index) =>
          toEventItem(event, `recent_${index}`),
        )
        setEvents(initialEvents)
        setEmptyMessage(response.recent.message || null)
      } catch (loadError) {
        if (cancelled) return
        const message = loadError instanceof Error ? loadError.message : "Failed to load live events"
        setError(message)
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const source = new EventSource("/api/dashboard/live-events/stream")

    const handleIncomingEvent = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as RawEventEnvelope
        setEvents((current) => [toEventItem(payload, `stream_${Date.now()}`), ...current].slice(0, 200))
      } catch {
        setStreamStatus("disconnected")
      }
    }

    source.onopen = () => {
      setStreamStatus("live")
    }

    source.onmessage = handleIncomingEvent

    ;[
      "payment.completed",
      "payment.blocked",
      "payment.failed",
      "session.created",
      "session.closed",
      "mandate.created",
      "agent.created",
      "faucet.drip",
    ].forEach((eventName) => {
      source.addEventListener(eventName, handleIncomingEvent as EventListener)
    })

    source.onerror = () => {
      setStreamStatus("disconnected")
      source.close()
    }

    return () => {
      source.close()
    }
  }, [])

  const availableTypes = useMemo(
    () => Array.from(new Set(events.map((event) => event.type))).sort(),
    [events],
  )

  const availableChains = useMemo(
    () => Array.from(new Set(events.map((event) => event.chain))).sort(),
    [events],
  )

  const filtered = useMemo(
    () =>
      events.filter((event) => {
        if (typeFilter !== "all" && event.type !== typeFilter) return false
        if (chainFilter !== "all" && event.chain !== chainFilter) return false
        if (severityFilter !== "all" && event.severity !== severityFilter) return false
        if (
          search &&
          !event.message.toLowerCase().includes(search.toLowerCase()) &&
          !event.type.toLowerCase().includes(search.toLowerCase())
        ) {
          return false
        }
        return true
      }),
    [events, typeFilter, chainFilter, severityFilter, search],
  )

  const stats = [
    { label: "Events / 24h", value: metrics ? metrics.agent_events_24h.toString() : "—", icon: Lightning },
    { label: "Stream", value: streamStatus === "live" ? "Live" : streamStatus === "connecting" ? "Connecting" : "Offline", icon: Broadcast },
    { label: "Policy Blocks", value: metrics ? metrics.policy_blocked_24h.toString() : "—", icon: Warning },
    { label: "API Calls / 24h", value: metrics ? metrics.api_calls_24h.toString() : "—", icon: Timer },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Live Events</h1>
        <p className="text-sm text-muted-foreground">Real-time event stream across agents and backend services</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{stat.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Event Feed</CardTitle>
          <CardAction>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span
                  className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${streamStatus === "live" ? "animate-ping bg-success" : "bg-warning"}`}
                />
                <span
                  className={`relative inline-flex h-2 w-2 rounded-full ${streamStatus === "live" ? "bg-success" : streamStatus === "connecting" ? "bg-warning" : "bg-destructive"}`}
                />
              </span>
              <span className="text-xs text-muted-foreground">
                {streamStatus === "live" ? "Live stream connected" : streamStatus === "connecting" ? "Connecting…" : "Stream disconnected"}
              </span>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2 py-3">
            <Select value={typeFilter} onValueChange={(value) => value && setTypeFilter(value)}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Event Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {availableTypes.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={chainFilter} onValueChange={(value) => value && setChainFilter(value)}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Chain" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Chains</SelectItem>
                {availableChains.map((chain) => (
                  <SelectItem key={chain} value={chain}>
                    {chain}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={severityFilter} onValueChange={(value) => value && setSeverityFilter(value)}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="info">Info</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="success">Success</SelectItem>
              </SelectContent>
            </Select>

            <Input
              placeholder="Search events..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-48"
            />
          </div>

          {loading ? (
            <div className="py-16 text-center text-sm text-muted-foreground">Loading event feed…</div>
          ) : error ? (
            <EmptyState
              icon={Broadcast}
              title="Event feed unavailable"
              description={error}
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Broadcast}
              title="No events available"
              description={
                emptyMessage ||
                "The backend did not return any persisted recent events. When the SSE stream emits events they will appear here."
              }
            />
          ) : (
            <ScrollArea className="h-[520px]">
              <div className="space-y-1">
                {filtered.map((event) => {
                  const severity = severityConfig[event.severity]
                  return (
                    <div
                      key={event.id}
                      className="flex items-start gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-muted/50"
                    >
                      <span className="w-[88px] shrink-0 pt-0.5 font-mono text-[11px] text-muted-foreground">
                        {event.timestamp}
                      </span>
                      <Badge variant={typeVariant[event.type] ?? "outline"} className="shrink-0 text-[10px]">
                        {event.type}
                      </Badge>
                      <span className="min-w-0 flex-1 text-sm">{event.message}</span>
                      <Badge variant="outline" className="shrink-0 text-[10px]">
                        {event.chain}
                      </Badge>
                      <span className="flex shrink-0 items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${severity.dot}`} />
                        <span className="text-[11px] text-muted-foreground">{severity.label}</span>
                      </span>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
