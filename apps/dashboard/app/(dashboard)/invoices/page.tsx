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
import { Separator } from "@/components/ui/separator"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
} from "@/components/ui/sheet"
import {
  FileText,
  CurrencyDollar,
  CheckCircle,
  Warning,
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardisList } from "@/hooks/use-sardis"

type Invoice = {
  id: string
  merchant: string
  amount: string
  issue_date: string
  due_date: string
  status: "outstanding" | "paid" | "overdue"
}

const statusConfig: Record<Invoice["status"], { variant: "warning" | "success" | "destructive"; label: string }> = {
  outstanding: { variant: "warning", label: "Outstanding" },
  paid: { variant: "success", label: "Paid" },
  overdue: { variant: "destructive", label: "Overdue" },
}

function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "$0"
  const amount = typeof value === "number" ? value : parseFloat(value.replace(/[^0-9.-]/g, ""))
  if (isNaN(amount)) return "$0"
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

function parseMoney(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = parseFloat(value.replace(/[^0-9.-]/g, ""))
  return isNaN(parsed) ? 0 : parsed
}

function formatDate(val: string | null): string {
  if (!val) return "—"
  const d = new Date(val)
  if (isNaN(d.getTime())) return val
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(d)
}

export default function InvoicesPage() {
  const { data: invoiceData, loading, refetch } = useSardisList<Invoice>("api/v2/invoices", "Invoices")
  const invoices = invoiceData ?? []

  const [tab, setTab] = useState("all")
  const [sheetOpen, setSheetOpen] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null)

  const stats = useMemo(() => {
    const total = invoices.length
    const outstanding = invoices.filter((i) => i.status === "outstanding")
    const paid = invoices.filter((i) => i.status === "paid")
    const overdue = invoices.filter((i) => i.status === "overdue")
    const outstandingTotal = outstanding.reduce((sum, i) => sum + parseMoney(i.amount), 0)
    const paidTotal = paid.reduce((sum, i) => sum + parseMoney(i.amount), 0)

    return [
      { label: "Total Invoices", value: String(total), icon: FileText },
      { label: "Outstanding", value: formatMoney(outstandingTotal), icon: CurrencyDollar },
      { label: "Paid This Month", value: formatMoney(paidTotal), icon: CheckCircle },
      { label: "Overdue", value: String(overdue.length), icon: Warning },
    ]
  }, [invoices])

  const filtered = tab === "all"
    ? invoices
    : invoices.filter((inv) => inv.status === tab)

  function handleView(inv: Invoice) {
    setSelectedInvoice(inv)
    setSheetOpen(true)
  }

  async function handleMarkPaid(id: string) {
    try {
      const res = await fetch(`/api/sardis/api/v2/invoices/${id}/mark-paid`, {
        method: "POST",
      })
      if (!res.ok) throw new Error("Failed")
      toast.success(`Invoice ${id} marked as paid`)
      refetch()
    } catch {
      toast.error("Failed to mark invoice as paid")
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Invoices</h1>
        <p className="text-sm text-muted-foreground">Manage and track invoices across merchants</p>
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
          <CardTitle>All Invoices</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="outstanding">Outstanding</TabsTrigger>
                <TabsTrigger value="paid">Paid</TabsTrigger>
                <TabsTrigger value="overdue">Overdue</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No invoices"
              description="Invoices will appear here when merchants request payments"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Invoice #</TableHead>
                <TableHead>Merchant</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Issue Date</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((inv) => {
                const st = statusConfig[inv.status] ?? { variant: "warning" as const, label: inv.status }
                return (
                  <ContextMenu key={inv.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-mono text-xs">{inv.id}</TableCell>
                        <TableCell className="font-medium">{inv.merchant}</TableCell>
                        <TableCell className="text-right tabular-nums font-medium">{inv.amount}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(inv.issue_date)}</TableCell>
                        <TableCell className="text-muted-foreground">{formatDate(inv.due_date)}</TableCell>
                        <TableCell>
                          <Badge variant={st.variant}>{st.label}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="xs" onClick={() => handleView(inv)}>View</Button>
                            {inv.status !== "paid" && (
                              <Button variant="outline" size="xs" onClick={() => handleMarkPaid(inv.id)}>Pay</Button>
                            )}
                          </div>
                        </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(inv.id); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onClick={() => handleView(inv)}>
                        View
                      </ContextMenuItem>
                      <ContextMenuItem onClick={() => handleMarkPaid(inv.id)}>
                        Mark Paid
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                )
              })}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      {/* Invoice Detail Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{selectedInvoice?.id}</SheetTitle>
            <SheetDescription>Invoice details for {selectedInvoice?.merchant}</SheetDescription>
          </SheetHeader>
          {selectedInvoice && (
            <div className="flex-1 overflow-y-auto px-4 space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Merchant</span>
                  <span className="font-medium">{selectedInvoice.merchant}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Amount</span>
                  <span className="font-medium tabular-nums">{selectedInvoice.amount}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Issue Date</span>
                  <span>{formatDate(selectedInvoice.issue_date)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Due Date</span>
                  <span>{formatDate(selectedInvoice.due_date)}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={statusConfig[selectedInvoice.status]?.variant ?? "warning"}>{statusConfig[selectedInvoice.status]?.label ?? selectedInvoice.status}</Badge>
                </div>
                <Separator />
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Reference</span>
                  <span className="font-mono text-xs">{selectedInvoice.id}-REF</span>
                </div>
              </div>
            </div>
          )}
          <SheetFooter>
            {selectedInvoice && selectedInvoice.status !== "paid" && (
              <Button onClick={async () => { await handleMarkPaid(selectedInvoice.id); setSelectedInvoice({ ...selectedInvoice, status: "paid" }) }}>Mark as Paid</Button>
            )}
            <SheetClose render={<Button variant="outline" />}>Close</SheetClose>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
