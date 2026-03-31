"use client"

import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import {
  Heartbeat, CheckCircle, Warning, ChartBar, Spinner, ArrowClockwise,
} from "@phosphor-icons/react"
import { useSardis } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type HealthReport = {
  providers: Record<string, {
    status: string
    latency_ms: number | null
    last_error: string | null
    checked_at: string
  }>
}

type ProviderEntry = {
  name: string
  status: "Healthy" | "Degraded" | "Down" | "Unknown"
  latency: string
  checkedAt: string
  lastError: string | null
}

const statusConfig: Record<string, { dot: string; label: string }> = {
  Healthy: { dot: "bg-success", label: "Healthy" },
  Degraded: { dot: "bg-warning", label: "Degraded" },
  Down: { dot: "bg-destructive", label: "Down" },
  Unknown: { dot: "bg-muted-foreground", label: "Unknown" },
}

function normalizeStatus(raw: string): ProviderEntry["status"] {
  const lower = raw.toLowerCase()
  if (lower === "healthy" || lower === "ok" || lower === "up") return "Healthy"
  if (lower === "degraded" || lower === "slow") return "Degraded"
  if (lower === "down" || lower === "error") return "Down"
  return "Unknown"
}

export default function ProviderHealthPage() {
  const { data, loading, error, refetch } = useSardis<HealthReport>("api/v2/health/providers")

  const providers: ProviderEntry[] = data
    ? Object.entries(data.providers).map(([name, info]) => ({
        name,
        status: normalizeStatus(info.status),
        latency: info.latency_ms !== null ? `${info.latency_ms}ms` : "—",
        checkedAt: info.checked_at,
        lastError: info.last_error,
      }))
    : []

  const healthyCount = providers.filter(p => p.status === "Healthy").length
  const degradedCount = providers.filter(p => p.status === "Degraded").length
  const downCount = providers.filter(p => p.status === "Down").length

  const stats = [
    { label: "Providers", value: String(providers.length), icon: Heartbeat },
    { label: "Healthy", value: String(healthyCount), icon: CheckCircle },
    { label: "Degraded", value: String(degradedCount), icon: Warning, color: degradedCount > 0 ? "text-warning" : undefined },
    { label: "Down", value: String(downCount), icon: Warning, color: downCount > 0 ? "text-destructive" : undefined },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Provider Health</h1>
          <p className="text-sm text-muted-foreground">Payment provider status and performance monitoring</p>
        </div>
        <Button variant="outline" size="sm" onClick={refetch} disabled={loading}>
          <ArrowClockwise className={`w-4 h-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : error || providers.length === 0 ? (
        <EmptyState
          icon={Heartbeat}
          title="Provider health unavailable"
          description="Health monitoring data will appear here once the API is configured and providers are registered."
          action={refetch}
          actionLabel="Retry"
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((s) => {
              const Ico = s.icon
              return (
                <Card key={s.label} size="sm">
                  <CardContent className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                      <Ico className={`h-4 w-4 ${s.color || "text-muted-foreground"}`} />
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">{s.label}</p>
                      <p className={`text-lg font-semibold tracking-tight tabular-nums ${s.color || ""}`}>{s.value}</p>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {providers.map((p) => {
              const st = statusConfig[p.status]
              return (
                <Card key={p.name}>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>{p.name}</span>
                      <span className="inline-flex items-center gap-1.5 text-sm font-normal">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`} />
                        <span className={p.status === "Healthy" ? "text-muted-foreground" : p.status === "Down" ? "text-destructive" : "text-warning"}>{st.label}</span>
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Latency</p>
                        <p className="text-sm font-semibold tabular-nums">{p.latency}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Last Check</p>
                        <p className="text-sm font-semibold">{p.checkedAt}</p>
                      </div>
                    </div>
                    {p.lastError && (
                      <div>
                        <p className="text-xs text-muted-foreground">Last Error</p>
                        <p className="text-xs text-destructive truncate">{p.lastError}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
