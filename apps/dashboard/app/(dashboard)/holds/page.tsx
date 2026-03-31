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
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Pause,
  CurrencyDollar,
  Warning,
  CheckCircle,
} from "@phosphor-icons/react"
import { toast } from "sonner"

type Hold = {
  id: string
  description: string
  agent: string
  amount: string
  merchant: string
  created: string
  expires: string
  status: "active" | "expiring" | "released" | "captured"
}

const initialHolds: Hold[] = [
  { id: "HLD-001", description: "Cloud hosting pre-auth", agent: "Payment Router Alpha", amount: "$2,400", merchant: "AWS", created: "Mar 25, 2026", expires: "Mar 27, 2026", status: "expiring" },
  { id: "HLD-002", description: "SaaS subscription hold", agent: "Subscription Manager", amount: "$890", merchant: "Notion", created: "Mar 24, 2026", expires: "Mar 31, 2026", status: "active" },
  { id: "HLD-003", description: "API usage deposit", agent: "Expense Tracker v2", amount: "$1,500", merchant: "OpenAI", created: "Mar 23, 2026", expires: "Apr 01, 2026", status: "active" },
  { id: "HLD-004", description: "Hardware procurement", agent: "Vendor Pay Agent", amount: "$3,200", merchant: "Dell Technologies", created: "Mar 22, 2026", expires: "Mar 27, 2026", status: "expiring" },
  { id: "HLD-005", description: "Conference registration", agent: "Expense Tracker v2", amount: "$750", merchant: "Eventbrite", created: "Mar 21, 2026", expires: "Apr 05, 2026", status: "active" },
  { id: "HLD-006", description: "Software license hold", agent: "Payment Router Alpha", amount: "$1,200", merchant: "JetBrains", created: "Mar 20, 2026", expires: "Mar 26, 2026", status: "released" },
  { id: "HLD-007", description: "Office supplies pre-auth", agent: "Vendor Pay Agent", amount: "$460", merchant: "Staples", created: "Mar 19, 2026", expires: "Mar 25, 2026", status: "released" },
  { id: "HLD-008", description: "Cloud storage upgrade", agent: "Treasury Sweep Bot", amount: "$2,050", merchant: "Google Cloud", created: "Mar 26, 2026", expires: "Apr 02, 2026", status: "active" },
]

const stats = [
  { label: "Active Holds", value: "7", icon: Pause },
  { label: "Total Held", value: "$12,450", icon: CurrencyDollar },
  { label: "Expiring Today", value: "2", icon: Warning },
  { label: "Released Today", value: "5", icon: CheckCircle },
]

const statusConfig: Record<Hold["status"], { variant: "success" | "warning" | "secondary" | "default"; label: string }> = {
  active: { variant: "success", label: "Active" },
  expiring: { variant: "warning", label: "Expiring" },
  released: { variant: "secondary", label: "Released" },
  captured: { variant: "default", label: "Captured" },
}

export default function HoldsPage() {
  const [holds, setHolds] = useState<Hold[]>(initialHolds)

  function updateHoldStatus(id: string, status: "released" | "captured") {
    setHolds((prev) =>
      prev.map((h) => (h.id === id ? { ...h, status } : h))
    )
    toast.success(`Hold ${id} ${status}`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Holds</h1>
        <p className="text-sm text-muted-foreground">Active holds and pre-authorizations across agents</p>
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
          <CardTitle>All Holds</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Hold ID</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Merchant</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {holds.map((hold) => {
                const st = statusConfig[hold.status]
                return (
                  <ContextMenu key={hold.id}>
                    <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-mono text-xs">{hold.id}</TableCell>
                        <TableCell className="font-medium">{hold.description}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.agent}</TableCell>
                        <TableCell className="text-right tabular-nums font-medium">{hold.amount}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.merchant}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.created}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.expires}</TableCell>
                        <TableCell>
                          <Badge variant={st.variant}>{st.label}</Badge>
                        </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(hold.id); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem
                        onClick={() => updateHoldStatus(hold.id, "released")}
                        disabled={hold.status === "released" || hold.status === "captured"}
                      >
                        Release
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => updateHoldStatus(hold.id, "captured")}
                        disabled={hold.status === "released" || hold.status === "captured"}
                      >
                        Capture
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
