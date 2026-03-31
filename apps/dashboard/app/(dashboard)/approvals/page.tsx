"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
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
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Hourglass,
  CheckCircle,
  XCircle,
  Timer,
} from "@phosphor-icons/react"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"

type ApprovalStatus = "pending" | "approved" | "rejected"

type Approval = {
  id: string
  type: "Payment" | "Agent" | "Config" | "Access"
  description: string
  requestedBy: string
  amount: string
  riskLevel: "low" | "medium" | "high"
  submittedAt: string
  status: ApprovalStatus
  resolvedBy?: string
}

const initialApprovals: Approval[] = [
  { id: "APR-001", type: "Payment", description: "Large payment to new vendor — Acme Corp", requestedBy: "Sarah Chen", amount: "$45,000", riskLevel: "high", submittedAt: "10 min ago", status: "pending" },
  { id: "APR-002", type: "Agent", description: "Register new payment routing agent", requestedBy: "Mike Torres", amount: "—", riskLevel: "medium", submittedAt: "34 min ago", status: "pending" },
  { id: "APR-003", type: "Config", description: "Increase daily mandate limit to $50k", requestedBy: "Alex Kim", amount: "$50,000", riskLevel: "high", submittedAt: "1 hr ago", status: "pending" },
  { id: "APR-004", type: "Payment", description: "Recurring subscription — Cloud Services Inc", requestedBy: "Sarah Chen", amount: "$2,400", riskLevel: "low", submittedAt: "2 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-005", type: "Access", description: "API key generation for staging environment", requestedBy: "Dev Team", amount: "—", riskLevel: "low", submittedAt: "3 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-006", type: "Payment", description: "Cross-chain bridge transfer to Arbitrum", requestedBy: "Mike Torres", amount: "$8,200", riskLevel: "medium", submittedAt: "3 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-007", type: "Config", description: "Modify geo-blocking rules for EU region", requestedBy: "Compliance Team", amount: "—", riskLevel: "medium", submittedAt: "4 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-008", type: "Agent", description: "Activate yield optimizer in production", requestedBy: "Alex Kim", amount: "—", riskLevel: "high", submittedAt: "5 hrs ago", status: "rejected", resolvedBy: "Admin" },
  { id: "APR-009", type: "Payment", description: "Bulk payout to 15 contractors", requestedBy: "HR System", amount: "$32,500", riskLevel: "medium", submittedAt: "5 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-010", type: "Access", description: "Grant admin access to new team member", requestedBy: "Sarah Chen", amount: "—", riskLevel: "high", submittedAt: "6 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-011", type: "Payment", description: "Refund request — duplicate transaction", requestedBy: "Support", amount: "$1,200", riskLevel: "low", submittedAt: "6 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-012", type: "Config", description: "Disable rate limiting for load test", requestedBy: "Dev Team", amount: "—", riskLevel: "high", submittedAt: "7 hrs ago", status: "rejected", resolvedBy: "Admin" },
  { id: "APR-013", type: "Payment", description: "Monthly infrastructure payment — AWS", requestedBy: "Treasury Bot", amount: "$18,700", riskLevel: "low", submittedAt: "8 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-014", type: "Agent", description: "Deploy updated expense tracker agent", requestedBy: "Mike Torres", amount: "—", riskLevel: "low", submittedAt: "9 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-015", type: "Payment", description: "One-time bonus distribution", requestedBy: "HR System", amount: "$24,000", riskLevel: "medium", submittedAt: "10 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-016", type: "Access", description: "Revoke API access for departed employee", requestedBy: "Security Team", amount: "—", riskLevel: "low", submittedAt: "12 hrs ago", status: "approved", resolvedBy: "Admin" },
  { id: "APR-017", type: "Config", description: "Update webhook endpoints for notifications", requestedBy: "Dev Team", amount: "—", riskLevel: "low", submittedAt: "14 hrs ago", status: "approved", resolvedBy: "Admin" },
]

const stats = [
  { label: "Pending", value: "3", icon: Hourglass },
  { label: "Approved Today", value: "12", icon: CheckCircle },
  { label: "Rejected Today", value: "2", icon: XCircle },
  { label: "Avg Response Time", value: "12m", icon: Timer },
]

const typeVariant: Record<Approval["type"], "default" | "secondary" | "outline" | "destructive"> = {
  Payment: "default",
  Agent: "secondary",
  Config: "outline",
  Access: "destructive",
}

const riskColor: Record<Approval["riskLevel"], string> = {
  low: "bg-success",
  medium: "bg-warning",
  high: "bg-destructive",
}

export default function ApprovalsPage() {
  const [tab, setTab] = useState("pending")
  const [approvals, setApprovals] = useState<Approval[]>(initialApprovals)

  const filtered = tab === "all"
    ? approvals
    : approvals.filter((a) => a.status === tab)

  function handleApprove(id: string) {
    setApprovals((prev) => prev.map((a) =>
      a.id === id ? { ...a, status: "approved" as ApprovalStatus, resolvedBy: "You" } : a
    ))
    toast.success(`${id} approved`)
  }

  function handleReject(id: string) {
    setApprovals((prev) => prev.map((a) =>
      a.id === id ? { ...a, status: "rejected" as ApprovalStatus, resolvedBy: "You" } : a
    ))
    toast.success(`${id} rejected`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Approvals</h1>
        <p className="text-sm text-muted-foreground">Review and manage pending approval requests</p>
      </div>

      {/* Stats */}
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

      {/* Approvals Table */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle>Approval Requests</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="pending">Pending</TabsTrigger>
                <TabsTrigger value="approved">Approved</TabsTrigger>
                <TabsTrigger value="rejected">Rejected</TabsTrigger>
                <TabsTrigger value="all">All</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {filtered.length === 0 ? (
            <EmptyState
              icon={Hourglass}
              title="No pending approvals"
              description="All clear! Approvals will appear here when transactions need human review"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Request ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Requested By</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Submitted</TableHead>
                {tab === "pending" && <TableHead>Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((approval) => (
                <ContextMenu key={approval.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                    <TableCell className="pl-4"><Badge variant="outline" className="font-mono">{approval.id}</Badge></TableCell>
                    <TableCell>
                      <Badge variant={typeVariant[approval.type]}>{approval.type}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[240px] truncate">{approval.description}</TableCell>
                    <TableCell className="text-muted-foreground">{approval.requestedBy}</TableCell>
                    <TableCell className="text-right tabular-nums font-medium">{approval.amount}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${riskColor[approval.riskLevel]}`} />
                        <span className="capitalize text-muted-foreground">{approval.riskLevel}</span>
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{approval.submittedAt}</TableCell>
                    {tab === "pending" && (
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <Button size="xs" variant="default" onClick={() => handleApprove(approval.id)}>Approve</Button>
                          <Button size="xs" variant="destructive" onClick={() => handleReject(approval.id)}>Reject</Button>
                        </div>
                      </TableCell>
                    )}
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(approval.id); toast.success("Copied to clipboard") }}>
                      Copy ID
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem disabled={approval.status !== "pending"} onClick={() => handleApprove(approval.id)}>Approve</ContextMenuItem>
                    <ContextMenuItem variant="destructive" disabled={approval.status !== "pending"} onClick={() => handleReject(approval.id)}>Reject</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
