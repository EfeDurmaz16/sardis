"use client"

import { useState } from "react"
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
} from "@phosphor-icons/react"
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

type LogEntry = {
  id: string
  timestamp: string
  level: "INFO" | "WARN" | "ERROR"
  service: string
  message: string
}

type Trace = {
  id: string
  traceId: string
  service: string
  operation: string
  duration: string
  status: "ok" | "error"
  spans: number
  timestamp: string
}

const logs: LogEntry[] = [
  { id: "l01", timestamp: "14:32:07.412", level: "INFO", service: "payment-router", message: "Transaction 0x8f2a processed successfully in 42ms" },
  { id: "l02", timestamp: "14:32:06.891", level: "INFO", service: "agent-orchestrator", message: "Delegation chain resolved: Treasury Sweep -> Payment Router" },
  { id: "l03", timestamp: "14:32:05.234", level: "WARN", service: "hold-service", message: "Hold timeout approaching for hold_4d7e — 2 minutes remaining" },
  { id: "l04", timestamp: "14:32:04.102", level: "ERROR", service: "bridge-relay", message: "Cross-chain message delivery failed — retrying in 5s (attempt 2/3)" },
  { id: "l05", timestamp: "14:32:03.556", level: "INFO", service: "policy-engine", message: "Velocity check passed for agent 0x3c8D — 12/50 daily txns used" },
  { id: "l06", timestamp: "14:32:02.001", level: "INFO", service: "wallet-manager", message: "Gas balance refreshed for 24 active wallets" },
  { id: "l07", timestamp: "14:32:00.887", level: "WARN", service: "reconciliation", message: "Pending reconciliation items exceeded threshold: 47 items" },
  { id: "l08", timestamp: "14:31:59.334", level: "ERROR", service: "payment-router", message: "Gas estimation failed for Optimism — node returned invalid response" },
  { id: "l09", timestamp: "14:31:58.221", level: "INFO", service: "mandate-service", message: "Mandate refresh completed for 8 agents — all within limits" },
  { id: "l10", timestamp: "14:31:57.009", level: "INFO", service: "policy-engine", message: "Counterparty whitelist cache refreshed — 342 entries" },
  { id: "l11", timestamp: "14:31:55.776", level: "WARN", service: "agent-orchestrator", message: "Agent response latency elevated: avg 280ms (threshold 200ms)" },
  { id: "l12", timestamp: "14:31:54.443", level: "INFO", service: "invoice-service", message: "Invoice batch #2847 settled — 3 invoices totaling $12,500" },
]

const traces: Trace[] = [
  { id: "t01", traceId: "abc-1234-def", service: "payment-router", operation: "processPayment", duration: "142ms", status: "ok", spans: 8, timestamp: "14:32:07" },
  { id: "t02", traceId: "ghi-5678-jkl", service: "agent-orchestrator", operation: "delegateTask", duration: "89ms", status: "ok", spans: 5, timestamp: "14:32:06" },
  { id: "t03", traceId: "mno-9012-pqr", service: "bridge-relay", operation: "crossChainTransfer", duration: "2,341ms", status: "error", spans: 12, timestamp: "14:32:04" },
  { id: "t04", traceId: "stu-3456-vwx", service: "policy-engine", operation: "evaluatePolicy", duration: "23ms", status: "ok", spans: 3, timestamp: "14:32:03" },
  { id: "t05", traceId: "yza-7890-bcd", service: "hold-service", operation: "createHold", duration: "67ms", status: "ok", spans: 4, timestamp: "14:32:01" },
  { id: "t06", traceId: "efg-2345-hij", service: "wallet-manager", operation: "refreshBalances", duration: "312ms", status: "ok", spans: 26, timestamp: "14:31:59" },
  { id: "t07", traceId: "klm-6789-nop", service: "payment-router", operation: "processPayment", duration: "5,102ms", status: "error", spans: 9, timestamp: "14:31:58" },
  { id: "t08", traceId: "qrs-0123-tuv", service: "mandate-service", operation: "checkMandate", duration: "18ms", status: "ok", spans: 2, timestamp: "14:31:57" },
]

const makeSparkline = (base: number, variance: number) =>
  Array.from({ length: 12 }, (_, i) => ({
    t: i,
    v: base + Math.round((Math.sin(i * 0.8) + Math.random() * 0.5) * variance),
  }))

const metrics = [
  { title: "Request Rate", value: "1,247 req/s", data: makeSparkline(1200, 100), color: "hsl(var(--chart-1))" },
  { title: "P99 Latency", value: "187ms", data: makeSparkline(180, 30), color: "hsl(var(--chart-2))" },
  { title: "Error Count", value: "3", data: makeSparkline(2, 2), color: "hsl(var(--chart-3))" },
  { title: "CPU Usage", value: "34%", data: makeSparkline(32, 8), color: "hsl(var(--chart-4))" },
  { title: "Memory", value: "2.1 GB", data: makeSparkline(2100, 200), color: "hsl(var(--chart-1))" },
  { title: "Active Connections", value: "847", data: makeSparkline(840, 50), color: "hsl(var(--chart-2))" },
]

const stats = [
  { label: "Uptime", value: "99.97%", icon: Heartbeat },
  { label: "Avg Latency", value: "42ms", icon: Timer },
  { label: "Error Rate", value: "0.12%", icon: Warning },
  { label: "Active Traces", value: "847", icon: Eye },
]

const levelConfig: Record<LogEntry["level"], string> = {
  INFO: "bg-info-muted text-info",
  WARN: "bg-warning-muted text-warning",
  ERROR: "bg-destructive/15 text-destructive",
}

export default function ObservabilityPage() {
  const [tab, setTab] = useState("logs")

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
          {tab === "logs" && (
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
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium shrink-0 ${levelConfig[log.level]}`}>
                      {log.level}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground shrink-0 w-[140px] truncate">{log.service}</span>
                    <span className="text-sm flex-1 min-w-0 truncate">{log.message}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}

          {tab === "traces" && (
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
                      <TableCell className="font-mono text-xs">{trace.traceId}</TableCell>
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
          )}

          {tab === "metrics" && (
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
          )}
        </CardContent>
      </Card>
    </div>
  )
}
