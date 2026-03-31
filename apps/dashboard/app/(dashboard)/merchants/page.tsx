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

type Merchant = {
  name: string
  category: string
  status: "verified" | "pending" | "suspended"
  totalVolume: string
  transactionCount: string
  chains: string[]
  addedDate: string
}

const merchants: Merchant[] = [
  { name: "Stripe", category: "Payment Processing", status: "verified", totalVolume: "$245,800", transactionCount: "1,842", chains: ["Ethereum", "Polygon"], addedDate: "Jan 12, 2025" },
  { name: "Amazon Web Services", category: "Cloud Infrastructure", status: "verified", totalVolume: "$128,400", transactionCount: "423", chains: ["Ethereum"], addedDate: "Feb 3, 2025" },
  { name: "Vercel", category: "Cloud Hosting", status: "verified", totalVolume: "$42,600", transactionCount: "156", chains: ["Base", "Polygon"], addedDate: "Mar 18, 2025" },
  { name: "Datadog", category: "Observability", status: "verified", totalVolume: "$38,200", transactionCount: "89", chains: ["Ethereum", "Arbitrum"], addedDate: "Apr 5, 2025" },
  { name: "GitHub", category: "Developer Tools", status: "verified", totalVolume: "$18,950", transactionCount: "312", chains: ["Polygon"], addedDate: "Jan 28, 2025" },
  { name: "Cloudflare", category: "CDN & Security", status: "verified", totalVolume: "$67,300", transactionCount: "198", chains: ["Ethereum", "Optimism"], addedDate: "Feb 14, 2025" },
  { name: "OpenAI", category: "AI Services", status: "pending", totalVolume: "$92,400", transactionCount: "567", chains: ["Ethereum", "Base"], addedDate: "Mar 22, 2026" },
  { name: "Supabase", category: "Backend Services", status: "verified", totalVolume: "$24,100", transactionCount: "143", chains: ["Polygon", "Arbitrum"], addedDate: "May 10, 2025" },
  { name: "Twilio", category: "Communications", status: "verified", totalVolume: "$56,800", transactionCount: "234", chains: ["Ethereum"], addedDate: "Mar 1, 2025" },
  { name: "Notion", category: "Productivity", status: "pending", totalVolume: "$15,200", transactionCount: "67", chains: ["Base"], addedDate: "Mar 15, 2026" },
]

const stats = [
  { label: "Total Merchants", value: "18", icon: Storefront },
  { label: "Verified", value: "16", icon: CheckCircle },
  { label: "Pending Review", value: "2", icon: Clock },
  { label: "30d Volume", value: "$892k", icon: CurrencyDollar },
]

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

function parseCurrency(val: string): number {
  return parseFloat(val.replace(/[$,]/g, "")) || 0
}

function parseCount(val: string): number {
  return parseFloat(val.replace(/,/g, "")) || 0
}

export default function MerchantsPage() {
  const [tab, setTab] = useState("all")
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [selectedMerchant, setSelectedMerchant] = useState<Merchant | null>(null)
  const [checkoutMerchant, setCheckoutMerchant] = useState<Merchant | null>(null)
  const [checkoutOpen, setCheckoutOpen] = useState(false)

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
    if (sortKey === "totalVolume") {
      cmp = parseCurrency(a.totalVolume) - parseCurrency(b.totalVolume)
    } else if (sortKey === "transactionCount") {
      cmp = parseCount(a.transactionCount) - parseCount(b.transactionCount)
    } else {
      const av = a[sortKey as keyof Merchant] as string
      const bv = b[sortKey as keyof Merchant] as string
      cmp = av.localeCompare(bv)
    }
    return sortDir === "asc" ? cmp : -cmp
  })

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
                  onClick={() => toggleSort("totalVolume")}
                >
                  <span className="flex items-center justify-end gap-1">
                    Total Volume
                    {sortKey === "totalVolume" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("transactionCount")}
                >
                  <span className="flex items-center justify-end gap-1">
                    Transactions
                    {sortKey === "transactionCount" ? (
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
                  <ContextMenu key={m.name}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4 font-medium">{m.name}</TableCell>
                      <TableCell className="text-muted-foreground">{m.category}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{m.totalVolume}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{m.transactionCount}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {m.chains.map((chain) => (
                            <Badge key={chain} variant={chainVariant[chain] ?? "outline"}>
                              {chain}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{m.addedDate}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(m.name); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onClick={() => setSelectedMerchant(prev => prev?.name === m.name ? null : m)}>View Details</ContextMenuItem>
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
                <p className="text-sm font-medium">{selectedMerchant.totalVolume}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Transactions</p>
                <p className="text-sm">{selectedMerchant.transactionCount}</p>
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
                <p className="text-sm">{selectedMerchant.addedDate}</p>
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
            onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const amount = (formData.get("amount") as string).trim()
              const description = (formData.get("description") as string).trim()
              if (!amount) return
              toast.success(`Checkout link created for ${checkoutMerchant?.name}: $${amount}${description ? ` - ${description}` : ""}`)
              setCheckoutOpen(false)
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
