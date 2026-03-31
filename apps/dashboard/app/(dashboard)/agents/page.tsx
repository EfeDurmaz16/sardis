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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Robot,
  Lightning,
  Pause,
  Wallet,
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
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"

type Agent = {
  name: string
  wallet: string
  balance: string
  chain: string
  status: "active" | "paused" | "suspended"
  mandate: string
  lastActive: string
}


const stats = [
  { label: "Total Agents", value: "24", icon: Robot },
  { label: "Active", value: "21", icon: Lightning },
  { label: "Paused", value: "3", icon: Pause },
  { label: "Total Balance", value: "$284,000", icon: Wallet },
]

const statusConfig: Record<Agent["status"], { dotColor: string; label: string; variant: "success" | "warning" | "destructive" }> = {
  active: { dotColor: "bg-success", label: "Active", variant: "success" },
  paused: { dotColor: "bg-warning", label: "Paused", variant: "warning" },
  suspended: { dotColor: "bg-destructive", label: "Suspended", variant: "destructive" },
}

const chainVariant: Record<string, "outline"> = {
  Ethereum: "outline",
  Polygon: "outline",
  Arbitrum: "outline",
  Optimism: "outline",
}

function parseCurrency(val: string): number {
  return parseFloat(val.replace(/[$,]/g, "")) || 0
}

function parseLastActive(val: string): number {
  const match = val.match(/(\d+)\s*(min|hr|hrs|day|days|sec)/)
  if (!match) return 0
  const num = parseInt(match[1])
  const unit = match[2]
  if (unit === "sec") return num
  if (unit === "min") return num * 60
  if (unit === "hr" || unit === "hrs") return num * 3600
  if (unit === "day" || unit === "days") return num * 86400
  return 0
}

const initialAgents: Agent[] = [
  { name: "Payment Router Alpha", wallet: "0x1a2B...9f4E", balance: "$42,800", chain: "Ethereum", status: "active", mandate: "Daily $10k", lastActive: "2 min ago" },
  { name: "Expense Tracker v2", wallet: "0x3c8D...2a1F", balance: "$18,350", chain: "Polygon", status: "active", mandate: "Weekly $25k", lastActive: "5 min ago" },
  { name: "Treasury Sweep Bot", wallet: "0x7e5A...6b3C", balance: "$67,200", chain: "Ethereum", status: "active", mandate: "Monthly $100k", lastActive: "1 min ago" },
  { name: "Vendor Pay Agent", wallet: "0x9f1B...4d7E", balance: "$12,400", chain: "Arbitrum", status: "active", mandate: "Daily $5k", lastActive: "12 min ago" },
  { name: "Subscription Manager", wallet: "0x2d6C...8e5A", balance: "$8,920", chain: "Polygon", status: "paused", mandate: "Monthly $15k", lastActive: "3 hrs ago" },
  { name: "Payroll Distributor", wallet: "0x5b4E...1c9D", balance: "$54,100", chain: "Ethereum", status: "active", mandate: "Monthly $200k", lastActive: "30 min ago" },
  { name: "Gas Optimizer v3", wallet: "0x8a3F...7d2B", balance: "$3,250", chain: "Arbitrum", status: "active", mandate: "Daily $2k", lastActive: "8 min ago" },
  { name: "Cross-chain Bridge", wallet: "0x4c7D...5f8A", balance: "$31,600", chain: "Optimism", status: "active", mandate: "Weekly $50k", lastActive: "15 min ago" },
  { name: "Invoice Settler", wallet: "0x6e2A...3b1C", balance: "$22,750", chain: "Polygon", status: "paused", mandate: "Weekly $20k", lastActive: "1 day ago" },
  { name: "Yield Harvester", wallet: "0xd1f9...a4e6", balance: "$22,630", chain: "Optimism", status: "active", mandate: "Daily $8k", lastActive: "4 min ago" },
]

