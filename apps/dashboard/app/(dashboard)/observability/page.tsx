"use client"

import { useState, useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Heartbeat,
  Timer,
  Warning,
  Eye,
  Spinner,
} from "@phosphor-icons/react"
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type LogEntry = {
  id: string
  timestamp: string
  level: "INFO" | "WARN" | "ERROR"
  service: string
  message: string
}

type Trace = {
  id: string
  trace_id: string
  service: string
  operation: string
  duration: string
  status: "ok" | "error"
  spans: number
  timestamp: string
}

type MetricSeries = {
  title: string
  value: string
  data: { t: number; v: number }[]
  color: string
}

type ObservabilityData = {
  uptime: string
  avg_latency: string
  error_rate: string
  active_traces: number
  logs: LogEntry[]
  traces: Trace[]
  metrics: MetricSeries[]
}

const levelConfig: Record<string, string> = {
  INFO: "bg-info-muted text-info",
  WARN: "bg-warning-muted text-warning",
  ERROR: "bg-destructive/15 text-destructive",
}

const defaultChartColors = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
]

export default function ObservabilityPage() {
  const { data, loading } = useSardis<ObservabilityData>("api/v2/metrics/summary")
  const [tab, setTab] = useState("logs")

  const logs = data?.logs ?? []
  const traces = data?.traces ?? []
  const metrics = useMemo(() => {
    if (!data?.metrics) return []
    return data.metrics.map((m, i) => ({
      ...m,
      color: m.color || defaultChartColors[i % defaultChartColors.length],
    }))
  }, [data?.metrics])

  const stats = useMemo(() => {
    if (!data) {
      return [
        { label: "Uptime", value: "—", icon: Heartbeat },
        { label: "Avg Latency", value: "—", icon: Timer },
        { label: "Error Rate", value: "—", icon: Warning },
        { label: "Active Traces", value: "—", icon: Eye },
      ]
    }

    return [
      { label: "Uptime", value: data.uptime ?? "—", icon: Heartbeat },
      { label: "Avg Latency", value: data.avg_latency ?? "—", icon: Timer },
      { label: "Error Rate", value: data.error_rate ?? "—", icon: Warning },
      { label: "Active Traces", value: String(data.active_traces ?? 0), icon: Eye },
    ]
  }, [data])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Observability</h1>
        <p className="text-sm text-muted-foreground">System health, logs, traces, and performance metrics</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => {
          const Ico = s.icon
          return (
            <Card key={s.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Ico className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{s.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader className="border-b">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="logs">Logs</TabsTrigger>
              <TabsTrigger value="traces">Traces</TabsTrigger>
              <TabsTrigger value="metrics">Metrics</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {tab === "logs" && (
                logs.length === 0 ? (
                  <EmptyState
                    icon={Eye}
                    title="No logs"
                    description="System logs will appear here once services start producing output"
                  />
                ) : (
                  <ScrollArea className="h-[480px]">
                    <div className="space-y-1 pt-3">
                      {logs.map((log) => (
                        <div
                          key={log.id}
                          className="flex items-start gap-3 rounded-md px-3 py-2 hover:bg-muted/50 transition-colors"
                        >
                          <span className="font-mono text-[11px] text-muted-foreground pt-0.5 shrink-0 w-[88px]">
                            {log.timestamp}
                          </span>
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium shrink-0 ${levelConfig[log.level] ?? ""}`}>
                            {log.level}
                          </span>
                          <span className="text-xs font-mono text-muted-foreground shrink-0 w-[140px] truncate">{log.service}</span>
                          <span className="text-sm flex-1 min-w-0 truncate">{log.message}</span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )
              )}

              {tab === "traces" && (
                traces.length === 0 ? (
                  <EmptyState
                    icon={Eye}
                    title="No traces"
                    description="Distributed traces will appear here once requests flow through the system"
                  />
                ) : (
                  <div className="pt-3">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Trace ID</TableHead>
                          <TableHead>Service</TableHead>
                          <TableHead>Operation</TableHead>
                          <TableHead className="text-right">Duration</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Spans</TableHead>
                          <TableHead>Time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {traces.map((trace) => (
                          <TableRow key={trace.id}>
                            <TableCell className="font-mono text-xs">{trace.trace_id}</TableCell>
                            <TableCell className="text-xs">{trace.service}</TableCell>
                            <TableCell className="font-mono text-xs">{trace.operation}</TableCell>
                            <TableCell className="text-right tabular-nums font-mono text-xs">{trace.duration}</TableCell>
                            <TableCell>
                              <span className={`inline-flex items-center gap-1.5`}>
                                <span className={`h-1.5 w-1.5 rounded-full ${trace.status === "ok" ? "bg-success" : "bg-destructive"}`} />
                                <span className="text-xs">{trace.status === "ok" ? "OK" : "Error"}</span>
                              </span>
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              <Badge variant="outline">{trace.spans}</Badge>
                            </TableCell>
                            <TableCell className="font-mono text-xs text-muted-foreground">{trace.timestamp}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )
              )}

              {tab === "metrics" && (
                metrics.length === 0 ? (
                  <EmptyState
                    icon={Heartbeat}
                    title="No metrics"
                    description="Performance metrics will appear here once the system starts collecting data"
                  />
                ) : (
                  <div className="grid grid-cols-1 gap-4 pt-4 md:grid-cols-2">
                    {metrics.map((metric) => (
                      <div key={metric.title} className="rounded-lg border p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-muted-foreground">{metric.title}</span>
                          <span className="text-sm font-semibold tabular-nums">{metric.value}</span>
                        </div>
                        <ResponsiveContainer width="100%" height={64}>
                          <LineChart data={metric.data}>
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "hsl(var(--popover))",
                                border: "1px solid hsl(var(--border))",
                                borderRadius: "8px",
                                fontSize: "11px",
                              }}
                              labelFormatter={() => ""}
                              formatter={(value) => [String(value), metric.title]}
                            />
                            <Line
                              type="monotone"
                              dataKey="v"
                              stroke={metric.color}
                              strokeWidth={1.5}
                              dot={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    ))}
                  </div>
                )
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
