"use client"

import { useState } from "react"
import {
  Card, CardHeader, CardTitle, CardContent, CardDescription, CardAction,
} from "@/components/ui/card"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import {
  ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger, ContextMenuSeparator,
} from "@/components/ui/context-menu"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import {
  ArrowUp, Circle, CaretDown, CaretUp, CheckCircle, Rocket, ShieldCheck, Users,
  Spinner, CloudSlash,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts"
import { useSardis } from "@/hooks/use-sardis"

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type DashboardMetrics = {
  balance_usd: string
  balance_chain: string
  volume_24h_usd: string
  tx_count_24h: number
  tx_count_total: number
  agent_count: number
  active_agents: number
  online_agents: number
  api_calls_24h: number
  agent_events_24h: number
  mandate_count: number
  active_sessions: number
  policy_pass_rate: number
  policy_blocked_24h: number
  wallet_count: number
  environment: string
  chain: string
}

type LedgerTransaction = {
  tx_id: string
  from_wallet: string
  to_wallet: string
  amount: string
  currency: string
  chain: string | null
  chain_tx_hash: string | null
  audit_anchor: string | null
  created_at: string
  status: string
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusDot: Record<string, string> = {
  confirmed: "text-success",
  completed: "text-success",
  pending: "text-warning",
  failed: "text-destructive",
  blocked: "text-destructive",
}

const statusBadgeVariant: Record<string, "success" | "warning" | "info"> = {
  confirmed: "success",
  completed: "success",
  pending: "warning",
  failed: "warning",
}

function formatUsd(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value
  if (!Number.isFinite(num)) return "$0.00"
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function shortenId(id: string): string {
  if (id.length <= 12) return id
  return `${id.slice(0, 6)}...${id.slice(-4)}`
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function OverviewPage() {
  const { data: metrics, loading: metricsLoading, error: metricsError } = useSardis<DashboardMetrics>("api/v2/dashboard/metrics")
  const { data: recentTxs, loading: txsLoading } = useSardis<LedgerTransaction[]>("api/v2/ledger/recent?limit=5")

  const [quickStartOpen, setQuickStartOpen] = useState(true)
  const [quickStartSteps, setQuickStartSteps] = useState([
    { label: "Create your first agent", done: false, icon: Rocket },
    { label: "Connect a wallet", done: false, icon: ShieldCheck },
    { label: "Set up merchant verification", done: false, icon: Users },
    { label: "Configure payment policies", done: false, icon: ShieldCheck },
  ])
  const completedSteps = quickStartSteps.filter((s) => s.done).length

  // New Payment dialog
  const [newPaymentOpen, setNewPaymentOpen] = useState(false)
  const [paymentRecipient, setPaymentRecipient] = useState("")
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentChain, setPaymentChain] = useState("Base")

  // Derive quick-start completion from real metrics
  const agentExists = (metrics?.agent_count ?? 0) > 0
  const walletExists = (metrics?.wallet_count ?? 0) > 0
  if (agentExists && !quickStartSteps[0].done) {
    quickStartSteps[0] = { ...quickStartSteps[0], done: true }
  }
  if (walletExists && !quickStartSteps[1].done) {
    quickStartSteps[1] = { ...quickStartSteps[1], done: true }
  }

  function handleQuickStartClick(index: number) {
    if (quickStartSteps[index].done) return
    setQuickStartSteps((prev) => prev.map((s, i) =>
      i === index ? { ...s, done: true } : s
    ))
    toast.success(`Completed: ${quickStartSteps[index].label}`)
  }

  function handleNewPayment() {
    if (!paymentRecipient || !paymentAmount) {
      toast.error("Please fill in all fields")
      return
    }
    toast.success(`Payment of $${paymentAmount} to ${paymentRecipient} initiated on ${paymentChain}`)
    setNewPaymentOpen(false)
    setPaymentRecipient("")
    setPaymentAmount("")
    setPaymentChain("Base")
  }

  const txList = recentTxs ?? []

  return (
    <>
      {/* ---- Stats Row ---- */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 flex-1">
          {metricsLoading ? (
            <>
              {[1,2,3,4].map((i) => (
                <Card key={i}><CardContent><div className="animate-pulse h-12 bg-muted rounded" /></CardContent></Card>
              ))}
            </>
          ) : metricsError ? (
            <Card className="col-span-full">
              <CardContent className="flex items-center gap-3 py-4">
                <CloudSlash className="w-5 h-5 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Dashboard metrics unavailable. Configure SARDIS_API_KEY to connect.</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <StatCard label="Active Agents" value={String(metrics?.active_agents ?? 0)} sub={`${metrics?.agent_count ?? 0} total`} positive={(metrics?.active_agents ?? 0) > 0} />
              <StatCard label="24h Volume" value={formatUsd(metrics?.volume_24h_usd ?? "0")} sub={`${metrics?.tx_count_24h ?? 0} txs`} positive={(metrics?.tx_count_24h ?? 0) > 0} />
              <StatCard label="Wallets" value={String(metrics?.wallet_count ?? 0)} sub={metrics?.chain ?? ""} />
              <StatCard label="Policy Pass Rate" value={`${metrics?.policy_pass_rate ?? 100}%`} sub={`${metrics?.policy_blocked_24h ?? 0} blocked`} />
            </>
          )}
        </div>

        {!metricsLoading && !metricsError && (
          <div className="flex flex-wrap lg:flex-col gap-2 lg:justify-center">
            <StatusPill color={metrics?.active_sessions ? "amber" : "green"} label={metrics?.active_sessions ? `${metrics.active_sessions} Active Sessions` : "No active sessions"} />
            <StatusPill color="green" label={`Environment: ${metrics?.environment ?? "unknown"}`} />
            <StatusPill color="blue" label={`${metrics?.mandate_count ?? 0} Mandates`} />
          </div>
        )}
      </div>

      {/* ---- New Payment Button ---- */}
      <div className="flex justify-end mt-4">
        <Button onClick={() => setNewPaymentOpen(true)}>New Payment</Button>
      </div>

      {/* ---- Main Grid ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-4 mt-4">
        {/* Left — Transaction Feed */}
        <Card size="sm">
          <CardHeader className="border-b">
            <CardTitle>Recent Transactions</CardTitle>
            <CardDescription>{txList.length > 0 ? `${txList.length} transactions` : "No transactions yet"}</CardDescription>
          </CardHeader>
          <CardContent className="divide-y">
            {txsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : txList.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Transactions will appear here once your agents start making payments
              </p>
            ) : (
              txList.map((tx) => (
                <ContextMenu key={tx.tx_id}>
                  <ContextMenuTrigger>
                    <div className="flex items-center gap-3 py-3">
                      <Circle weight="fill" className={cn("h-1.5 w-1.5 flex-shrink-0", statusDot[tx.status] || "text-muted-foreground")} />
                      <div className="flex-1 min-w-0">
                        <div className="text-[13px] font-medium truncate">{tx.from_wallet} → {tx.to_wallet}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <HoverCard>
                            <HoverCardTrigger>
                              <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-mono cursor-pointer">{shortenId(tx.tx_id)}</Badge>
                            </HoverCardTrigger>
                            <HoverCardContent className="w-64">
                              <div className="space-y-1.5">
                                <p className="text-xs font-mono text-muted-foreground">{tx.tx_id}</p>
                                <p className="text-sm">{tx.from_wallet} → {tx.to_wallet}</p>
                                <div className="flex justify-between text-xs text-muted-foreground">
                                  <span>{tx.chain || "—"}</span>
                                  <span className="font-medium text-foreground">{formatUsd(tx.amount)}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <Circle weight="fill" className={cn("h-1.5 w-1.5", statusDot[tx.status] || "text-muted-foreground")} />
                                  <span className="text-xs capitalize">{tx.status}</span>
                                </div>
                              </div>
                            </HoverCardContent>
                          </HoverCard>
                          {tx.chain && <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">{tx.chain}</Badge>}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-[13px] font-medium tabular-nums">{formatUsd(tx.amount)}</div>
                        <div className="text-[11px] text-muted-foreground">{timeAgo(tx.created_at)}</div>
                      </div>
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.tx_id); toast.success("Copied to clipboard") }}>Copy TX ID</ContextMenuItem>
                    {tx.chain_tx_hash && <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.chain_tx_hash!); toast.success("Copied to clipboard") }}>Copy Hash</ContextMenuItem>}
                    <ContextMenuSeparator />
                    {tx.chain_tx_hash && (
                      <ContextMenuItem onClick={() => window.open(`https://basescan.org/tx/${tx.chain_tx_hash}`, "_blank")}>View on Explorer</ContextMenuItem>
                    )}
                  </ContextMenuContent>
                </ContextMenu>
              ))
            )}
          </CardContent>
        </Card>

        {/* Right — Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Agents Summary */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Agents</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {metricsLoading ? (
                <div className="animate-pulse h-20 bg-muted rounded" />
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Total Agents</span>
                    <span className="font-semibold tabular-nums">{metrics?.agent_count ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active</span>
                    <span className="font-semibold tabular-nums">{metrics?.active_agents ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Online (2m)</span>
                    <span className="font-semibold tabular-nums">{metrics?.online_agents ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Events (24h)</span>
                    <span className="font-semibold tabular-nums">{metrics?.agent_events_24h ?? 0}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* API Activity */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>API Activity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {metricsLoading ? (
                <div className="animate-pulse h-20 bg-muted rounded" />
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">API Calls (24h)</span>
                    <span className="font-semibold tabular-nums">{metrics?.api_calls_24h ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Total Transactions</span>
                    <span className="font-semibold tabular-nums">{(metrics?.tx_count_total ?? 0).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Blocked (24h)</span>
                    <span className="font-semibold tabular-nums">{metrics?.policy_blocked_24h ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active Sessions</span>
                    <span className="font-semibold tabular-nums">{metrics?.active_sessions ?? 0}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Wallets Summary */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Wallets</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {metricsLoading ? (
                <div className="animate-pulse h-20 bg-muted rounded" />
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Total Wallets</span>
                    <span className="font-semibold tabular-nums">{metrics?.wallet_count ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Balance</span>
                    <span className="font-semibold tabular-nums">{formatUsd(metrics?.balance_usd ?? "0")}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Chain</span>
                    <span className="font-semibold">{metrics?.balance_chain ?? "—"}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Policy Health */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Policy Health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {metricsLoading ? (
                <div className="animate-pulse h-20 bg-muted rounded" />
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Pass Rate</span>
                    <span className="font-semibold tabular-nums">{metrics?.policy_pass_rate ?? 100}%</span>
                  </div>
                  <Progress value={metrics?.policy_pass_rate ?? 100} className="h-1.5" />
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Mandates</span>
                    <span className="font-semibold tabular-nums">{metrics?.mandate_count ?? 0}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ---- QuickStart Strip ---- */}
      <Card size="sm">
        <CardHeader
          className="cursor-pointer select-none"
          onClick={() => setQuickStartOpen((v) => !v)}
        >
          <div>
            <CardTitle className="flex items-center gap-2">
              Get Started with Sardis
              {quickStartOpen ? <CaretUp className="w-3.5 h-3.5 text-muted-foreground" /> : <CaretDown className="w-3.5 h-3.5 text-muted-foreground" />}
            </CardTitle>
            <CardDescription>{completedSteps}/{quickStartSteps.length} complete</CardDescription>
          </div>
          <CardAction>
            <Progress value={(completedSteps / quickStartSteps.length) * 100} className="w-32 h-1.5" />
          </CardAction>
        </CardHeader>
        {quickStartOpen && (
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {quickStartSteps.map((step, i) => {
                const Ico = step.icon
                return (
                  <button
                    key={i}
                    onClick={(e) => { e.stopPropagation(); handleQuickStartClick(i) }}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border p-3 text-[13px] text-left transition-colors",
                      step.done
                        ? "bg-muted/50 text-muted-foreground"
                        : "bg-card hover:bg-muted/30 cursor-pointer"
                    )}
                  >
                    {step.done ? (
                      <CheckCircle weight="fill" className="w-5 h-5 text-success flex-shrink-0" />
                    ) : (
                      <Ico className="w-5 h-5 text-muted-foreground flex-shrink-0" />
                    )}
                    <span className={cn(step.done && "line-through")}>{step.label}</span>
                  </button>
                )
              })}
            </div>
          </CardContent>
        )}
      </Card>

      {/* New Payment Dialog */}
      <Dialog open={newPaymentOpen} onOpenChange={setNewPaymentOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New Payment</DialogTitle>
            <DialogDescription>Create a new payment transaction</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Recipient</label>
              <Input value={paymentRecipient} onChange={(e) => setPaymentRecipient(e.target.value)} placeholder="e.g. MerchantCo or 0x..." />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Amount ($)</label>
              <Input type="number" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} placeholder="0.00" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Chain</label>
              <div className="flex gap-2">
                {["Base", "Polygon", "Arbitrum", "Optimism", "Ethereum"].map((chain) => (
                  <Button
                    key={chain}
                    variant={paymentChain === chain ? "default" : "outline"}
                    size="xs"
                    onClick={() => setPaymentChain(chain)}
                  >
                    {chain}
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={handleNewPayment}>Send Payment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function StatCard({ label, value, sub, positive }: {
  label: string
  value: string
  sub: string
  positive?: boolean
}) {
  return (
    <Card>
      <CardContent>
        <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">{label}</div>
        <div className="text-xl font-semibold mt-0.5 tabular-nums">{value}</div>
        <div className={cn(
          "flex items-center gap-1 text-[11px] mt-0.5",
          positive ? "text-success" : "text-muted-foreground"
        )}>
          {positive && <ArrowUp className="w-3 h-3" weight="bold" />}
          {sub}
        </div>
      </CardContent>
    </Card>
  )
}

function StatusPill({ color, label }: { color: "amber" | "green" | "blue"; label: string }) {
  const dotColor = {
    amber: "bg-warning",
    green: "bg-success",
    blue: "bg-info",
  }[color]

  return (
    <div className="flex items-center gap-2 rounded-full border bg-card px-3 py-1.5 text-[11px] font-medium">
      <span className={cn("w-1.5 h-1.5 rounded-full", dotColor)} />
      {label}
    </div>
  )
}