export default function AgentsPage() {
  const [tab, setTab] = useState("all")
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [agentsList, setAgentsList] = useState<Agent[]>(initialAgents)
  const [detailAgent, setDetailAgent] = useState<Agent | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editAgent, setEditAgent] = useState<Agent | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  function toggleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  const filtered = tab === "all"
    ? agentsList
    : agentsList.filter((a) => a.status === tab)

  const sorted = [...filtered].sort((a, b) => {
    if (!sortKey) return 0
    let cmp = 0
    if (sortKey === "balance") {
      cmp = parseCurrency(a.balance) - parseCurrency(b.balance)
    } else if (sortKey === "lastActive") {
      cmp = parseLastActive(a.lastActive) - parseLastActive(b.lastActive)
    } else {
      const av = a[sortKey as keyof Agent] as string
      const bv = b[sortKey as keyof Agent] as string
      cmp = av.localeCompare(bv)
    }
    return sortDir === "asc" ? cmp : -cmp
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <p className="text-sm text-muted-foreground">Manage and monitor your AI agents</p>
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
          <CardTitle>All Agents</CardTitle>
          <CardAction>
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="paused">Paused</TabsTrigger>
                <TabsTrigger value="suspended">Suspended</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardAction>
        </CardHeader>
        <CardContent className="px-0">
          {filtered.length === 0 ? (
            <EmptyState
              icon={Robot}
              title="No agents yet"
              description="Create your first AI agent to get started"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="pl-4 cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("name")}
                  >
                    <span className="flex items-center gap-1">
                      Agent Name
                      {sortKey === "name" ? (
                        sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead>Wallet Address</TableHead>
                  <TableHead
                    className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("balance")}
                  >
                    <span className="flex items-center justify-end gap-1">
                      Balance
                      {sortKey === "balance" ? (
                        sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead>Chain</TableHead>
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
                  <TableHead>Mandate</TableHead>
                  <TableHead
                    className="cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("lastActive")}
                  >
                    <span className="flex items-center gap-1">
                      Last Active
                      {sortKey === "lastActive" ? (
                        sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />
                      ) : (
                        <ArrowsDownUp className="w-3 h-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((agent) => {
                  const st = statusConfig[agent.status]
                  return (
                    <ContextMenu key={agent.name}>
                      <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-medium">{agent.name}</TableCell>
                        <TableCell>
                          <HoverCard>
                            <HoverCardTrigger>
                              <span className="font-mono text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">{agent.wallet}</span>
                            </HoverCardTrigger>
                            <HoverCardContent className="w-64">
                              <div className="space-y-1.5">
                                <p className="text-sm font-medium">{agent.name}</p>
                                <p className="text-xs font-mono text-muted-foreground">{agent.wallet}</p>
                                <div className="flex items-center gap-1.5">
                                  <span className={`h-1.5 w-1.5 rounded-full ${st.dotColor}`} />
                                  <span className="text-xs">{st.label}</span>
                                </div>
                                <div className="flex justify-between text-xs text-muted-foreground">
                                  <span>{agent.chain}</span>
                                  <span className="font-medium text-foreground">{agent.balance}</span>
                                </div>
                              </div>
                            </HoverCardContent>
                          </HoverCard>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{agent.balance}</TableCell>
                        <TableCell>
                          <Badge variant={chainVariant[agent.chain] ?? "outline"}>{agent.chain}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1.5">
                            <span className={`h-1.5 w-1.5 rounded-full ${st.dotColor}`} />
                            {st.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-muted-foreground">{agent.mandate}</TableCell>
                        <TableCell className="text-muted-foreground">{agent.lastActive}</TableCell>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem onClick={() => { navigator.clipboard.writeText(agent.wallet); toast.success("Copied to clipboard") }}>
                          Copy Agent ID
                        </ContextMenuItem>
                        <ContextMenuSeparator />
                        <ContextMenuItem onClick={() => { setDetailAgent(agent); setSheetOpen(true) }}>View Details</ContextMenuItem>
                        <ContextMenuItem onClick={() => { setEditAgent(agent); setEditOpen(true) }}>Edit</ContextMenuItem>
                      </ContextMenuContent>
                    </ContextMenu>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Agent Details Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{detailAgent?.name}</SheetTitle>
            <SheetDescription>Agent details and configuration</SheetDescription>
          </SheetHeader>
          {detailAgent && (
            <div className="space-y-4 px-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Wallet Address</p>
                  <p className="font-mono text-sm">{detailAgent.wallet}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Balance</p>
                  <p className="text-sm font-medium">{detailAgent.balance}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Chain</p>
                  <p className="text-sm">{detailAgent.chain}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Status</p>
                  <span className="inline-flex items-center gap-1.5 text-sm">
                    <span className={`h-1.5 w-1.5 rounded-full ${statusConfig[detailAgent.status].dotColor}`} />
                    {statusConfig[detailAgent.status].label}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Mandate</p>
                  <p className="text-sm">{detailAgent.mandate}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Last Active</p>
                  <p className="text-sm">{detailAgent.lastActive}</p>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Edit Agent Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Agent</DialogTitle>
            <DialogDescription>Update agent name and mandate</DialogDescription>
          </DialogHeader>
          {editAgent && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                const newName = (formData.get("name") as string).trim()
                const newMandate = (formData.get("mandate") as string).trim()
                if (!newName) return
                setAgentsList((prev) =>
                  prev.map((a) =>
                    a.wallet === editAgent.wallet
                      ? { ...a, name: newName, mandate: newMandate || a.mandate }
                      : a
                  )
                )
                toast.success("Agent updated")
                setEditOpen(false)
              }}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Name</p>
                <Input name="name" defaultValue={editAgent.name} />
              </div>
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Mandate</p>
                <Input name="mandate" defaultValue={editAgent.mandate} />
              </div>
              <DialogFooter>
                <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
                <Button type="submit">Save</Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
