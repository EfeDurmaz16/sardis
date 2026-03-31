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
import { Switch } from "@/components/ui/switch"
import {
  UserCheck,
  Clock,
  CheckCircle,
  ChartBar,
} from "@phosphor-icons/react"

type ApprovalRule = {
  name: string
  condition: string
  approvers: number
  timeout: string
  autoApprove: boolean
  status: "Active" | "Disabled"
}

const approvalRules: ApprovalRule[] = [
  { name: "High Value Transaction", condition: "Amount > $5,000", approvers: 2, timeout: "30m", autoApprove: false, status: "Active" },
  { name: "New Merchant First Pay", condition: "First transaction to merchant", approvers: 1, timeout: "15m", autoApprove: false, status: "Active" },
  { name: "Cross-chain Transfer", condition: "Source chain ≠ Target chain", approvers: 2, timeout: "1h", autoApprove: false, status: "Active" },
  { name: "Low Value Recurring", condition: "Amount < $500 & recurring", approvers: 0, timeout: "N/A", autoApprove: true, status: "Active" },
  { name: "Whitelisted Vendor Pay", condition: "Merchant in whitelist", approvers: 0, timeout: "N/A", autoApprove: true, status: "Active" },
  { name: "Suspicious Activity", condition: "Risk score > 0.8", approvers: 3, timeout: "2h", autoApprove: false, status: "Disabled" },
]

const stats = [
  { label: "Approval Rules", value: "8", icon: UserCheck },
  { label: "Pending Approvals", value: "3", icon: Clock },
  { label: "Avg Approval Time", value: "12m", icon: CheckCircle },
  { label: "Auto-Approved", value: "67%", icon: ChartBar },
]

const statusConfig: Record<ApprovalRule["status"], { color: string }> = {
  Active: { color: "bg-success" },
  Disabled: { color: "bg-destructive" },
}

export default function ApprovalConfigPage() {
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
              {approvalRules.map((rule) => {
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
        </CardContent>
      </Card>
    </div>
  )
}
