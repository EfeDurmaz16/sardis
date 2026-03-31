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
import { useSardis } from "@/hooks/use-sardis"

type ApprovalStatus = "pending" | "approved" | "rejected"

type Approval = {
  id: string
  type: string
  description: string
  requestedBy: string
  amount: string
  riskLevel: string
  submittedAt: string
  status: ApprovalStatus
  resolvedBy?: string
}

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
  const { data: remoteApprovals, loading } = useSardis<Approval[]>("api/v2/approvals")
  const [tab, setTab] = useState("pending")
  const [approvals, setApprovals] = useState<Approval[]>([])

  // Sync remote data when it arrives
  if (remoteApprovals && remoteApprovals.length > 0 && approvals.length === 0) {
    setApprovals(remoteApprovals)
  }

  const pendingCount = approvals.filter(a => a.status === "pending").length
  const approvedCount = approvals.filter(a => a.status === "approved").length
  const rejectedCount = approvals.filter(a => a.status === "rejected").length

  const stats = [
    { label: "Pending", value: String(pendingCount), icon: Hourglass },
    { label: "Approved", value: String(approvedCount), icon: CheckCircle },
    { label: "Rejected", value: String(rejectedCount), icon: XCircle },
    { label: "Total", value: String(approvals.length), icon: Timer },
  ]

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
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : s.value}</p>
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
