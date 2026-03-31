"use client"

import { useEffect, useMemo, useState } from "react"
import { formatDistanceToNow } from "date-fns"
import {
  Card,
  CardAction,
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowClockwise,
  ArrowDown,
  ArrowUp,
  ArrowsDownUp,
  Lightning,
  Pause,
  Robot,
  ShieldWarning,
  Wallet,
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
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { AuthRequiredError, type AgentApiRecord, type WalletApiRecord, listAgents, listWallets } from "@/lib/sardis-api"

type AgentStatus = "active" | "paused" | "suspended"

type AgentRow = {
  agentId: string
  name: string
  description: string | null
  walletId: string | null
  walletAddress: string | null
  chain: string
  perTransactionLimit: string
  dailyLimit: string
  status: AgentStatus
  kyaStatus: string
  updatedAt: string
  ownerId: string
  nextSteps: string[]
}

const statusConfig: Record<AgentStatus, { dotColor: string; label: string; variant: "success" | "warning" | "destructive" }> = {
  active: { dotColor: "bg-success", label: "Active", variant: "success" },
  paused: { dotColor: "bg-warning", label: "Paused", variant: "warning" },
  suspended: { dotColor: "bg-destructive", label: "Suspended", variant: "destructive" },
}

const chainVariant: Record<string, "outline"> = {
  Ethereum: "outline",
  Polygon: "outline",
  Arbitrum: "outline",
  Optimism: "outline",
  Base: "outline",
  "Base Sepolia": "outline",
  Unknown: "outline",
  Unassigned: "outline",
}

function formatCurrency(value?: string | null): string {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) {
    return "$0"
  }
  return `$${amount.toLocaleString("en-US", { maximumFractionDigits: 0 })}`
}

function formatRelativeTime(timestamp: string): string {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) {
    return "Unavailable"
  }
  return `${formatDistanceToNow(parsed, { addSuffix: true })}`
}

function formatChainLabel(chain: string | null | undefined): string {
  if (!chain) {
    return "Unassigned"
  }

  const normalized = chain.replace(/[_-]/g, " ").trim()
  if (!normalized) {
    return "Unassigned"
  }

  return normalized.replace(/\b\w/g, (char) => char.toUpperCase())
}

function primaryWalletAddress(wallet?: WalletApiRecord): string | null {
  if (!wallet) {
    return null
  }

  return Object.values(wallet.addresses).find(Boolean) || null
}

function primaryWalletChain(wallet?: WalletApiRecord): string {
  if (!wallet) {
    return "Unassigned"
  }

  const firstChain = Object.keys(wallet.addresses).find((key) => wallet.addresses[key])
  return formatChainLabel(firstChain)
}

function resolveAgentStatus(agent: AgentApiRecord): AgentStatus {
  if (!agent.is_active) {
    return "paused"
  }

  if (["rejected", "blocked", "suspended"].includes(agent.kya_status.toLowerCase())) {
    return "suspended"
  }

  return "active"
}

function buildAgentRow(agent: AgentApiRecord, wallet?: WalletApiRecord): AgentRow {
  return {
    agentId: agent.agent_id,
    name: agent.name,
    description: agent.description,
    walletId: agent.wallet_id,
    walletAddress: primaryWalletAddress(wallet),
    chain: primaryWalletChain(wallet),
    perTransactionLimit: formatCurrency(agent.spending_limits?.per_transaction),
    dailyLimit: formatCurrency(agent.spending_limits?.daily),
    status: resolveAgentStatus(agent),
    kyaStatus: agent.kya_status,
    updatedAt: agent.updated_at,
    ownerId: agent.owner_id,
    nextSteps: agent.next_steps || [],
  }
}

type SortKey = "name" | "perTransactionLimit" | "dailyLimit" | "status" | "updatedAt"

