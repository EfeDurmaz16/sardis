"use client"

import React, { useState, useMemo } from "react"
import { format } from "date-fns"
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
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  CurrencyDollar,
  ArrowsLeftRight,
  ChartBar,
  CheckCircle,
  CalendarBlank,
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
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"

type Transaction = {
  id: string
  type: "transfer" | "payment" | "swap" | "deposit" | "withdrawal"
  from: string
  to: string
  amount: string
  chain: string
  status: "confirmed" | "pending" | "failed"
  timestamp: string
}

const transactions: Transaction[] = [
  { id: "0x8f3a...d21e", type: "transfer", from: "Payment Router Alpha", to: "Treasury Sweep Bot", amount: "$4,200.00", chain: "Ethereum", status: "confirmed", timestamp: "Mar 27, 2026 14:32" },
  { id: "0x1b7c...e49f", type: "payment", from: "Vendor Pay Agent", to: "Acme Corp", amount: "$1,850.00", chain: "Polygon", status: "confirmed", timestamp: "Mar 27, 2026 14:28" },
  { id: "0x5d2e...a83b", type: "swap", from: "Gas Optimizer v3", to: "Uniswap V3", amount: "$320.50", chain: "Arbitrum", status: "confirmed", timestamp: "Mar 27, 2026 14:15" },
  { id: "0x9e4f...c17d", type: "deposit", from: "External Wallet", to: "Cross-chain Bridge", amount: "$15,000.00", chain: "Ethereum", status: "pending", timestamp: "Mar 27, 2026 14:08" },
  { id: "0x2a6b...f53e", type: "payment", from: "Expense Tracker v2", to: "AWS Services", amount: "$2,490.00", chain: "Polygon", status: "confirmed", timestamp: "Mar 27, 2026 13:55" },
  { id: "0x7c1d...b28a", type: "transfer", from: "Payroll Distributor", to: "Employee Pool", amount: "$28,400.00", chain: "Ethereum", status: "confirmed", timestamp: "Mar 27, 2026 13:42" },
  { id: "0x3f8e...d94c", type: "withdrawal", from: "Yield Harvester", to: "Cold Storage", amount: "$8,750.00", chain: "Optimism", status: "confirmed", timestamp: "Mar 27, 2026 13:30" },
  { id: "0x6b2a...e71f", type: "swap", from: "Treasury Sweep Bot", to: "Curve Finance", amount: "$12,300.00", chain: "Ethereum", status: "confirmed", timestamp: "Mar 27, 2026 13:18" },
  { id: "0x4e9c...a36d", type: "payment", from: "Invoice Settler", to: "DigitalOcean", amount: "$680.00", chain: "Polygon", status: "failed", timestamp: "Mar 27, 2026 13:05" },
  { id: "0xd1f5...c82b", type: "transfer", from: "Subscription Manager", to: "SaaS Vendor Pool", amount: "$3,200.00", chain: "Polygon", status: "confirmed", timestamp: "Mar 27, 2026 12:52" },
  { id: "0xa3e7...f19d", type: "deposit", from: "External Wallet", to: "Payment Router Alpha", amount: "$50,000.00", chain: "Ethereum", status: "confirmed", timestamp: "Mar 27, 2026 12:40" },
  { id: "0x8d4b...e26a", type: "payment", from: "Vendor Pay Agent", to: "Cloudflare Inc", amount: "$1,120.00", chain: "Arbitrum", status: "confirmed", timestamp: "Mar 27, 2026 12:28" },
  { id: "0xc2f9...b47e", type: "swap", from: "Gas Optimizer v3", to: "1inch", amount: "$540.00", chain: "Arbitrum", status: "pending", timestamp: "Mar 27, 2026 12:15" },
  { id: "0x5a1e...d83c", type: "withdrawal", from: "Cross-chain Bridge", to: "Hot Wallet", amount: "$6,890.00", chain: "Optimism", status: "confirmed", timestamp: "Mar 27, 2026 12:02" },
  { id: "0x7f3d...a95b", type: "transfer", from: "Payroll Distributor", to: "Contractor Pool", amount: "$12,150.00", chain: "Ethereum", status: "confirmed", timestamp: "Mar 27, 2026 11:48" },
]

const stats = [
  { label: "Today's Volume", value: "$148,392", icon: CurrencyDollar },
  { label: "Transactions", value: "1,247", icon: ArrowsLeftRight },
  { label: "Avg Amount", value: "$119", icon: ChartBar },
  { label: "Success Rate", value: "98.2%", icon: CheckCircle },
]

