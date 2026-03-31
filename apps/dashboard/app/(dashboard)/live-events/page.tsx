"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Lightning,
  Broadcast,
  Warning,
  Timer,
} from "@phosphor-icons/react"

type EventItem = {
  id: string
  timestamp: string
  type: string
  message: string
  chain: string
  severity: "info" | "warning" | "error" | "success"
}

const events: EventItem[] = [
  { id: "evt_001", timestamp: "14:32:07.412", type: "payment.completed", message: "Payment of $2,400 processed via Ethereum mainnet", chain: "Ethereum", severity: "success" },
  { id: "evt_002", timestamp: "14:32:06.891", type: "agent.delegated", message: "Treasury Sweep Bot delegated to Payment Router Alpha", chain: "Polygon", severity: "info" },
  { id: "evt_003", timestamp: "14:32:05.234", type: "hold.created", message: "Hold of $5,000 created for vendor payment batch", chain: "Ethereum", severity: "info" },
  { id: "evt_004", timestamp: "14:32:04.102", type: "policy.triggered", message: "Velocity limit policy triggered — daily threshold 80% reached", chain: "Arbitrum", severity: "warning" },
  { id: "evt_005", timestamp: "14:32:03.556", type: "payment.completed", message: "Subscription payment of $99 settled on Polygon", chain: "Polygon", severity: "success" },
  { id: "evt_006", timestamp: "14:32:02.001", type: "mandate.updated", message: "Mandate limit increased to $50k/week for Payroll Distributor", chain: "Ethereum", severity: "info" },
  { id: "evt_007", timestamp: "14:32:00.887", type: "agent.paused", message: "Invoice Settler paused due to insufficient balance", chain: "Polygon", severity: "warning" },
  { id: "evt_008", timestamp: "14:31:59.334", type: "payment.failed", message: "Cross-chain transfer failed — gas estimation error on Optimism", chain: "Optimism", severity: "error" },
  { id: "evt_009", timestamp: "14:31:58.221", type: "hold.released", message: "Hold of $3,200 released after approval confirmation", chain: "Arbitrum", severity: "success" },
  { id: "evt_010", timestamp: "14:31:57.009", type: "policy.triggered", message: "Counterparty whitelist check passed for 0x7e5A...6b3C", chain: "Ethereum", severity: "info" },
  { id: "evt_011", timestamp: "14:31:55.776", type: "wallet.funded", message: "Gas Optimizer v3 wallet topped up with 0.5 ETH", chain: "Arbitrum", severity: "info" },
  { id: "evt_012", timestamp: "14:31:54.443", type: "payment.completed", message: "Invoice #INV-2847 settled for $12,500", chain: "Ethereum", severity: "success" },
  { id: "evt_013", timestamp: "14:31:53.112", type: "agent.delegated", message: "Yield Harvester delegated cross-chain swap to Bridge Agent", chain: "Optimism", severity: "info" },
  { id: "evt_014", timestamp: "14:31:51.998", type: "policy.triggered", message: "Amount threshold exceeded — manual approval required for $25k transfer", chain: "Ethereum", severity: "warning" },
  { id: "evt_015", timestamp: "14:31:50.665", type: "payment.completed", message: "Batch payroll distribution completed — 12 recipients", chain: "Ethereum", severity: "success" },
  { id: "evt_016", timestamp: "14:31:49.334", type: "reconciliation.mismatch", message: "Balance mismatch detected on Polygon wallet 0x3c8D...2a1F", chain: "Polygon", severity: "error" },
  { id: "evt_017", timestamp: "14:31:48.001", type: "hold.created", message: "Precautionary hold of $1,800 for new counterparty", chain: "Arbitrum", severity: "info" },
]

const stats = [
  { label: "Events / Min", value: "342", icon: Lightning },
  { label: "Active Streams", value: "5", icon: Broadcast },
  { label: "Error Rate", value: "0.3%", icon: Warning },
  { label: "Avg Latency", value: "45ms", icon: Timer },
]

const severityConfig: Record<EventItem["severity"], { dot: string; label: string }> = {
  info: { dot: "bg-info", label: "Info" },
  warning: { dot: "bg-warning", label: "Warning" },
  error: { dot: "bg-destructive", label: "Error" },
  success: { dot: "bg-success", label: "Success" },
}

const typeVariant: Record<string, "default" | "secondary" | "outline" | "destructive" | "success" | "warning"> = {
  "payment.completed": "success",
  "payment.failed": "destructive",
  "agent.delegated": "secondary",
  "agent.paused": "warning",
  "hold.created": "outline",
  "hold.released": "secondary",
  "policy.triggered": "warning",
  "mandate.updated": "secondary",
  "wallet.funded": "secondary",
  "reconciliation.mismatch": "destructive",
}

