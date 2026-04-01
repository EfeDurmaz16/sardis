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
  Spinner,
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

type Mandate = {
  mandate_id: string
  name: string
  agent_id: string
  limit_amount: string
  used_amount: string
  remaining_amount: string
  period: string
  status: string
  created_at: string
}

const statusConfig: Record<string, { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  exhausted: { color: "bg-destructive", label: "Exhausted" },
  paused: { color: "bg-warning", label: "Paused" },
}

const periodVariant: Record<string, "outline"> = {
  daily: "outline",
  weekly: "outline",
  monthly: "outline",
  Daily: "outline",
  Weekly: "outline",
  Monthly: "outline",
}

export default function MandatesPage() {
  const { data: remoteMandates, loading } = useSardis<Mandate[]>("api/v2/spending-mandates")
  const mandates = remoteMandates ?? []

  const [dialogOpen, setDialogOpen] = useState(false)

  // Form state
  const [purpose, setPurpose] = useState("")
  const [perTxLimit, setPerTxLimit] = useState("")
  const [dailyLimit, setDailyLimit] = useState("")
  const [approvalMode, setApprovalMode] = useState<string>("auto")

  // Compute stats dynamically
  const activeCount = mandates.filter((m) => m.status === "active").length
  const totalLimit = mandates.reduce(
    (sum, m) => sum + (parseFloat(m.limit_amount) || 0),
    0,
  )
  const totalUsed = mandates.reduce(
    (sum, m) => sum + (parseFloat(m.used_amount) || 0),
    0,
  )
  const utilization = totalLimit > 0 ? ((totalUsed / totalLimit) * 100).toFixed(1) : "0.0"

  const stats = [
    { label: "Active Mandates", value: String(activeCount), icon: ShieldCheck },
    { label: "Total Limit", value: `$${totalLimit.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, icon: CurrencyDollar },
    { label: "Used This Period", value: `$${totalUsed.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, icon: ChartBar },
    { label: "Utilization", value: `${utilization}%`, icon: Gauge },
  ]

  function resetForm() {
    setPurpose("")
    setPerTxLimit("")
    setDailyLimit("")
    setApprovalMode("auto")
  }

  function handleCreate() {
    if (!purpose.trim()) return
    // TODO: POST to API to create mandate
    setDialogOpen(false)
    resetForm()
    toast.success("Mandate created")
  }

  function handleActivate(id: string) {
    // TODO: PATCH to API
    toast.success("Mandate activated")
  }

  function handleSuspend(id: string) {
    // TODO: PATCH to API
    toast.success("Mandate suspended")
  }

  function handleRevoke(id: string) {
    // TODO: DELETE to API
    toast.success("Mandate revoked")
  }

  function formatCurrency(val: string) {
    const n = parseFloat(val)
    if (isNaN(n)) return "$0.00"
    return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
  }

  function computeUsedPct(m: Mandate) {
    const limit = parseFloat(m.limit_amount) || 0
    const used = parseFloat(m.used_amount) || 0
    return limit > 0 ? Math.round((used / limit) * 100) : 0
  }

  function formatPeriod(p: string) {
    return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()
  }

  function formatDate(d: string) {
    if (!d) return "—"
    const date = new Date(d)
    if (isNaN(date.getTime())) return d
    return date.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" })
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
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : s.value}</p>
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
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : mandates.length === 0 ? (
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
                const st = statusConfig[m.status] ?? { color: "bg-muted", label: m.status }
                const usedPct = computeUsedPct(m)
                const period = formatPeriod(m.period)
                return (
                  <ContextMenu key={m.mandate_id}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{m.name}</TableCell>
                      <TableCell className="text-muted-foreground">{m.agent_id}</TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(m.limit_amount)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={usedPct} className="h-1.5 w-16 [&_[data-slot=progress-track]]:h-1.5" />
                          <span className="text-xs text-muted-foreground">{formatCurrency(m.used_amount)}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatCurrency(m.remaining_amount)}</TableCell>
                      <TableCell>
                        <Badge variant={periodVariant[m.period] ?? "outline"}>{period}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(m.created_at)}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(m.mandate_id); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem disabled={m.status === "active"} onClick={() => handleActivate(m.mandate_id)}>Activate</ContextMenuItem>
                      <ContextMenuItem disabled={m.status === "paused"} onClick={() => handleSuspend(m.mandate_id)}>Suspend</ContextMenuItem>
                      <ContextMenuItem variant="destructive" onClick={() => handleRevoke(m.mandate_id)}>Revoke</ContextMenuItem>
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
