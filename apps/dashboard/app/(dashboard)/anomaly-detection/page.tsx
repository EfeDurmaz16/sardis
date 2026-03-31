"use client"

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

const trendData = [
  { day: "Mon", normal: 482, anomalous: 1 },
  { day: "Tue", normal: 510, anomalous: 3 },
  { day: "Wed", normal: 498, anomalous: 0 },
  { day: "Thu", normal: 523, anomalous: 2 },
  { day: "Fri", normal: 541, anomalous: 4 },
  { day: "Sat", normal: 389, anomalous: 1 },
  { day: "Sun", normal: 412, anomalous: 1 },
]

type Anomaly = {
  id: string
  type: "Amount" | "Velocity" | "Pattern" | "Location"
  description: string
  riskScore: number
  agent: string
  amount: string
  detected: string
  status: "Critical" | "Under Review" | "Resolved" | "Dismissed"
}

const anomalies: Anomaly[] = [
  { id: "AN-0412", type: "Amount", description: "Transaction 8.2x above agent daily average", riskScore: 94, agent: "Payment Router Alpha", amount: "$84,200", detected: "3 min ago", status: "Critical" },
  { id: "AN-0411", type: "Velocity", description: "47 transactions in 2-minute window", riskScore: 88, agent: "Gas Optimizer v3", amount: "$12,400", detected: "12 min ago", status: "Critical" },
  { id: "AN-0410", type: "Pattern", description: "Unusual round-number transfer sequence detected", riskScore: 72, agent: "Treasury Sweep Bot", amount: "$50,000", detected: "28 min ago", status: "Under Review" },
  { id: "AN-0409", type: "Location", description: "Transaction origin from new geographic region", riskScore: 65, agent: "Cross-chain Bridge", amount: "$31,600", detected: "45 min ago", status: "Under Review" },
  { id: "AN-0408", type: "Amount", description: "Single transfer exceeds 60% of wallet balance", riskScore: 78, agent: "Vendor Pay Agent", amount: "$7,800", detected: "1 hr ago", status: "Under Review" },
  { id: "AN-0407", type: "Velocity", description: "Spike in API calls from agent endpoint", riskScore: 55, agent: "Expense Tracker v2", amount: "$2,100", detected: "2 hrs ago", status: "Resolved" },
  { id: "AN-0406", type: "Pattern", description: "Repeated failed transactions followed by success", riskScore: 61, agent: "Invoice Settler", amount: "$15,300", detected: "3 hrs ago", status: "Under Review" },
  { id: "AN-0405", type: "Location", description: "Cross-chain hop through unvetted bridge", riskScore: 48, agent: "Yield Harvester", amount: "$5,600", detected: "5 hrs ago", status: "Under Review" },
]

const stats = [
  { label: "Anomalies Detected", value: "12", icon: Warning },
  { label: "Critical", value: "2", icon: ShieldWarning, color: "text-destructive" },
  { label: "Under Review", value: "5", icon: Eye },
  { label: "Model Accuracy", value: "96.8%", icon: ChartBar },
]

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

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Recent Anomalies</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
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
        </CardContent>
      </Card>
    </div>
  )
}