export default function LiveEventsPage() {
  const [typeFilter, setTypeFilter] = useState("all")
  const [chainFilter, setChainFilter] = useState("all")
  const [severityFilter, setSeverityFilter] = useState("all")
  const [search, setSearch] = useState("")

  const filtered = events.filter((e) => {
    if (typeFilter !== "all" && e.type !== typeFilter) return false
    if (chainFilter !== "all" && e.chain !== chainFilter) return false
    if (severityFilter !== "all" && e.severity !== severityFilter) return false
    if (search && !e.message.toLowerCase().includes(search.toLowerCase()) && !e.type.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Live Events</h1>
        <p className="text-sm text-muted-foreground">Real-time event stream across all agents and services</p>
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
          <CardTitle>Event Feed</CardTitle>
          <CardAction>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
              </span>
              <span className="text-xs text-muted-foreground">Live</span>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2 py-3">
            <Select value={typeFilter} onValueChange={(v) => v && setTypeFilter(v)} items={{ all: "All Types", "payment.completed": "payment.completed", "payment.failed": "payment.failed", "agent.delegated": "agent.delegated", "agent.paused": "agent.paused", "hold.created": "hold.created", "hold.released": "hold.released", "policy.triggered": "policy.triggered", "mandate.updated": "mandate.updated", "wallet.funded": "wallet.funded", "reconciliation.mismatch": "reconciliation.mismatch" }}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Event Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="payment.completed">payment.completed</SelectItem>
                <SelectItem value="payment.failed">payment.failed</SelectItem>
                <SelectItem value="agent.delegated">agent.delegated</SelectItem>
                <SelectItem value="agent.paused">agent.paused</SelectItem>
                <SelectItem value="hold.created">hold.created</SelectItem>
                <SelectItem value="hold.released">hold.released</SelectItem>
                <SelectItem value="policy.triggered">policy.triggered</SelectItem>
                <SelectItem value="mandate.updated">mandate.updated</SelectItem>
                <SelectItem value="wallet.funded">wallet.funded</SelectItem>
                <SelectItem value="reconciliation.mismatch">reconciliation.mismatch</SelectItem>
              </SelectContent>
            </Select>
            <Select value={chainFilter} onValueChange={(v) => v && setChainFilter(v)} items={{ all: "All Chains", Ethereum: "Ethereum", Polygon: "Polygon", Arbitrum: "Arbitrum", Optimism: "Optimism" }}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Chain" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Chains</SelectItem>
                <SelectItem value="Ethereum">Ethereum</SelectItem>
                <SelectItem value="Polygon">Polygon</SelectItem>
                <SelectItem value="Arbitrum">Arbitrum</SelectItem>
                <SelectItem value="Optimism">Optimism</SelectItem>
              </SelectContent>
            </Select>
            <Select value={severityFilter} onValueChange={(v) => v && setSeverityFilter(v)} items={{ all: "All Severity", info: "Info", warning: "Warning", error: "Error", success: "Success" }}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="info">Info</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="error">Error</SelectItem>
                <SelectItem value="success">Success</SelectItem>
              </SelectContent>
            </Select>
            <Input
              placeholder="Search events..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-48"
            />
          </div>
          <ScrollArea className="h-[520px]">
            <div className="space-y-1">
              {filtered.map((event) => {
                const sev = severityConfig[event.severity]
                return (
                  <div
                    key={event.id}
                    className="flex items-start gap-3 rounded-md px-3 py-2.5 hover:bg-muted/50 transition-colors"
                  >
                    <span className="font-mono text-[11px] text-muted-foreground pt-0.5 shrink-0 w-[88px]">
                      {event.timestamp}
                    </span>
                    <Badge variant={typeVariant[event.type] ?? "outline"} className="shrink-0 text-[10px]">
                      {event.type}
                    </Badge>
                    <span className="text-sm flex-1 min-w-0 truncate">{event.message}</span>
                    <Badge variant="outline" className="shrink-0 text-[10px]">{event.chain}</Badge>
                    <span className="flex items-center gap-1.5 shrink-0">
                      <span className={`h-1.5 w-1.5 rounded-full ${sev.dot}`} />
                      <span className="text-[11px] text-muted-foreground">{sev.label}</span>
                    </span>
                  </div>
                )
              })}
              {filtered.length === 0 && (
                <div className="text-center py-12 text-sm text-muted-foreground">No events match the current filters</div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}
