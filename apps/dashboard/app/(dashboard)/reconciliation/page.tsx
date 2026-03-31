"use client"

import { useState } from "react"
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
import { toast } from "sonner"
import {
  ArrowsClockwise,
  CheckCircle,
  Warning,
  XCircle,
} from "@phosphor-icons/react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"

type Discrepancy = {
  txId: string
  expectedAmount: string
  actualAmount: string
  difference: string
  chain: string
  status: "unresolved" | "investigating" | "resolved" | "reconciled"
  detected: string
}

const initialDiscrepancies: Discrepancy[] = [
  { txId: "TX-90821", expectedAmount: "$1,200.00", actualAmount: "$1,187.50", difference: "-$12.50", chain: "Ethereum", status: "unresolved", detected: "Mar 27, 2026" },
  { txId: "TX-90734", expectedAmount: "$450.00", actualAmount: "$450.89", difference: "+$0.89", chain: "Polygon", status: "investigating", detected: "Mar 26, 2026" },
  { txId: "TX-90698", expectedAmount: "$3,800.00", actualAmount: "$3,762.00", difference: "-$38.00", chain: "Arbitrum", status: "unresolved", detected: "Mar 26, 2026" },
  { txId: "TX-90612", expectedAmount: "$890.00", actualAmount: "$890.00", difference: "$0.00", chain: "Ethereum", status: "resolved", detected: "Mar 25, 2026" },
  { txId: "TX-90587", expectedAmount: "$2,100.00", actualAmount: "$2,094.75", difference: "-$5.25", chain: "Optimism", status: "investigating", detected: "Mar 25, 2026" },
  { txId: "TX-90543", expectedAmount: "$670.00", actualAmount: "$685.00", difference: "+$15.00", chain: "Polygon", status: "unresolved", detected: "Mar 24, 2026" },
]

const stats = [
  { label: "Total Transactions", value: "1,247", icon: ArrowsClockwise },
  { label: "Matched", value: "1,198", icon: CheckCircle },
  { label: "Unmatched", value: "49", icon: Warning },
  { label: "Discrepancies", value: "12", icon: XCircle },
]

const pieData = [
  { name: "Matched", value: 1198, color: "#10b981" },
  { name: "Unmatched", value: 49, color: "#f59e0b" },
  { name: "Discrepancy", value: 12, color: "#ef4444" },
]

const statusConfig: Record<Discrepancy["status"], { variant: "destructive" | "warning" | "success" | "info"; label: string }> = {
  unresolved: { variant: "destructive", label: "Unresolved" },
  investigating: { variant: "warning", label: "Investigating" },
  resolved: { variant: "success", label: "Resolved" },
  reconciled: { variant: "info", label: "Reconciled" },
}

export default function ReconciliationPage() {
  const [discrepancies, setDiscrepancies] = useState<Discrepancy[]>(initialDiscrepancies)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<Discrepancy | null>(null)

  function handleView(d: Discrepancy) {
    setSelectedItem(d)
    setSheetOpen(true)
  }

  function handleForceReconcile(txId: string) {
    setDiscrepancies((prev) => prev.map((d) =>
      d.txId === txId ? { ...d, status: "reconciled" as const } : d
    ))
    toast.success(`${txId} force reconciled`)
  }

  function renderDiscrepancyTable(items: Discrepancy[], showChain: boolean, showDetected: boolean) {
    return (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="pl-4">TX ID</TableHead>
            <TableHead className="text-right">Expected{showChain ? " Amount" : ""}</TableHead>
            <TableHead className="text-right">Actual{showChain ? " Amount" : ""}</TableHead>
            <TableHead className="text-right">Diff{showChain ? "erence" : ""}</TableHead>
            {showChain && <TableHead>Chain</TableHead>}
            <TableHead>Status</TableHead>
            {showDetected && <TableHead>Detected</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((d) => {
            const st = statusConfig[d.status]
            return (
              <ContextMenu key={d.txId}>
                <ContextMenuTrigger render={<TableRow />}>
                    <TableCell className="pl-4 font-mono text-xs">{d.txId}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{d.expectedAmount}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{d.actualAmount}</TableCell>
                    <TableCell className="text-right tabular-nums font-mono text-xs font-medium">{d.difference}</TableCell>
                    {showChain && (
                      <TableCell>
                        <Badge variant="outline">{d.chain}</Badge>
                      </TableCell>
                    )}
                    <TableCell>
                      <Badge variant={st.variant}>{st.label}</Badge>
                    </TableCell>
                    {showDetected && <TableCell className="text-muted-foreground">{d.detected}</TableCell>}
                </ContextMenuTrigger>
                <ContextMenuContent>
                  <ContextMenuItem onClick={() => { navigator.clipboard.writeText(d.txId); toast.success("Copied to clipboard") }}>
                    Copy ID
                  </ContextMenuItem>
                  <ContextMenuSeparator />
                  <ContextMenuItem onClick={() => handleView(d)}>
                    View
                  </ContextMenuItem>
                  <ContextMenuItem onClick={() => handleForceReconcile(d.txId)}>
                    Force Reconcile
                  </ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
            )
          })}
        </TableBody>
      </Table>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reconciliation</h1>
        <p className="text-sm text-muted-foreground">Transaction reconciliation and discrepancy tracking</p>
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Reconciliation Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(value: string) => (
                      <span className="text-xs text-muted-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Recent Discrepancies</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {renderDiscrepancyTable(discrepancies.slice(0, 5), false, false)}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>All Discrepancies</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {renderDiscrepancyTable(discrepancies, true, true)}
        </CardContent>
      </Card>

      {/* Reconciliation Detail Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{selectedItem?.txId}</SheetTitle>
            <SheetDescription>Discrepancy details</SheetDescription>
          </SheetHeader>
          {selectedItem && (
            <div className="flex-1 overflow-y-auto px-4 space-y-4">
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Transaction ID</span>
                  <span className="font-mono text-xs">{selectedItem.txId}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Chain</span>
                  <Badge variant="outline">{selectedItem.chain}</Badge>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Expected Amount</span>
                  <span className="tabular-nums font-medium">{selectedItem.expectedAmount}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Actual Amount</span>
                  <span className="tabular-nums font-medium">{selectedItem.actualAmount}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Difference</span>
                  <span className="tabular-nums font-mono text-xs font-medium">{selectedItem.difference}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={statusConfig[selectedItem.status].variant}>{statusConfig[selectedItem.status].label}</Badge>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Detected</span>
                  <span>{selectedItem.detected}</span>
                </div>
                <Separator />
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Reconciliation Method</span>
                  <span>Automated Matching</span>
                </div>
              </div>
            </div>
          )}
          <SheetFooter>
            {selectedItem && selectedItem.status !== "reconciled" && selectedItem.status !== "resolved" && (
              <Button onClick={() => { handleForceReconcile(selectedItem.txId); setSelectedItem({ ...selectedItem, status: "reconciled" }) }}>Force Reconcile</Button>
            )}
            <SheetClose render={<Button variant="outline" />}>Close</SheetClose>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
