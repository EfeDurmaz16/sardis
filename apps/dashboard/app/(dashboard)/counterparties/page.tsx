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
} from "@phosphor-icons/react"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"

type Counterparty = {
  id: string
  name: string
  type: "Merchant" | "Exchange" | "Protocol" | "Individual"
  address: string
  riskScore: number
  txCount: number
  totalVolume: string
  status: "trusted" | "blocked" | "pending"
  addedDate: string
}

const initialCounterparties: Counterparty[] = [
  { id: "1", name: "Uniswap V3 Router", type: "Protocol", address: "0x68b3...4f2a", riskScore: 12, txCount: 1284, totalVolume: "$4.2M", status: "trusted", addedDate: "2025-09-14" },
  { id: "2", name: "Binance Hot Wallet", type: "Exchange", address: "0x28c6...e91d", riskScore: 18, txCount: 842, totalVolume: "$2.8M", status: "trusted", addedDate: "2025-08-22" },
  { id: "3", name: "Stripe Merchant Co", type: "Merchant", address: "0x9a1f...3b7c", riskScore: 8, txCount: 2103, totalVolume: "$6.1M", status: "trusted", addedDate: "2025-07-10" },
  { id: "4", name: "Unknown Wallet X", type: "Individual", address: "0xd4e7...1c5a", riskScore: 87, txCount: 3, totalVolume: "$12,400", status: "blocked", addedDate: "2026-01-18" },
  { id: "5", name: "Aave Lending Pool", type: "Protocol", address: "0x7d2b...8e4f", riskScore: 10, txCount: 567, totalVolume: "$1.9M", status: "trusted", addedDate: "2025-10-05" },
  { id: "6", name: "Circle USDC Bridge", type: "Protocol", address: "0x3f8a...6d2e", riskScore: 5, txCount: 1890, totalVolume: "$8.4M", status: "trusted", addedDate: "2025-06-30" },
  { id: "7", name: "ShadyMixer.io", type: "Protocol", address: "0xe5c1...2a9b", riskScore: 95, txCount: 1, totalVolume: "$450", status: "blocked", addedDate: "2026-02-01" },
  { id: "8", name: "Coinbase Commerce", type: "Exchange", address: "0x1b4e...7f3d", riskScore: 14, txCount: 634, totalVolume: "$3.2M", status: "trusted", addedDate: "2025-08-15" },
  { id: "9", name: "New Vendor LLC", type: "Merchant", address: "0x8c6d...5a1e", riskScore: 45, txCount: 12, totalVolume: "$34,200", status: "pending", addedDate: "2026-03-20" },
  { id: "10", name: "FlaggedTrader99", type: "Individual", address: "0xf2a9...4b8c", riskScore: 72, txCount: 28, totalVolume: "$89,000", status: "blocked", addedDate: "2026-01-05" },
]

const stats = [
  { label: "Total Counterparties", value: "42", icon: Users },
  { label: "Trusted", value: "35", icon: ShieldCheck },
  { label: "Blocked", value: "4", icon: Prohibit },
  { label: "Pending Review", value: "3", icon: Hourglass },
]

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
  const [tab, setTab] = useState("all")
  const [counterparties, setCounterparties] = useState<Counterparty[]>(initialCounterparties)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)

  // Form state
  const [cpName, setCpName] = useState("")
  const [cpAddress, setCpAddress] = useState("")
  const [cpType, setCpType] = useState<string>("wallet")

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
      setCounterparties((prev) =>
        prev.map((cp) =>
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
        riskScore: Math.floor(Math.random() * 50),
        txCount: 0,
        totalVolume: "$0",
        status: "pending",
        addedDate: new Date().toISOString().slice(0, 10),
      }
      setCounterparties((prev) => [...prev, newCp])
      toast.success("Counterparty added")
    }
    setDialogOpen(false)
    resetForm()
  }

  function handleDelete(id: string) {
    setCounterparties((prev) => prev.filter((cp) => cp.id !== id))
    toast.success("Counterparty deleted")
  }

  const filtered = tab === "all"
    ? counterparties
    : counterparties.filter((c) => c.status === tab)

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
                        <span className={`font-semibold tabular-nums ${riskColor(cp.riskScore)}`}>
                          {cp.riskScore}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{cp.txCount.toLocaleString()}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{cp.totalVolume}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{cp.addedDate}</TableCell>
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
