"use client"

import { useState } from "react"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger, ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Pause, CurrencyDollar, Warning, CheckCircle, Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Hold = {
  hold_id: string
  wallet_id: string
  agent_id: string
  amount: string
  currency: string
  merchant: string
  description: string
  status: string
  created_at: string
  expires_at: string
}

const statusConfig: Record<string, { variant: "success" | "warning" | "secondary" | "default"; label: string }> = {
  active: { variant: "success", label: "Active" },
  expiring: { variant: "warning", label: "Expiring" },
  released: { variant: "secondary", label: "Released" },
  captured: { variant: "default", label: "Captured" },
}

export default function HoldsPage() {
  const { data: remoteHolds, loading, refetch } = useSardis<Hold[]>("api/v2/holds")
  const holds = remoteHolds ?? []

  const activeCount = holds.filter(h => h.status === "active").length
  const releasedCount = holds.filter(h => h.status === "released").length
  const totalHeld = holds.filter(h => h.status === "active" || h.status === "expiring")
    .reduce((sum, h) => sum + (parseFloat(h.amount) || 0), 0)

  const stats = [
    { label: "Active Holds", value: String(activeCount), icon: Pause },
    { label: "Total Held", value: `$${totalHeld.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, icon: CurrencyDollar },
    { label: "Expiring", value: String(holds.filter(h => h.status === "expiring").length), icon: Warning },
    { label: "Released", value: String(releasedCount), icon: CheckCircle },
  ]

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
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "—" : s.value}</p>
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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : holds.length === 0 ? (
            <EmptyState
              icon={Pause}
              title="No holds"
              description="Payment holds will appear here when agents create pre-authorizations"
            />
          ) : (
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
                const st = statusConfig[hold.status] || { variant: "secondary" as const, label: hold.status }
                return (
                  <ContextMenu key={hold.hold_id}>
                    <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-mono text-xs">{hold.hold_id}</TableCell>
                        <TableCell className="font-medium">{hold.description || "—"}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.agent_id}</TableCell>
                        <TableCell className="text-right tabular-nums font-medium">${parseFloat(hold.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.merchant || "—"}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.created_at}</TableCell>
                        <TableCell className="text-muted-foreground">{hold.expires_at}</TableCell>
                        <TableCell>
                          <Badge variant={st.variant}>{st.label}</Badge>
                        </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(hold.hold_id); toast.success("Copied to clipboard") }}>
                        Copy ID
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem disabled={hold.status === "released" || hold.status === "captured"} onClick={async () => {
                        try {
                          const res = await fetch(`/api/sardis/api/v2/holds/${hold.hold_id}/release`, { method: "POST" })
                          if (!res.ok) throw new Error("Failed")
                          toast.success("Hold released")
                          refetch()
                        } catch {
                          toast.error("Failed to release hold")
                        }
                      }}>
                        Release
                      </ContextMenuItem>
                      <ContextMenuItem disabled={hold.status === "released" || hold.status === "captured"} onClick={async () => {
                        try {
                          const res = await fetch(`/api/sardis/api/v2/holds/${hold.hold_id}/capture`, { method: "POST" })
                          if (!res.ok) throw new Error("Failed")
                          toast.success("Hold captured")
                          refetch()
                        } catch {
                          toast.error("Failed to capture hold")
                        }
                      }}>
                        Capture
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
    </div>
  )
}