const typeConfig: Record<Transaction["type"], { color: string; label: string }> = {
  transfer: { color: "bg-info", label: "Transfer" },
  payment: { color: "bg-success", label: "Payment" },
  swap: { color: "bg-violet-500", label: "Swap" },
  deposit: { color: "bg-warning", label: "Deposit" },
  withdrawal: { color: "bg-orange-500", label: "Withdrawal" },
}

const statusConfig: Record<Transaction["status"], { color: string; label: string }> = {
  confirmed: { color: "bg-success", label: "Confirmed" },
  pending: { color: "bg-warning", label: "Pending" },
  failed: { color: "bg-destructive", label: "Failed" },
}

function parseCurrency(val: string): number {
  return parseFloat(val.replace(/[$,]/g, "")) || 0
}

const itemsPerPage = 10

export default function TransactionsPage() {
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined)
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [expandedTx, setExpandedTx] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
    setCurrentPage(1)
  }

  const sorted = [...transactions].sort((a, b) => {
    if (!sortKey) return 0
    let cmp = 0
    if (sortKey === "amount") {
      cmp = parseCurrency(a.amount) - parseCurrency(b.amount)
    } else if (sortKey === "timestamp") {
      cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    } else {
      const av = a[sortKey as keyof Transaction] as string
      const bv = b[sortKey as keyof Transaction] as string
      cmp = av.localeCompare(bv)
    }
    return sortDir === "asc" ? cmp : -cmp
  })

  const totalPages = Math.ceil(sorted.length / itemsPerPage)
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return sorted.slice(start, start + itemsPerPage)
  }, [sorted, currentPage])

  const startItem = (currentPage - 1) * itemsPerPage + 1
  const endItem = Math.min(currentPage * itemsPerPage, sorted.length)

  function getPageNumbers(): (number | "...")[] {
    const pages: (number | "...")[] = []
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      pages.push(1)
      if (currentPage > 3) pages.push("...")
      const start = Math.max(2, currentPage - 1)
      const end = Math.min(totalPages - 1, currentPage + 1)
      for (let i = start; i <= end; i++) pages.push(i)
      if (currentPage < totalPages - 2) pages.push("...")
      pages.push(totalPages)
    }
    return pages
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
        <p className="text-sm text-muted-foreground">View and track all transaction activity</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
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
          <CardTitle>Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2 py-4">
            <Popover>
              <PopoverTrigger
                className={cn(
                  "inline-flex items-center justify-start gap-1.5 rounded-md border bg-card px-3 h-8 w-full sm:w-36 text-xs font-normal transition-colors hover:bg-accent",
                  !dateFrom && "text-muted-foreground"
                )}
              >
                <CalendarBlank className="h-3.5 w-3.5" />
                {dateFrom ? format(dateFrom, "MMM dd, yyyy") : "From date"}
              </PopoverTrigger>
              <PopoverContent className="w-auto p-2" align="start">
                <Calendar mode="single" selected={dateFrom} onSelect={setDateFrom} />
              </PopoverContent>
            </Popover>
            <Popover>
              <PopoverTrigger
                className={cn(
                  "inline-flex items-center justify-start gap-1.5 rounded-md border bg-card px-3 h-8 w-full sm:w-36 text-xs font-normal transition-colors hover:bg-accent",
                  !dateTo && "text-muted-foreground"
                )}
              >
                <CalendarBlank className="h-3.5 w-3.5" />
                {dateTo ? format(dateTo, "MMM dd, yyyy") : "To date"}
              </PopoverTrigger>
              <PopoverContent className="w-auto p-2" align="start">
                <Calendar mode="single" selected={dateTo} onSelect={setDateTo} />
              </PopoverContent>
            </Popover>
            <Select items={{ "all-types": "All Types", transfer: "Transfer", payment: "Payment", swap: "Swap", deposit: "Deposit", withdrawal: "Withdrawal" }}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all-types">All Types</SelectItem>
                <SelectItem value="transfer">Transfer</SelectItem>
                <SelectItem value="payment">Payment</SelectItem>
                <SelectItem value="swap">Swap</SelectItem>
                <SelectItem value="deposit">Deposit</SelectItem>
                <SelectItem value="withdrawal">Withdrawal</SelectItem>
              </SelectContent>
            </Select>
            <Select items={{ "all-chains": "All Chains", ethereum: "Ethereum", polygon: "Polygon", arbitrum: "Arbitrum", optimism: "Optimism" }}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue placeholder="All Chains" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all-chains">All Chains</SelectItem>
                <SelectItem value="ethereum">Ethereum</SelectItem>
                <SelectItem value="polygon">Polygon</SelectItem>
                <SelectItem value="arbitrum">Arbitrum</SelectItem>
                <SelectItem value="optimism">Optimism</SelectItem>
              </SelectContent>
            </Select>
            <Select items={{ "all-statuses": "All Statuses", confirmed: "Confirmed", pending: "Pending", failed: "Failed" }}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all-statuses">All Statuses</SelectItem>
                <SelectItem value="confirmed">Confirmed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
            <Input placeholder="Search transactions..." className="w-full sm:w-48" />
          </div>
        </CardContent>
        <CardContent className="px-0 pt-0">
          {transactions.length === 0 ? (
            <EmptyState
              icon={ArrowsLeftRight}
              title="No transactions"
              description="Transactions will appear here once your agents start making payments"
            />
          ) : (
          <div className="overflow-x-auto -mx-4 sm:mx-0">
            <Table className="min-w-[800px]">
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">TX ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>From</TableHead>
                <TableHead>To</TableHead>
                <TableHead
                  className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("amount")}
                >
                  <span className="flex items-center justify-end gap-1">
                    Amount
                    {sortKey === "amount" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("chain")}
                >
                  <span className="flex items-center gap-1">
                    Chain
                    {sortKey === "chain" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("status")}
                >
                  <span className="flex items-center gap-1">
                    Status
                    {sortKey === "status" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
                <TableHead
                  className="cursor-pointer select-none hover:text-foreground transition-colors"
                  onClick={() => toggleSort("timestamp")}
                >
                  <span className="flex items-center gap-1">
                    Timestamp
                    {sortKey === "timestamp" ? (
                      sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                    ) : (
                      <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                    )}
                  </span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.map((tx) => {
                const tp = typeConfig[tx.type]
                const st = statusConfig[tx.status]
                return (
                  <React.Fragment key={tx.id}>
                  <ContextMenu>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4">
                        <HoverCard>
                          <HoverCardTrigger>
                            <Badge variant="outline" className="font-mono text-xs cursor-pointer">{tx.id}</Badge>
                          </HoverCardTrigger>
                          <HoverCardContent className="w-64">
                            <div className="space-y-1.5">
                              <p className="text-xs font-mono text-muted-foreground">{tx.id}</p>
                              <div className="flex items-center gap-1.5">
                                <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                                <span className="text-sm">{st.label}</span>
                              </div>
                              <div className="flex justify-between text-xs text-muted-foreground">
                                <span>{tx.chain}</span>
                                <span className="font-medium text-foreground">{tx.amount}</span>
                              </div>
                              <p className="text-xs text-muted-foreground">{tx.timestamp}</p>
                            </div>
                          </HoverCardContent>
                        </HoverCard>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${tp.color}`} />
                          {tp.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-[180px] truncate">{tx.from}</TableCell>
                      <TableCell className="text-muted-foreground max-w-[180px] truncate">{tx.to}</TableCell>
                      <TableCell className="text-right tabular-nums font-medium">{tx.amount}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{tx.chain}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{tx.timestamp}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.id); toast.success("Copied to clipboard") }}>
                        Copy TX ID
                      </ContextMenuItem>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.id); toast.success("Copied to clipboard") }}>
                        Copy Hash
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onClick={() => window.open(`https://etherscan.io/tx/${tx.id}`, "_blank")}>
                        View on Explorer
                      </ContextMenuItem>
                      <ContextMenuItem onClick={() => setExpandedTx(prev => prev === tx.id ? null : tx.id)}>
                        {expandedTx === tx.id ? "Collapse Details" : "Expand Details"}
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                  {expandedTx === tx.id && (
                    <TableRow className="bg-muted/30">
                      <TableCell colSpan={8} className="pl-4">
                        <div className="grid grid-cols-2 gap-x-8 gap-y-2 py-2 text-sm sm:grid-cols-4">
                          <div>
                            <p className="text-xs text-muted-foreground">Transaction ID</p>
                            <p className="font-mono text-xs">{tx.id}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Type</p>
                            <p>{typeConfig[tx.type].label}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">From</p>
                            <p>{tx.from}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">To</p>
                            <p>{tx.to}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Amount</p>
                            <p className="font-medium">{tx.amount}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Chain</p>
                            <p>{tx.chain}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Status</p>
                            <p>{statusConfig[tx.status].label}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Timestamp</p>
                            <p>{tx.timestamp}</p>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  </React.Fragment>
                )
              })}
            </TableBody>
            </Table>
          </div>
          )}
        </CardContent>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-t px-4 py-3">
          <p className="text-sm text-muted-foreground">
            Showing {startItem}-{endItem} of {sorted.length} transactions
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </Button>
            {getPageNumbers().map((page, i) =>
              page === "..." ? (
                <span key={`ellipsis-${i}`} className="px-1 text-sm text-muted-foreground">...</span>
              ) : (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              )
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