export default function AgentsPage() {
  const [tab, setTab] = useState("all")
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [agentsList, setAgentsList] = useState<AgentRow[]>([])
  const [detailAgent, setDetailAgent] = useState<AgentRow | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [authRequired, setAuthRequired] = useState(false)

  async function loadAgents() {
    setLoading(true)
    setErrorMessage(null)
    setAuthRequired(false)

    try {
      const [agents, wallets] = await Promise.all([listAgents(), listWallets()])
      const walletsById = new Map(wallets.map((wallet) => [wallet.wallet_id, wallet]))
      setAgentsList(agents.map((agent) => buildAgentRow(agent, agent.wallet_id ? walletsById.get(agent.wallet_id) : undefined)))
    } catch (error) {
      if (error instanceof AuthRequiredError) {
        setAuthRequired(true)
        setAgentsList([])
      } else {
        setErrorMessage(error instanceof Error ? error.message : "Failed to load agents")
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadAgents()
  }, [])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((direction) => (direction === "asc" ? "desc" : "asc"))
      return
    }

    setSortKey(key)
    setSortDir("asc")
  }

  const stats = useMemo(() => {
    const activeCount = agentsList.filter((agent) => agent.status === "active").length
    const pausedCount = agentsList.filter((agent) => agent.status === "paused").length
    const walletLinkedCount = agentsList.filter((agent) => agent.walletId).length

    return [
      { label: "Total Agents", value: `${agentsList.length}`, icon: Robot },
      { label: "Active", value: `${activeCount}`, icon: Lightning },
      { label: "Paused", value: `${pausedCount}`, icon: Pause },
      { label: "Wallet Linked", value: `${walletLinkedCount}`, icon: Wallet },
    ]
  }, [agentsList])

  const filtered = useMemo(() => {
    if (tab === "all") {
      return agentsList
    }

    return agentsList.filter((agent) => agent.status === tab)
  }, [agentsList, tab])

  const sorted = useMemo(() => {
    return [...filtered].sort((left, right) => {
      if (!sortKey) {
        return 0
      }

      let comparison = 0

      if (sortKey === "perTransactionLimit" || sortKey === "dailyLimit") {
        comparison = Number(left[sortKey].replace(/[$,]/g, "")) - Number(right[sortKey].replace(/[$,]/g, ""))
      } else if (sortKey === "updatedAt") {
        comparison = new Date(left.updatedAt).getTime() - new Date(right.updatedAt).getTime()
      } else {
        comparison = left[sortKey].localeCompare(right[sortKey])
      }

      return sortDir === "asc" ? comparison : -comparison
    })
  }, [filtered, sortDir, sortKey])

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
          <p className="text-sm text-muted-foreground">Real agent records from the canonical Sardis API.</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void loadAgents()} disabled={loading}>
          <ArrowClockwise className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{loading ? "…" : stat.value}</p>
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
          {loading ? (
            <div className="px-6 py-10 text-sm text-muted-foreground">Loading agents…</div>
          ) : authRequired ? (
            <EmptyState
              icon={ShieldWarning}
              title="Authentication required"
              description="The canonical dashboard could not find a Sardis session token for the live API."
              action={() => void loadAgents()}
              actionLabel="Retry"
            />
          ) : errorMessage ? (
            <EmptyState
              icon={ShieldWarning}
              title="Unable to load agents"
              description={errorMessage}
              action={() => void loadAgents()}
              actionLabel="Retry"
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={Robot}
              title="No agents yet"
              description="Create your first real agent to start issuing wallets and policies."
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
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead>Wallet Address</TableHead>
                  <TableHead
                    className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("perTransactionLimit")}
                  >
                    <span className="flex items-center justify-end gap-1">
                      Per Tx Limit
                      {sortKey === "perTransactionLimit" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
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
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead
                    className="text-right cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("dailyLimit")}
                  >
                    <span className="flex items-center justify-end gap-1">
                      Daily Limit
                      {sortKey === "dailyLimit" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer select-none hover:text-foreground transition-colors"
                    onClick={() => toggleSort("updatedAt")}
                  >
                    <span className="flex items-center gap-1">
                      Last Updated
                      {sortKey === "updatedAt" ? (
                        sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
                      ) : (
                        <ArrowsDownUp className="h-3 w-3 text-muted-foreground/50" />
                      )}
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((agent) => {
                  const status = statusConfig[agent.status]
                  const walletLabel = agent.walletAddress || agent.walletId || "Not linked"
                  return (
                    <ContextMenu key={agent.agentId}>
                      <ContextMenuTrigger render={<TableRow />}>
                        <TableCell className="pl-4 font-medium">{agent.name}</TableCell>
                        <TableCell>
                          <HoverCard>
                            <HoverCardTrigger>
                              <span className="cursor-pointer font-mono text-xs text-muted-foreground hover:text-foreground transition-colors">
                                {walletLabel}
                              </span>
                            </HoverCardTrigger>
                            <HoverCardContent className="w-72">
                              <div className="space-y-1.5">
                                <p className="text-sm font-medium">{agent.name}</p>
                                <p className="text-xs font-mono text-muted-foreground">{agent.agentId}</p>
                                <p className="text-xs text-muted-foreground">
                                  {agent.description || "No description provided"}
                                </p>
                                <div className="flex items-center gap-1.5">
                                  <span className={`h-1.5 w-1.5 rounded-full ${status.dotColor}`} />
                                  <span className="text-xs">{status.label}</span>
                                </div>
                              </div>
                            </HoverCardContent>
                          </HoverCard>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{agent.perTransactionLimit}</TableCell>
                        <TableCell>
                          <Badge variant={chainVariant[agent.chain] ?? "outline"}>{agent.chain}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1.5">
                            <span className={`h-1.5 w-1.5 rounded-full ${status.dotColor}`} />
                            {status.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-right tabular-nums text-muted-foreground">{agent.dailyLimit}</TableCell>
                        <TableCell className="text-muted-foreground">{formatRelativeTime(agent.updatedAt)}</TableCell>
                      </ContextMenuTrigger>
                      <ContextMenuContent>
                        <ContextMenuItem
                          onClick={() => {
                            navigator.clipboard.writeText(agent.agentId)
                            toast.success("Copied agent ID")
                          }}
                        >
                          Copy Agent ID
                        </ContextMenuItem>
                        {agent.walletAddress ? (
                          <ContextMenuItem
                            onClick={() => {
                              navigator.clipboard.writeText(agent.walletAddress!)
                              toast.success("Copied wallet address")
                            }}
                          >
                            Copy Wallet Address
                          </ContextMenuItem>
                        ) : null}
                        <ContextMenuSeparator />
                        <ContextMenuItem
                          onClick={() => {
                            setDetailAgent(agent)
                            setSheetOpen(true)
                          }}
                        >
                          View Details
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

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{detailAgent?.name}</SheetTitle>
            <SheetDescription>Canonical agent metadata from the live API.</SheetDescription>
          </SheetHeader>
          {detailAgent ? (
            <div className="space-y-4 px-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Agent ID</p>
                  <p className="font-mono text-sm">{detailAgent.agentId}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Owner</p>
                  <p className="text-sm">{detailAgent.ownerId}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Wallet</p>
                  <p className="font-mono text-sm">{detailAgent.walletAddress || detailAgent.walletId || "Not linked"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Description</p>
                  <p className="text-sm">{detailAgent.description || "No description provided"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Status</p>
                  <span className="inline-flex items-center gap-1.5 text-sm">
                    <span className={`h-1.5 w-1.5 rounded-full ${statusConfig[detailAgent.status].dotColor}`} />
                    {statusConfig[detailAgent.status].label}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">KYA Status</p>
                  <p className="text-sm capitalize">{detailAgent.kyaStatus}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Per-transaction limit</p>
                  <p className="text-sm">{detailAgent.perTransactionLimit}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Daily limit</p>
                  <p className="text-sm">{detailAgent.dailyLimit}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Last updated</p>
                  <p className="text-sm">{formatRelativeTime(detailAgent.updatedAt)}</p>
                </div>
                {detailAgent.nextSteps.length > 0 ? (
                  <div>
                    <p className="text-xs text-muted-foreground">Next steps</p>
                    <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                      {detailAgent.nextSteps.map((step) => (
                        <li key={step}>• {step}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  )
}
