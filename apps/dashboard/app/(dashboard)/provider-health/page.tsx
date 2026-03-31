"use client"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import {
  Heartbeat,
  CheckCircle,
  Warning,
  ChartBar,
} from "@phosphor-icons/react"

type Provider = {
  name: string
  status: "Healthy" | "Degraded" | "Down"
  uptime: number
  avgLatency: string
  transactionsPerHour: string
  lastIncident: string
}

const providers: Provider[] = [
  { name: "Stripe", status: "Healthy", uptime: 99.99, avgLatency: "42ms", transactionsPerHour: "1,284", lastIncident: "32 days ago" },
  { name: "Circle", status: "Healthy", uptime: 99.97, avgLatency: "68ms", transactionsPerHour: "892", lastIncident: "14 days ago" },
  { name: "Fireblocks", status: "Healthy", uptime: 99.98, avgLatency: "55ms", transactionsPerHour: "647", lastIncident: "21 days ago" },
  { name: "Alchemy", status: "Degraded", uptime: 99.72, avgLatency: "124ms", transactionsPerHour: "2,103", lastIncident: "2 hrs ago" },
  { name: "Infura", status: "Healthy", uptime: 99.95, avgLatency: "78ms", transactionsPerHour: "1,847", lastIncident: "7 days ago" },
  { name: "QuickNode", status: "Healthy", uptime: 99.96, avgLatency: "61ms", transactionsPerHour: "1,523", lastIncident: "18 days ago" },
  { name: "Chainlink", status: "Healthy", uptime: 99.99, avgLatency: "35ms", transactionsPerHour: "3,214", lastIncident: "45 days ago" },
  { name: "TheGraph", status: "Healthy", uptime: 99.94, avgLatency: "92ms", transactionsPerHour: "756", lastIncident: "9 days ago" },
]

const stats = [
  { label: "Providers", value: "8", icon: Heartbeat },
  { label: "Healthy", value: "7", icon: CheckCircle },
  { label: "Degraded", value: "1", icon: Warning, color: "text-warning" },
  { label: "Avg Uptime", value: "99.94%", icon: ChartBar },
]

const statusConfig: Record<Provider["status"], { dot: string; label: string }> = {
  Healthy: { dot: "bg-success", label: "Healthy" },
  Degraded: { dot: "bg-warning", label: "Degraded" },
  Down: { dot: "bg-destructive", label: "Down" },
}

export default function ProviderHealthPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Provider Health</h1>
        <p className="text-sm text-muted-foreground">Payment provider status and performance monitoring</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => {
          const Ico = s.icon
          return (
            <Card key={s.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Ico className={`h-4 w-4 ${"color" in s && s.color ? s.color : "text-muted-foreground"}`} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className={`text-lg font-semibold tracking-tight tabular-nums ${"color" in s && s.color ? s.color : ""}`}>{s.value}</p>
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
                    <span className={p.status === "Healthy" ? "text-muted-foreground" : "text-warning"}>{st.label}</span>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Uptime</p>
                    <p className="text-sm font-semibold tabular-nums">{p.uptime}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Avg Latency</p>
                    <p className="text-sm font-semibold tabular-nums">{p.avgLatency}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Transactions/hr</p>
                    <p className="text-sm font-semibold tabular-nums">{p.transactionsPerHour}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Last Incident</p>
                    <p className="text-sm font-semibold">{p.lastIncident}</p>
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">Uptime</span>
                    <span className="text-xs font-mono tabular-nums text-muted-foreground">{p.uptime}%</span>
                  </div>
                  <Progress value={p.uptime} className="h-1.5" />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
