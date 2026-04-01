"use client"

import { useMemo } from "react"
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
import {
  Warning,
  ShieldWarning,
  Eye,
  ChartBar,
  Spinner,
} from "@phosphor-icons/react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Anomaly = {
  id: string
  type: "Amount" | "Velocity" | "Pattern" | "Location"
  description: string
  riskScore: number
  agent: string
  amount: string
  detected: string
  status: "Critical" | "Under Review" | "Resolved" | "Dismissed"
  trend?: { day: string; normal: number; anomalous: number }[]
}

const typeVariant: Record<Anomaly["type"], "default" | "secondary" | "outline" | "destructive"> = {
  Amount: "destructive",
  Velocity: "default",
  Pattern: "secondary",
  Location: "outline",
}

function riskColor(score: number) {
  if (score >= 80) return "text-destructive"
  if (score >= 60) return "text-warning"
  return "text-info"
}

const statusVariant: Record<Anomaly["status"], "destructive" | "warning" | "success" | "secondary"> = {
  Critical: "destructive",
  "Under Review": "warning",
  Resolved: "success",
  Dismissed: "secondary",
}

export default function AnomalyDetectionPage() {
  const { data: anomalyData, loading } = useSardis<Anomaly[]>("api/v2/anomaly/recent")
  const anomalies = anomalyData ?? []

  const stats = useMemo(() => {
    const total = anomalies.length
    const critical = anomalies.filter((a) => a.status === "Critical").length
    const underReview = anomalies.filter((a) => a.status === "Under Review").length
    const resolved = anomalies.filter((a) => a.status === "Resolved").length
    const accuracy = total > 0
      ? (((total - anomalies.filter((a) => a.status === "Dismissed").length) / total) * 100).toFixed(1)
      : "0.0"

    return [
      { label: "Anomalies Detected", value: String(total), icon: Warning },
      { label: "Critical", value: String(critical), icon: ShieldWarning, color: "text-destructive" },
      { label: "Under Review", value: String(underReview), icon: Eye },
      { label: "Model Accuracy", value: `${accuracy}%`, icon: ChartBar },
    ]
  }, [anomalies])

  // Build trend data from anomalies if available, otherwise empty
  const trendData = useMemo(() => {
    if (anomalies.length > 0 && anomalies[0]?.trend) {
      return anomalies[0].trend
    }
    return []
  }, [anomalies])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Anomaly Detection</h1>
        <p className="text-sm text-muted-foreground">ML-based anomaly detection and threat monitoring</p>
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

      {trendData.length > 0 && (
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Anomaly Trend (7-Day)</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="normalGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="day" className="text-xs" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis className="text-xs" tick={{ fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend />
                  <Area type="monotone" dataKey="normal" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#normalGrad)" name="Normal Transactions" />
                  <Area type="monotone" dataKey="anomalous" stroke="#ef4444" fillOpacity={1} fill="url(#anomalyGrad)" name="Anomalous" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Recent Anomalies</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : anomalies.length === 0 ? (
            <EmptyState
              icon={Warning}
              title="No anomalies detected"
              description="The ML anomaly detection engine has not flagged any suspicious activity yet"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Alert ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Risk Score</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Detected</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {anomalies.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="pl-4"><Badge variant="outline" className="font-mono">{a.id}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={typeVariant[a.type]}>{a.type}</Badge>
                  </TableCell>
                  <TableCell className="max-w-[240px] truncate">{a.description}</TableCell>
                  <TableCell className="text-right">
                    <span className={`font-semibold font-mono tabular-nums ${riskColor(a.riskScore)}`}>{a.riskScore}</span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{a.agent}</TableCell>
                  <TableCell className="text-right tabular-nums font-mono text-xs">{a.amount}</TableCell>
                  <TableCell className="text-muted-foreground">{a.detected}</TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[a.status]}>{a.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
