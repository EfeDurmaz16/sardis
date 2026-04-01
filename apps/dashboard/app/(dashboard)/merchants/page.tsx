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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Storefront,
  CheckCircle,
  Clock,
  CurrencyDollar,
  ArrowUp,
  ArrowDown,
  ArrowsDownUp,
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
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import { useSardis } from "@/hooks/use-sardis"

type Merchant = {
  merchant_id: string
  name: string
  category: string
  status: "verified" | "pending" | "suspended"
  total_volume: number
  transaction_count: number
  chains: string[]
  created_at: string
}

const statusConfig: Record<Merchant["status"], { color: string; label: string }> = {
  verified: { color: "bg-success", label: "Verified" },
  pending: { color: "bg-warning", label: "Pending" },
  suspended: { color: "bg-destructive", label: "Suspended" },
}

const chainVariant: Record<string, "outline"> = {
  Ethereum: "outline",
  Polygon: "outline",
  Arbitrum: "outline",
  Optimism: "outline",
  Base: "outline",
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}k`
  return `$${value.toFixed(0)}`
}

function formatVolume(value: number): string {
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function formatCount(value: number): string {
  return value.toLocaleString("en-US")
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export default function MerchantsPage() {
  const { data: remoteMerchants, loading, refetch } = useSardis<Merchant[]>("api/v2/merchants")
  const merchants = remoteMerchants ?? []

  const [tab, setTab] = useState("all")
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [selectedMerchant, setSelectedMerchant] = useState<Merchant | null>(null)
  const [checkoutMerchant, setCheckoutMerchant] = useState<Merchant | null>(null)
  const [checkoutOpen, setCheckoutOpen] = useState(false)

  /* ---------- Computed stats ---------- */
  const totalMerchants = merchants.length
  const verifiedCount = merchants.filter((m) => m.status === "verified").length
  const pendingCount = merchants.filter((m) => m.status === "pending").length
  const totalVolume = merchants.reduce((sum, m) => sum + (m.total_volume ?? 0), 0)

  const stats = [
    { label: "Total Merchants", value: String(totalMerchants), icon: Storefront },
    { label: "Verified", value: String(verifiedCount), icon: CheckCircle },
    { label: "Pending Review", value: String(pendingCount), icon: Clock },
    { label: "30d Volume", value: formatCurrency(totalVolume), icon: CurrencyDollar },
  ]

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  const filtered = tab === "all"
    ? merchants
    : merchants.filter((m) => m.status === tab)

  const sorted = [...filtered].sort((a, b) => {
    if (!sortKey) return 0
    let cmp = 0
    if (sortKey === "total_volume") {
      cmp = (a.total_volume ?? 0) - (b.total_volume ?? 0)
    } else if (sortKey === "transaction_count") {
      cmp = (a.transaction_count ?? 0) - (b.transaction_count ?? 0)
    } else {
      const av = String(a[sortKey as keyof Merchant] ?? "")
      const bv = String(b[sortKey as keyof Merchant] ?? "")
      cmp = av.localeCompare(bv)
    }
    return sortDir === "asc" ? cmp : -cmp
  })

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Merchants</h1>
        <p className="text-sm text-muted-foreground">Manage merchant accounts and verification status</p>
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
          <CardTitle>All Merchants</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="verified">Verified</TabsTrigger>
                <TabsTrigger value="pending">Pending</TabsTrigger>
                <TabsTrigger value="suspended">Suspended</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {filtered.length === 0 ? (
            <EmptyState
              icon={Storefront}
              title="No merchants"
              description="Register merchants to accept payments from your agents"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead
                  className="pl-4 cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("name")}
                >
                  <span className="flex items-center gap-1">
                    Merchant Name
                    {sortKey === "name" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead>Category</TableHead>
                <TableHead
                  className="cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("status")}
                >
                  <span className="flex items-center gap-1">
                    Verification Status
                    {sortKey === "status" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("total_volume")}
                >
                  <span className="flex items-center justify-end gap-1">
                    Total Volume
                    {sortKey === "total_volume" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("transaction_count")}
                >
                  <span className="flex items-center justify-end gap-1">
                    Transactions
                    {sortKey === "transaction_count" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead>Chains Supported</TableHead>
                <TableHead>Added Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sorted.map((m) => {
                const st = statusConfig[m.status]
                return (
                  <ContextMenu key={m.merchant_id}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{m.name}</TableCell>
                      <TableCell className="text-muted-foreground">{m.category}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{formatVolume(m.total_volume)}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{formatCount(m.transaction_count)}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {m.chains.map((chain) => (
                            <Badge key={chain} variant={chainVariant[chain] ?? "outline"}>
                              {chain}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{formatDate(m.created_at)}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(m.merchant_id); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onClick={() => setSelectedMerchant(prev => prev?.merchant_id === m.merchant_id ? null : m)}>View Details</ContextMenuItem>
                      <ContextMenuItem onClick={() => { setCheckoutMerchant(m); setCheckoutOpen(true) }}>Create Checkout Link</ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                )
              })}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      {/* Merchant Detail Panel */}
      {selectedMerchant && (
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center justify-between">
              <span>{selectedMerchant.name}</span>
              <Button variant="ghost" size="sm" onClick={() => setSelectedMerchant(null)}>
                Close
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-3">
              <div>
                <p className="text-xs text-muted-foreground">Category</p>
                <p className="text-sm">{selectedMerchant.category}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Status</p>
                <span className="inline-flex items-center gap-1.5 text-sm">
                  <span className={`h-1.5 w-1.5 rounded-full ${statusConfig[selectedMerchant.status].color}`} />
                  {statusConfig[selectedMerchant.status].label}
                </span>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Volume</p>
                <p className="text-sm font-medium">{formatVolume(selectedMerchant.total_volume)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Transactions</p>
                <p className="text-sm">{formatCount(selectedMerchant.transaction_count)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Chains Supported</p>
                <div className="flex flex-wrap gap-1 pt-0.5">
                  {selectedMerchant.chains.map((chain) => (
                    <Badge key={chain} variant="outline">{chain}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Added Date</p>
                <p className="text-sm">{formatDate(selectedMerchant.created_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Checkout Link Dialog */}
      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Checkout Link</DialogTitle>
            <DialogDescription>
              Generate a checkout link for {checkoutMerchant?.name}
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const amount = (formData.get("amount") as string).trim()
              const description = (formData.get("description") as string).trim()
              if (!amount || !checkoutMerchant) return
              try {
                const res = await fetch(`/api/sardis/api/v2/merchants/${checkoutMerchant.merchant_id}/links`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    amount: parseFloat(amount),
                    description,
                  }),
                })
                if (!res.ok) throw new Error("Failed")
                toast.success(`Checkout link created for ${checkoutMerchant.name}`)
                setCheckoutOpen(false)
                refetch()
              } catch {
                toast.error("Failed to create checkout link")
              }
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Amount ($)</p>
              <Input name="amount" type="number" step="0.01" min="0" placeholder="0.00" required />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Description</p>
              <Input name="description" placeholder="Payment for..." />
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Create Link</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
