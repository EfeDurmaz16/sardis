"use client"

import React, { useState, useMemo } from "react"
import { format } from "date-fns"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import {
  CurrencyDollar, ArrowsLeftRight, ChartBar, CheckCircle,
  CalendarBlank, ArrowUp, ArrowDown, ArrowsDownUp, Spinner,
} from "@phosphor-icons/react"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Transaction = {
  tx_id: string
  from_wallet: string
  to_wallet: string
  amount: string
  currency: string
  chain: string | null
  chain_tx_hash: string | null
  audit_anchor: string | null
  created_at: string
  status: string
}

const statusConfig: Record<string, { color: string; label: string }> = {
  confirmed: { color: "bg-success", label: "Confirmed" },
  completed: { color: "bg-success", label: "Completed" },
  pending: { color: "bg-warning", label: "Pending" },
  failed: { color: "bg-destructive", label: "Failed" },
  blocked: { color: "bg-destructive", label: "Blocked" },
}

function formatUsd(value: string): string {
  const num = parseFloat(value)
  if (!Number.isFinite(num)) return "$0.00"
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function shortenId(id: string): string {
  if (id.length <= 14) return id
  return `${id.slice(0, 6)}...${id.slice(-4)}`
}

const itemsPerPage = 10

export default function TransactionsPage() {
  const { data: transactions, loading, error } = useSardis<Transaction[]>("api/v2/ledger/recent?limit=200")
  const txList = transactions ?? []

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

  const sorted = useMemo(() => {
    const list = [...txList]
    if (!sortKey) return list
    return list.sort((a, b) => {
      let cmp = 0
      if (sortKey === "amount") {
        cmp = parseFloat(a.amount) - parseFloat(b.amount)
      } else if (sortKey === "created_at") {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      } else {
        const av = (a as Record<string, unknown>)[sortKey] as string ?? ""
        const bv = (b as Record<string, unknown>)[sortKey] as string ?? ""
        cmp = av.localeCompare(bv)
      }
      return sortDir === "asc" ? cmp : -cmp
    })
  }, [txList, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / itemsPerPage))
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage
    return sorted.slice(start, start + itemsPerPage)
  }, [sorted, currentPage])

  const startItem = sorted.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0
  const endItem = Math.min(currentPage * itemsPerPage, sorted.length)

  // Compute summary stats from real data
  const totalVolume = txList.reduce((sum, tx) => sum + (parseFloat(tx.amount) || 0), 0)
  const successCount = txList.filter(tx => tx.status === "confirmed" || tx.status === "completed").length
  const successRate = txList.length > 0 ? ((successCount / txList.length) * 100).toFixed(1) : "0.0"
  const avgAmount = txList.length > 0 ? totalVolume / txList.length : 0

  const stats = [
    { label: "Total Volume", value: formatUsd(String(totalVolume)), icon: CurrencyDollar },
    { label: "Transactions", value: txList.length.toLocaleString(), icon: ArrowsLeftRight },
    { label: "Avg Amount", value: formatUsd(String(avgAmount)), icon: ChartBar },
    { label: "Success Rate", value: `${successRate}%`, icon: CheckCircle },
  ]

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
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : s.value}</p>
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
            <Input placeholder="Search transactions..." className="w-full sm:w-48" />
          </div>
        </CardContent>
        <CardContent className="px-0 pt-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : txList.length === 0 ? (
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
                  onClick={() => toggleSort("created_at")}
                >
                  <span className="flex items-center gap-1">
                    Timestamp
                    {sortKey === "created_at" ? (
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
                const st = statusConfig[tx.status] || { color: "bg-muted", label: tx.status }
                return (
                  <React.Fragment key={tx.tx_id}>
                  <ContextMenu>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4">
                        <HoverCard>
                          <HoverCardTrigger>
                            <Badge variant="outline" className="font-mono text-xs cursor-pointer">{shortenId(tx.tx_id)}</Badge>
                          </HoverCardTrigger>
                          <HoverCardContent className="w-64">
                            <div className="space-y-1.5">
                              <p className="text-xs font-mono text-muted-foreground">{tx.tx_id}</p>
                              <div className="flex items-center gap-1.5">
                                <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                                <span className="text-sm">{st.label}</span>
                              </div>
                              <div className="flex justify-between text-xs text-muted-foreground">
                                <span>{tx.chain || "—"}</span>
                                <span className="font-medium text-foreground">{formatUsd(tx.amount)}</span>
                              </div>
                              <p className="text-xs text-muted-foreground">{tx.created_at}</p>
                            </div>
                          </HoverCardContent>
                        </HoverCard>
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-[180px] truncate">{tx.from_wallet}</TableCell>
                      <TableCell className="text-muted-foreground max-w-[180px] truncate">{tx.to_wallet}</TableCell>
                      <TableCell className="text-right tabular-nums font-medium">{formatUsd(tx.amount)}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{tx.chain || "—"}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                          {st.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{tx.created_at}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.tx_id); toast.success("Copied to clipboard") }}>
                        Copy TX ID
                      </ContextMenuItem>
                      {tx.chain_tx_hash && (
                        <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.chain_tx_hash!); toast.success("Copied to clipboard") }}>
                          Copy Hash
                        </ContextMenuItem>
                      )}
                      <ContextMenuSeparator />
                      {tx.chain_tx_hash && (
                        <ContextMenuItem onClick={() => window.open(`https://basescan.org/tx/${tx.chain_tx_hash}`, "_blank")}>
                          View on Explorer
                        </ContextMenuItem>
                      )}
                      <ContextMenuItem onClick={() => setExpandedTx(prev => prev === tx.tx_id ? null : tx.tx_id)}>
                        {expandedTx === tx.tx_id ? "Collapse Details" : "Expand Details"}
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                  {expandedTx === tx.tx_id && (
                    <TableRow className="bg-muted/30">
                      <TableCell colSpan={7} className="pl-4">
                        <div className="grid grid-cols-2 gap-x-8 gap-y-2 py-2 text-sm sm:grid-cols-4">
                          <div>
                            <p className="text-xs text-muted-foreground">Transaction ID</p>
                            <p className="font-mono text-xs">{tx.tx_id}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Currency</p>
                            <p>{tx.currency}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">From</p>
                            <p className="truncate">{tx.from_wallet}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">To</p>
                            <p className="truncate">{tx.to_wallet}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Amount</p>
                            <p className="font-medium">{formatUsd(tx.amount)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Chain</p>
                            <p>{tx.chain || "—"}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Status</p>
                            <p>{st.label}</p>
                          </div>
                          <div>
                            <p className="text-xs text-muted-foreground">Audit Anchor</p>
                            <p className="font-mono text-xs truncate">{tx.audit_anchor || "—"}</p>
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
        {txList.length > itemsPerPage && (
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-t px-4 py-3">
            <p className="text-sm text-muted-foreground">
              Showing {startItem}-{endItem} of {sorted.length} transactions
            </p>
            <div className="flex items-center gap-1">
              <Button variant="outline" size="sm" disabled={currentPage === 1} onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}>
                Previous
              </Button>
              {getPageNumbers().map((page, i) =>
                page === "..." ? (
                  <span key={`ellipsis-${i}`} className="px-1 text-sm text-muted-foreground">...</span>
                ) : (
                  <Button key={page} variant={currentPage === page ? "default" : "outline"} size="sm" onClick={() => setCurrentPage(page)}>
                    {page}
                  </Button>
                )
              )}
              <Button variant="outline" size="sm" disabled={currentPage === totalPages} onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}>
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
