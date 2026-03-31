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
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import {
  ShieldCheck,
  CurrencyDollar,
  ChartBar,
  Gauge,
  Plus,
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

type Mandate = {
  id: string
  name: string
  agent: string
  limit: string
  used: string
  usedPct: number
  remaining: string
  period: "Daily" | "Weekly" | "Monthly"
  status: "active" | "exhausted" | "paused"
  created: string
}

const initialMandates: Mandate[] = [
  { id: "1", name: "Vendor Payments", agent: "Vendor Pay Agent", limit: "$10,000", used: "$4,200", usedPct: 42, remaining: "$5,800", period: "Daily", status: "active", created: "Jan 15, 2026" },
  { id: "2", name: "Cloud Infrastructure", agent: "Expense Tracker v2", limit: "$25,000", used: "$18,350", usedPct: 73, remaining: "$6,650", period: "Weekly", status: "active", created: "Feb 02, 2026" },
  { id: "3", name: "Treasury Operations", agent: "Treasury Sweep Bot", limit: "$100,000", used: "$67,200", usedPct: 67, remaining: "$32,800", period: "Monthly", status: "active", created: "Dec 10, 2025" },
  { id: "4", name: "Employee Payroll", agent: "Payroll Distributor", limit: "$200,000", used: "$54,100", usedPct: 27, remaining: "$145,900", period: "Monthly", status: "active", created: "Nov 20, 2025" },
  { id: "5", name: "Gas Fee Budget", agent: "Gas Optimizer v3", limit: "$2,000", used: "$1,850", usedPct: 93, remaining: "$150", period: "Daily", status: "active", created: "Mar 01, 2026" },
  { id: "6", name: "Bridge Transfers", agent: "Cross-chain Bridge", limit: "$50,000", used: "$31,600", usedPct: 63, remaining: "$18,400", period: "Weekly", status: "active", created: "Jan 28, 2026" },
  { id: "7", name: "SaaS Subscriptions", agent: "Subscription Manager", limit: "$15,000", used: "$8,920", usedPct: 59, remaining: "$6,080", period: "Monthly", status: "paused", created: "Feb 14, 2026" },
  { id: "8", name: "Invoice Settlement", agent: "Invoice Settler", limit: "$20,000", used: "$20,000", usedPct: 100, remaining: "$0", period: "Weekly", status: "exhausted", created: "Feb 22, 2026" },
  { id: "9", name: "Yield Operations", agent: "Yield Harvester", limit: "$8,000", used: "$3,250", usedPct: 41, remaining: "$4,750", period: "Daily", status: "active", created: "Mar 10, 2026" },
  { id: "10", name: "Contractor Payments", agent: "Payroll Distributor", limit: "$70,000", used: "$12,150", usedPct: 17, remaining: "$57,850", period: "Monthly", status: "active", created: "Mar 05, 2026" },
]

const stats = [
  { label: "Active Mandates", value: "18", icon: ShieldCheck },
  { label: "Total Limit", value: "$500,000", icon: CurrencyDollar },
  { label: "Used This Month", value: "$148,000", icon: ChartBar },
  { label: "Utilization", value: "29.6%", icon: Gauge },
]

const statusConfig: Record<Mandate["status"], { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  exhausted: { color: "bg-destructive", label: "Exhausted" },
  paused: { color: "bg-warning", label: "Paused" },
}

const periodVariant: Record<string, "outline"> = {
  Daily: "outline",
  Weekly: "outline",
  Monthly: "outline",
}

export default function MandatesPage() {
  const [mandates, setMandates] = useState<Mandate[]>(initialMandates)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Form state
  const [purpose, setPurpose] = useState("")
  const [perTxLimit, setPerTxLimit] = useState("")
  const [dailyLimit, setDailyLimit] = useState("")
  const [approvalMode, setApprovalMode] = useState<string>("auto")

  function resetForm() {
    setPurpose("")
    setPerTxLimit("")
    setDailyLimit("")
    setApprovalMode("auto")
  }

  function handleCreate() {
    if (!purpose.trim()) return
    const limitVal = dailyLimit || perTxLimit || "$0"
    const newMandate: Mandate = {
      id: crypto.randomUUID(),
      name: purpose.trim(),
      agent: "Unassigned",
      limit: `$${Number(limitVal.replace(/[^0-9.]/g, "") || 0).toLocaleString()}`,
      used: "$0",
      usedPct: 0,
      remaining: `$${Number(limitVal.replace(/[^0-9.]/g, "") || 0).toLocaleString()}`,
      period: "Daily",
      status: "active",
      created: new Date().toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }),
    }
    setMandates((prev) => [...prev, newMandate])
    setDialogOpen(false)
    resetForm()
    toast.success("Mandate created")
  }

  function handleActivate(id: string) {
    setMandates((prev) => prev.map((m) => m.id === id ? { ...m, status: "active" as const } : m))
    toast.success("Mandate activated")
  }

  function handleSuspend(id: string) {
    setMandates((prev) => prev.map((m) => m.id === id ? { ...m, status: "paused" as const } : m))
    toast.success("Mandate suspended")
  }

  function handleRevoke(id: string) {
    setMandates((prev) => prev.filter((m) => m.id !== id))
    toast.success("Mandate revoked")
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Mandates</h1>
        <p className="text-sm text-muted-foreground">Configure and monitor spending mandates for agents</p>
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
          <CardTitle>All Mandates</CardTitle>
          <CardAction>
            <Button size="sm" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              Create Mandate
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {mandates.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No mandates"
              description="Create a spending mandate to control agent budgets"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Mandate Name</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="text-right">Spending Limit</TableHead>
                <TableHead className="w-40">Used</TableHead>
                <TableHead className="text-right">Remaining</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mandates.map((m) => {
                const st = statusConfig[m.status]
                return (
                  <ContextMenu key={m.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{m.name}</TableCell>
                      <TableCell className="text-muted-foreground">{m.agent}</TableCell>
                      <TableCell className="text-right tabular-nums">{m.limit}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={m.usedPct} className="h-1.5 w-16 [&_[data-slot=progress-track]]:h-1.5" />
                          <span className="text-xs text-muted-foreground">{m.used}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{m.remaining}</TableCell>
                      <TableCell>
                        <Badge variant={periodVariant[m.period]}>{m.period}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{m.created}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(m.name); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem disabled={m.status === "active"} onClick={() => handleActivate(m.id)}>Activate</ContextMenuItem>
                      <ContextMenuItem disabled={m.status === "paused"} onClick={() => handleSuspend(m.id)}>Suspend</ContextMenuItem>
                      <ContextMenuItem variant="destructive" onClick={() => handleRevoke(m.id)}>Revoke</ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem>Expand</ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                )
              })}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Mandate Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Mandate</DialogTitle>
            <DialogDescription>Set up a new spending mandate for an agent.</DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleCreate()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Purpose</label>
              <Input
                placeholder="e.g. Vendor Payments"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Per-Transaction Limit ($)</label>
              <Input
                placeholder="e.g. 5000"
                value={perTxLimit}
                onChange={(e) => setPerTxLimit(e.target.value)}
                type="number"
                min="0"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Daily Limit ($)</label>
              <Input
                placeholder="e.g. 10000"
                value={dailyLimit}
                onChange={(e) => setDailyLimit(e.target.value)}
                type="number"
                min="0"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Approval Mode</label>
              <Select value={approvalMode} onValueChange={(v) => v && setApprovalMode(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto-approve</SelectItem>
                  <SelectItem value="manual">Manual approval</SelectItem>
                  <SelectItem value="threshold">Threshold-based</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Create Mandate</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
