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
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu"
import {
  Lock,
  CheckCircle,
  Clock,
  ChartBar,
} from "@phosphor-icons/react"
import { toast } from "sonner"

type EvidenceItem = {
  id: string
  type: "Transaction Proof" | "Policy Log" | "Access Record"
  description: string
  relatedEntity: string
  hash: string
  created: string
  status: "Verified" | "Pending"
}

const evidenceItems: EvidenceItem[] = [
  { id: "EV-001847", type: "Transaction Proof", description: "Payment authorization for vendor invoice #4821", relatedEntity: "Payment Router Alpha", hash: "0x8a3f...7d2b", created: "2 min ago", status: "Verified" },
  { id: "EV-001846", type: "Policy Log", description: "Spending limit override approved by admin", relatedEntity: "Treasury Sweep Bot", hash: "0x5c1e...9f4a", created: "8 min ago", status: "Verified" },
  { id: "EV-001845", type: "Access Record", description: "API key rotation completed for production env", relatedEntity: "System Admin", hash: "0x2d6c...8e5a", created: "15 min ago", status: "Verified" },
  { id: "EV-001844", type: "Transaction Proof", description: "Cross-chain bridge transfer confirmation", relatedEntity: "Cross-chain Bridge", hash: "0x9f1b...4d7e", created: "22 min ago", status: "Pending" },
  { id: "EV-001843", type: "Policy Log", description: "New counterparty whitelist rule activated", relatedEntity: "Policy Manager", hash: "0x7e5a...6b3c", created: "35 min ago", status: "Verified" },
  { id: "EV-001842", type: "Access Record", description: "Multi-sig wallet access granted to new signer", relatedEntity: "Wallet 0x4c7D", hash: "0x1a2b...3c4d", created: "1 hr ago", status: "Pending" },
  { id: "EV-001841", type: "Transaction Proof", description: "Batch payroll distribution to 42 recipients", relatedEntity: "Payroll Distributor", hash: "0xd1f9...a4e6", created: "1.5 hrs ago", status: "Verified" },
  { id: "EV-001840", type: "Policy Log", description: "Guardrail trigger threshold updated for max amount", relatedEntity: "Control Center", hash: "0x6e2a...3b1c", created: "2 hrs ago", status: "Verified" },
]

const stats = [
  { label: "Evidence Items", value: "234", icon: Lock },
  { label: "Verified", value: "228", icon: CheckCircle },
  { label: "Pending", value: "6", icon: Clock },
  { label: "Compliance Score", value: "97.4%", icon: ChartBar },
]

const typeFilter: Record<string, string> = {
  all: "All",
  "Transaction Proof": "Transaction Proofs",
  "Policy Log": "Policy Logs",
  "Access Record": "Access Records",
}

export default function EvidencePage() {
  const [tab, setTab] = useState("all")

  const filtered = tab === "all"
    ? evidenceItems
    : evidenceItems.filter((e) => e.type === tab)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Evidence</h1>
        <p className="text-sm text-muted-foreground">Audit evidence and compliance documentation</p>
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
          <CardTitle>Evidence Records</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                {Object.entries(typeFilter).map(([key, label]) => (
                  <TabsTrigger key={key} value={key}>{label}</TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Evidence ID</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Related Entity</TableHead>
                <TableHead>Hash</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((item) => (
                <ContextMenu key={item.id}>
                  <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4"><Badge variant="outline" className="font-mono">{item.id}</Badge></TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.type}</Badge>
                      </TableCell>
                      <TableCell className="max-w-[260px] truncate">{item.description}</TableCell>
                      <TableCell className="text-muted-foreground">{item.relatedEntity}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{item.hash}</TableCell>
                      <TableCell className="text-muted-foreground">{item.created}</TableCell>
                      <TableCell>
                        <Badge variant={item.status === "Verified" ? "success" : "warning"}>
                          {item.status}
                        </Badge>
                      </TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(item.hash); toast.success("Copied to clipboard") }}>
                      Copy Hash
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(item.id); toast.success("Copied to clipboard") }}>
                      Copy Signature
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => window.open(`https://etherscan.io/tx/${item.hash}`, "_blank")}>
                      View Explorer
                    </ContextMenuItem>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(JSON.stringify(item, null, 2)); toast.success("Copied to clipboard") }}>
                      Export
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
