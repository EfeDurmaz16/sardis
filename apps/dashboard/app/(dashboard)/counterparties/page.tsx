"use client"

import { useState, useMemo } from "react"
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
  Users,
  ShieldCheck,
  Prohibit,
  Hourglass,
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
import { useSardis } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type Counterparty = {
  id: string
  name: string
  type: "Merchant" | "Exchange" | "Protocol" | "Individual"
  address: string
  risk_score: number
  tx_count: number
  total_volume: string
  status: "trusted" | "blocked" | "pending"
  added_date: string
}

const statusConfig: Record<Counterparty["status"], { color: string; label: string }> = {
  trusted: { color: "bg-success", label: "Trusted" },
  blocked: { color: "bg-destructive", label: "Blocked" },
  pending: { color: "bg-warning", label: "Pending" },
}

const typeVariant: Record<Counterparty["type"], "outline"> = {
  Merchant: "outline",
  Exchange: "outline",
  Protocol: "outline",
  Individual: "outline",
}

function riskColor(score: number) {
  if (score <= 25) return "text-success"
  if (score <= 50) return "text-warning"
  if (score <= 75) return "text-warning"
  return "text-destructive"
}

type CpType = "wallet" | "merchant" | "agent"
const cpTypeToDisplay: Record<CpType, Counterparty["type"]> = {
  wallet: "Individual",
  merchant: "Merchant",
  agent: "Protocol",
}

export default function CounterpartiesPage() {
  const { data, loading, error, refetch } = useSardis<Counterparty[]>("api/v2/counterparties")

  const [tab, setTab] = useState("all")
  const [localOverrides, setLocalOverrides] = useState<Counterparty[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  // Form state
  const [cpName, setCpName] = useState("")
  const [cpAddress, setCpAddress] = useState("")
  const [cpType, setCpType] = useState<string>("wallet")

  const counterparties = useMemo(() => {
    if (localOverrides.length > 0) return localOverrides
    return data ?? []
  }, [data, localOverrides])

  const stats = useMemo(() => {
    const total = counterparties.length
    const trusted = counterparties.filter(c => c.status === "trusted").length
    const blocked = counterparties.filter(c => c.status === "blocked").length
    const pending = counterparties.filter(c => c.status === "pending").length
    return [
      { label: "Total Counterparties", value: String(total), icon: Users },
      { label: "Trusted", value: String(trusted), icon: ShieldCheck },
      { label: "Blocked", value: String(blocked), icon: Prohibit },
      { label: "Pending Review", value: String(pending), icon: Hourglass },
    ]
  }, [counterparties])

  function resetForm() {
    setCpName("")
    setCpAddress("")
    setCpType("wallet")
    setEditingId(null)
  }

  function openCreateDialog() {
    resetForm()
    setDialogOpen(true)
  }

  function openEditDialog(cp: Counterparty) {
    setCpName(cp.name)
    setCpAddress(cp.address)
    // reverse map type
    const reverseType = cp.type === "Individual" ? "wallet" : cp.type === "Merchant" ? "merchant" : "agent"
    setCpType(reverseType)
    setEditingId(cp.id)
    setDialogOpen(true)
  }

  function handleSubmit() {
    if (!cpName.trim() || !cpAddress.trim()) return

    if (editingId) {
      setLocalOverrides(
        counterparties.map((cp) =>
          cp.id === editingId
            ? {
                ...cp,
                name: cpName.trim(),
                address: cpAddress.trim(),
                type: cpTypeToDisplay[cpType as CpType],
              }
            : cp
        )
      )
      toast.success("Counterparty updated")
    } else {
      const randomHex = () => Math.random().toString(16).substring(2, 6)
      const newCp: Counterparty = {
        id: crypto.randomUUID(),
        name: cpName.trim(),
        type: cpTypeToDisplay[cpType as CpType],
        address: cpAddress.trim() || `0x${randomHex()}...${randomHex()}`,
        risk_score: Math.floor(Math.random() * 50),
        tx_count: 0,
        total_volume: "$0",
        status: "pending",
        added_date: new Date().toISOString().slice(0, 10),
      }
      setLocalOverrides([...counterparties, newCp])
      toast.success("Counterparty added")
    }
    setDialogOpen(false)
    resetForm()
  }

  function handleDelete(id: string) {
    setLocalOverrides(counterparties.filter((cp) => cp.id !== id))
    toast.success("Counterparty deleted")
  }

  const filtered = tab === "all"
    ? counterparties
    : counterparties.filter((c) => c.status === tab)

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Counterparties</h1>
          <p className="text-sm text-muted-foreground">Manage trusted, blocked, and pending counterparties</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error && counterparties.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Counterparties</h1>
          <p className="text-sm text-muted-foreground">Manage trusted, blocked, and pending counterparties</p>
        </div>
        <EmptyState
          icon={Users}
          title="Counterparties unavailable"
          description={error}
          action={refetch}
          actionLabel="Retry"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Counterparties</h1>
          <p className="text-sm text-muted-foreground">Manage trusted, blocked, and pending counterparties</p>
        </div>
        <Button onClick={openCreateDialog}>
          <Plus className="h-4 w-4" />
          Add Counterparty
        </Button>
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
          <CardTitle>All Counterparties</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="trusted">Trusted</TabsTrigger>
                <TabsTrigger value="blocked">Blocked</TabsTrigger>
                <TabsTrigger value="pending">Pending</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {filtered.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No counterparties"
              description="Counterparties will appear here once they are registered via the API or added manually."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Address</TableHead>
                  <TableHead className="text-right">Risk Score</TableHead>
                  <TableHead className="text-right">Transactions</TableHead>
                  <TableHead className="text-right">Total Volume</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Added</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((cp) => {
                  const st = statusConfig[cp.status]
                  return (
                    <ContextMenu key={cp.id}>
                      <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-medium">{cp.name}</TableCell>
                        <TableCell>
                          <Badge variant={typeVariant[cp.type]}>{cp.type}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">{cp.address}</TableCell>
                        <TableCell className="text-right">
                          <span className={`font-semibold tabular-nums ${riskColor(cp.risk_score)}`}>
                            {cp.risk_score}
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{cp.tx_count.toLocaleString()}</TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">{cp.total_volume}</TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1.5">
                            <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                            {st.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{cp.added_date}</TableCell>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem onClick={() => { navigator.clipboard.writeText(cp.address); toast.success("Copied to clipboard") }}>
                          Copy ID
                        </ContextMenuItem>
                        <ContextMenuSeparator />
                        <ContextMenuItem onClick={() => openEditDialog(cp)}>Edit</ContextMenuItem>
                        <ContextMenuItem variant="destructive" onClick={() => handleDelete(cp.id)}>Delete</ContextMenuItem>
                      </ContextMenuContent>
                    </ContextMenu>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add / Edit Counterparty Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Counterparty" : "Add Counterparty"}</DialogTitle>
            <DialogDescription>
              {editingId ? "Update counterparty details." : "Register a new counterparty."}
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit()
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Name</label>
              <Input
                placeholder="e.g. Acme Corp"
                value={cpName}
                onChange={(e) => setCpName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Address</label>
              <Input
                placeholder="e.g. 0x1234...abcd"
                value={cpAddress}
                onChange={(e) => setCpAddress(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Type</label>
              <Select value={cpType} onValueChange={(v) => v && setCpType(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="wallet">Wallet</SelectItem>
                  <SelectItem value="merchant">Merchant</SelectItem>
                  <SelectItem value="agent">Agent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">{editingId ? "Save Changes" : "Add Counterparty"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
