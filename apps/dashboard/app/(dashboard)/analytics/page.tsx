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
  Spinner,
  ChartBar,
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
import { useSardis } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type ApprovalTrendEntry = {
  day: string
  approved: number
  blocked: number
}

type PolicyEffectivenessEntry = {
  name: string
  triggers: number
}

type TopRule = {
  rule: string
  policy: string
  triggers: number
  block_rate: string
  avg_amount: string
  last_triggered: string
}

type AnalyticsData = {
  approval_trend: ApprovalTrendEntry[]
  policy_effectiveness: PolicyEffectivenessEntry[]
  top_rules: TopRule[]
  policies_active: number
  approval_rate: number
  block_rate: number
  avg_response_ms: number
}

export default function AnalyticsPage() {
  const { data, loading, error, refetch } = useSardis<AnalyticsData>("api/v2/analytics/summary")

  const approvalTrend = data?.approval_trend ?? []
  const policyEffectiveness = data?.policy_effectiveness ?? []
  const topRules = data?.top_rules ?? []

  const stats = [
    { label: "Policies Active", value: data ? String(data.policies_active) : "—", icon: Shield },
    { label: "Approval Rate", value: data ? `${data.approval_rate}%` : "—", icon: CheckCircle },
    { label: "Block Rate", value: data ? `${data.block_rate}%` : "—", icon: Prohibit },
    { label: "Avg Response", value: data ? `${data.avg_response_ms}ms` : "—", icon: Timer },
  ]

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">Policy performance and effectiveness metrics</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">Policy performance and effectiveness metrics</p>
        </div>
        <EmptyState
          icon={ChartBar}
          title="Analytics unavailable"
          description={error || "Analytics data will appear here once transactions start flowing through the system."}
          action={refetch}
          actionLabel="Retry"
        />
      </div>
    )
  }

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
            {approvalTrend.length === 0 ? (
              <EmptyState
                icon={ChartBar}
                title="No trend data"
                description="Approval trend will populate once policies evaluate transactions."
              />
            ) : (
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
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Policy Effectiveness</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            {policyEffectiveness.length === 0 ? (
              <EmptyState
                icon={Shield}
                title="No policy data"
                description="Policy effectiveness metrics will appear once rules are triggered."
              />
            ) : (
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
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Top Triggered Rules</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {topRules.length === 0 ? (
            <EmptyState
              icon={Shield}
              title="No triggered rules"
              description="Rule trigger history will appear here as policies evaluate transactions."
            />
          ) : (
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
                      <TableCell className="text-right tabular-nums font-mono text-xs">{rule.block_rate}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{rule.avg_amount}</TableCell>
                      <TableCell className="text-muted-foreground">{rule.last_triggered}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
