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
  Shield,
  CheckCircle,
  Prohibit,
  Timer,
} from "@phosphor-icons/react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

const approvalTrend = [
  { day: "Mon", approved: 142, blocked: 8 },
  { day: "Tue", approved: 158, blocked: 12 },
  { day: "Wed", approved: 135, blocked: 6 },
  { day: "Thu", approved: 167, blocked: 9 },
  { day: "Fri", approved: 149, blocked: 11 },
  { day: "Sat", approved: 88, blocked: 4 },
  { day: "Sun", approved: 72, blocked: 3 },
]

const policyEffectiveness = [
  { name: "Velocity Limit", triggers: 247 },
  { name: "Amount Threshold", triggers: 189 },
  { name: "Counterparty WL", triggers: 156 },
  { name: "Time Window", triggers: 98 },
  { name: "Chain Restrict", triggers: 64 },
]

const topRules = [
  { rule: "Max Single Transaction", policy: "Velocity Limit", triggers: 89, blockRate: "12.4%", avgAmount: "$8,420", lastTriggered: "2 min ago" },
  { rule: "Daily Aggregate Cap", policy: "Velocity Limit", triggers: 76, blockRate: "8.2%", avgAmount: "$14,300", lastTriggered: "5 min ago" },
  { rule: "New Counterparty Hold", policy: "Counterparty WL", triggers: 64, blockRate: "100%", avgAmount: "$3,200", lastTriggered: "12 min ago" },
  { rule: "High Value Transfer", policy: "Amount Threshold", triggers: 58, blockRate: "22.1%", avgAmount: "$42,500", lastTriggered: "8 min ago" },
  { rule: "Off-Hours Block", policy: "Time Window", triggers: 43, blockRate: "67.4%", avgAmount: "$5,100", lastTriggered: "3 hrs ago" },
  { rule: "Cross-Chain Limit", policy: "Chain Restrict", triggers: 37, blockRate: "18.9%", avgAmount: "$11,800", lastTriggered: "22 min ago" },
  { rule: "Rapid Succession", policy: "Velocity Limit", triggers: 31, blockRate: "45.2%", avgAmount: "$2,100", lastTriggered: "1 hr ago" },
  { rule: "Sanctioned Region", policy: "Counterparty WL", triggers: 12, blockRate: "100%", avgAmount: "$7,600", lastTriggered: "6 hrs ago" },
]

const stats = [
  { label: "Policies Active", value: "14", icon: Shield },
  { label: "Approval Rate", value: "94.2%", icon: CheckCircle },
  { label: "Block Rate", value: "5.8%", icon: Prohibit },
  { label: "Avg Response", value: "23ms", icon: Timer },
]

export default function AnalyticsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">Policy performance and effectiveness metrics</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Approval vs Block Rate</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={approvalTrend}>
                <defs>
                  <linearGradient id="fillApproved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="fillBlocked" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--chart-2))" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(var(--chart-2))" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Area type="monotone" dataKey="approved" stroke="hsl(var(--chart-1))" fill="url(#fillApproved)" strokeWidth={2} />
                <Area type="monotone" dataKey="blocked" stroke="hsl(var(--chart-2))" fill="url(#fillBlocked)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Policy Effectiveness</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={policyEffectiveness} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12 }} className="text-muted-foreground" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={110} className="text-muted-foreground" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="triggers" fill="hsl(var(--chart-1))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Top Triggered Rules</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <div className="overflow-x-auto -mx-4 sm:mx-0">
            <Table className="min-w-[700px]">
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Rule Name</TableHead>
                  <TableHead>Policy</TableHead>
                  <TableHead className="text-right">Trigger Count</TableHead>
                  <TableHead className="text-right">Block Rate</TableHead>
                  <TableHead className="text-right">Avg Amount</TableHead>
                  <TableHead>Last Triggered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {topRules.map((rule) => (
                  <TableRow key={rule.rule}>
                    <TableCell className="pl-4 font-medium">{rule.rule}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{rule.policy}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-mono text-xs">{rule.triggers}</TableCell>
                    <TableCell className="text-right tabular-nums font-mono text-xs">{rule.blockRate}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{rule.avgAmount}</TableCell>
                    <TableCell className="text-muted-foreground">{rule.lastTriggered}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
