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
import { Switch } from "@/components/ui/switch"
import {
  UserCheck,
  Clock,
  CheckCircle,
  ChartBar,
  Spinner,
} from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type ApprovalRule = {
  name: string
  condition: string
  approvers: number
  timeout: string
  autoApprove: boolean
  status: "Active" | "Disabled"
}

type ApprovalConfig = {
  rules: ApprovalRule[]
  pendingApprovals?: number
  avgApprovalTime?: string
}

const statusConfig: Record<ApprovalRule["status"], { color: string }> = {
  Active: { color: "bg-success" },
  Disabled: { color: "bg-destructive" },
}

export default function ApprovalConfigPage() {
  const { data: config, loading } = useSardis<ApprovalConfig>("api/v2/approval-config")
  const rules = config?.rules ?? []

  const stats = useMemo(() => {
    const totalRules = rules.length
    const pending = config?.pendingApprovals ?? 0
    const avgTime = config?.avgApprovalTime ?? "N/A"
    const autoApproveCount = rules.filter((r) => r.autoApprove).length
    const autoApproveRate = totalRules > 0
      ? Math.round((autoApproveCount / totalRules) * 100)
      : 0

    return [
      { label: "Approval Rules", value: String(totalRules), icon: UserCheck },
      { label: "Pending Approvals", value: String(pending), icon: Clock },
      { label: "Avg Approval Time", value: avgTime, icon: CheckCircle },
      { label: "Auto-Approved", value: `${autoApproveRate}%`, icon: ChartBar },
    ]
  }, [rules, config])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Approval Config</h1>
        <p className="text-sm text-muted-foreground">Configure approval workflows and automation rules</p>
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
          <CardTitle>Approval Rules</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : rules.length === 0 ? (
            <EmptyState
              icon={UserCheck}
              title="No approval rules"
              description="Configure approval workflows to require sign-offs on high-value or sensitive transactions"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Rule Name</TableHead>
                <TableHead>Condition</TableHead>
                <TableHead className="text-right">Required Approvers</TableHead>
                <TableHead>Timeout</TableHead>
                <TableHead>Auto-Approve</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((rule) => {
                const st = statusConfig[rule.status]
                return (
                  <TableRow key={rule.name}>
                    <TableCell className="pl-4 font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {rule.condition}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{rule.approvers}</TableCell>
                    <TableCell className="text-muted-foreground">{rule.timeout}</TableCell>
                    <TableCell>
                      <Switch defaultChecked={rule.autoApprove} />
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                        {rule.status}
                      </span>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
