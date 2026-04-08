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
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardisList } from "@/hooks/use-sardis"

type EvidenceItem = {
  id: string
  type: "Transaction Proof" | "Policy Log" | "Access Record"
  description: string
  relatedEntity: string
  hash: string
  created: string
  status: "Verified" | "Pending"
}

const typeFilter: Record<string, string> = {
  all: "All",
  "Transaction Proof": "Transaction Proofs",
  "Policy Log": "Policy Logs",
  "Access Record": "Access Records",
}

export default function EvidencePage() {
  const { data: evidenceData, loading } = useSardisList<EvidenceItem>("api/v2/evidence", "Evidence")
  const evidenceItems = evidenceData ?? []

  const [tab, setTab] = useState("all")

  const filtered = tab === "all"
    ? evidenceItems
    : evidenceItems.filter((e) => e.type === tab)

  const stats = useMemo(() => {
    const total = evidenceItems.length
    const verified = evidenceItems.filter((e) => e.status === "Verified").length
    const pending = evidenceItems.filter((e) => e.status === "Pending").length
    const score = total > 0 ? ((verified / total) * 100).toFixed(1) : "0.0"

    return [
      { label: "Evidence Items", value: String(total), icon: Lock },
      { label: "Verified", value: String(verified), icon: CheckCircle },
      { label: "Pending", value: String(pending), icon: Clock },
      { label: "Compliance Score", value: `${score}%`, icon: ChartBar },
    ]
  }, [evidenceItems])

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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : evidenceItems.length === 0 ? (
            <EmptyState
              icon={Lock}
              title="No evidence records"
              description="Evidence records will appear here as transactions and policy actions are recorded"
            />
          ) : (
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
          )}
        </CardContent>
      </Card>
    </div>
  )
}
