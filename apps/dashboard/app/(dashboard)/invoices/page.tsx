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
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"

type Invoice = {
  id: string
  merchant: string
  amount: string
  issueDate: string
  dueDate: string
  status: "outstanding" | "paid" | "overdue"
}

const initialInvoices: Invoice[] = [
  { id: "INV-1042", merchant: "AWS", amount: "$8,400", issueDate: "Mar 01, 2026", dueDate: "Mar 31, 2026", status: "outstanding" },
  { id: "INV-1041", merchant: "Google Cloud", amount: "$5,200", issueDate: "Mar 01, 2026", dueDate: "Mar 31, 2026", status: "outstanding" },
  { id: "INV-1040", merchant: "Vercel", amount: "$1,890", issueDate: "Feb 28, 2026", dueDate: "Mar 28, 2026", status: "outstanding" },
  { id: "INV-1039", merchant: "OpenAI", amount: "$12,600", issueDate: "Feb 15, 2026", dueDate: "Mar 15, 2026", status: "overdue" },
  { id: "INV-1038", merchant: "Datadog", amount: "$3,400", issueDate: "Feb 10, 2026", dueDate: "Mar 10, 2026", status: "overdue" },
  { id: "INV-1037", merchant: "Notion", amount: "$890", issueDate: "Feb 01, 2026", dueDate: "Mar 01, 2026", status: "paid" },
  { id: "INV-1036", merchant: "JetBrains", amount: "$2,100", issueDate: "Feb 01, 2026", dueDate: "Mar 01, 2026", status: "paid" },
  { id: "INV-1035", merchant: "Figma", amount: "$1,440", issueDate: "Jan 15, 2026", dueDate: "Feb 15, 2026", status: "paid" },
  { id: "INV-1034", merchant: "Slack", amount: "$760", issueDate: "Jan 10, 2026", dueDate: "Feb 10, 2026", status: "paid" },
  { id: "INV-1033", merchant: "Linear", amount: "$2,510", issueDate: "Feb 05, 2026", dueDate: "Mar 05, 2026", status: "overdue" },
]

const stats = [
  { label: "Total Invoices", value: "156", icon: FileText },
  { label: "Outstanding", value: "$23,400", icon: CurrencyDollar },
  { label: "Paid This Month", value: "$67,200", icon: CheckCircle },
  { label: "Overdue", value: "3", icon: Warning },
]

const statusConfig: Record<Invoice["status"], { variant: "warning" | "success" | "destructive"; label: string }> = {
  outstanding: { variant: "warning", label: "Outstanding" },
  paid: { variant: "success", label: "Paid" },
  overdue: { variant: "destructive", label: "Overdue" },
}

export default function InvoicesPage() {
  const [tab, setTab] = useState("all")
  const [invoices, setInvoices] = useState<Invoice[]>(initialInvoices)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null)

  const filtered = tab === "all"
    ? invoices
    : invoices.filter((inv) => inv.status === tab)

  function handleView(inv: Invoice) {
    setSelectedInvoice(inv)
    setSheetOpen(true)
  }

  function handleMarkPaid(id: string) {
    setInvoices((prev) => prev.map((inv) =>
      inv.id === id ? { ...inv, status: "paid" as const } : inv
    ))
    toast.success(`Invoice ${id} marked as paid`)
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
          {filtered.length === 0 ? (
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
                const st = statusConfig[inv.status]
                return (
                  <ContextMenu key={inv.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-mono text-xs">{inv.id}</TableCell>
                        <TableCell className="font-medium">{inv.merchant}</TableCell>
                        <TableCell className="text-right tabular-nums font-medium">{inv.amount}</TableCell>
                        <TableCell className="text-muted-foreground">{inv.issueDate}</TableCell>
                        <TableCell className="text-muted-foreground">{inv.dueDate}</TableCell>
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
                  <span>{selectedInvoice.issueDate}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Due Date</span>
                  <span>{selectedInvoice.dueDate}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={statusConfig[selectedInvoice.status].variant}>{statusConfig[selectedInvoice.status].label}</Badge>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Payment Method</span>
                  <span>Wire Transfer</span>
                </div>
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
              <Button onClick={() => { handleMarkPaid(selectedInvoice.id); setSelectedInvoice({ ...selectedInvoice, status: "paid" }); toast.success(`Invoice ${selectedInvoice.id} marked as paid`) }}>Mark as Paid</Button>
            )}
            <SheetClose render={<Button variant="outline" />}>Close</SheetClose>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
