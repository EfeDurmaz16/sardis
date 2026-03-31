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
} from "@phosphor-icons/react"
import { toast } from "sonner"
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts"

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const transactions = [
  { status: "success", desc: "Agent→Merchant Payment", txId: "tx_8f3a", chain: "Base", amount: "+$2,400.00", time: "2m ago" },
  { status: "success", desc: "Agent→Agent Transfer", txId: "tx_1b7c", chain: "Polygon", amount: "+$890.00", time: "5m ago" },
  { status: "pending", desc: "Payment Hold Created", txId: "tx_4e2d", chain: "Arbitrum", amount: "$1,200.00", time: "8m ago" },
  { status: "failed", desc: "Agent→Merchant Payment", txId: "tx_9d1f", chain: "Optimism", amount: "$340.00", time: "12m ago" },
  { status: "success", desc: "Refund Processed", txId: "tx_6a4b", chain: "Base", amount: "-$156.00", time: "15m ago" },
]

const pieData = [
  { name: "Agent→Merchant", value: 45, color: "var(--chart-5)" },
  { name: "Agent→Agent", value: 28, color: "var(--chart-4)" },
  { name: "Holds", value: 18, color: "var(--chart-2)" },
  { name: "Refunds", value: 9, color: "var(--chart-1)" },
]

const networkHealth = [
  { chain: "Base", latency: "42ms", ok: true },
  { chain: "Polygon", latency: "38ms", ok: true },
  { chain: "Arbitrum", latency: "51ms", ok: true },
  { chain: "Optimism", latency: "284ms", ok: false },
  { chain: "Ethereum", latency: "67ms", ok: true },
]

const volumeData = [
  { day: "Mon", vol: 18200 },
  { day: "Tue", vol: 22400 },
  { day: "Wed", vol: 19800 },
  { day: "Thu", vol: 27100 },
  { day: "Fri", vol: 24600 },
  { day: "Sat", vol: 16300 },
  { day: "Sun", vol: 19900 },
]

const chainVolume = [
  { chain: "Base", amount: "$42.1k", pct: 72 },
  { chain: "Polygon", amount: "$35.8k", pct: 61 },
  { chain: "Arbitrum", amount: "$28.4k", pct: 48 },
  { chain: "Optimism", amount: "$24.2k", pct: 41 },
  { chain: "Ethereum", amount: "$17.9k", pct: 30 },
]

const recentActivity = [
  { type: "Payment", desc: "Agent #12 → MerchantCo", amount: "$3,200.00", chain: "Base", status: "Completed", time: "2m ago" },
  { type: "Transfer", desc: "Agent #7 → Agent #19", amount: "$1,450.00", chain: "Polygon", status: "Pending", time: "5m ago" },
  { type: "Refund", desc: "MerchantCo → Agent #3", amount: "$280.00", chain: "Arbitrum", status: "Processing", time: "8m ago" },
]

const initialQuickStartSteps = [
  { label: "Create your first agent", done: true, icon: Rocket },
  { label: "Connect a wallet", done: true, icon: ShieldCheck },
  { label: "Set up merchant verification", done: false, icon: Users },
  { label: "Configure payment policies", done: false, icon: ShieldCheck },
]

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const statusDot: Record<string, string> = {
  success: "text-success",
  pending: "text-warning",
  failed: "text-destructive",
}

const statusBadgeVariant: Record<string, "success" | "warning" | "info"> = {
  Completed: "success",
  Pending: "warning",
  Processing: "info",
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function OverviewPage() {
  const [quickStartOpen, setQuickStartOpen] = useState(true)
  const [quickStartSteps, setQuickStartSteps] = useState(initialQuickStartSteps)
  const completedSteps = quickStartSteps.filter((s) => s.done).length

  // New Payment dialog
  const [newPaymentOpen, setNewPaymentOpen] = useState(false)
  const [paymentRecipient, setPaymentRecipient] = useState("")
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentChain, setPaymentChain] = useState("Base")

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

  return (
    <>
      {/* ---- Stats Row ---- */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 flex-1">
          <StatCard label="Active Agents" value="24" sub="+3 this week" positive />
          <StatCard label="24h Volume" value="$148,392" sub="+12.4%" positive />
          <StatCard label="Transactions" value="1,247" sub="today" />
          <StatCard label="Merchants" value="18" sub="16 verified" />
        </div>

        <div className="flex flex-wrap lg:flex-col gap-2 lg:justify-center">
          <StatusPill color="amber" label="3 Pending Approvals" />
          <StatusPill color="green" label="Kill Switch: Inactive" />
          <StatusPill color="blue" label="Multi-Agent Trust: 94%" />
        </div>
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
            <CardTitle>Live Transaction Feed</CardTitle>
            <CardDescription>10 transactions</CardDescription>
          </CardHeader>
          <CardContent className="divide-y">
            {transactions.map((tx, i) => (
              <ContextMenu key={i}>
                <ContextMenuTrigger>
                  <div className="flex items-center gap-3 py-3">
                    <Circle weight="fill" className={cn("h-1.5 w-1.5 flex-shrink-0", statusDot[tx.status])} />
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium truncate">{tx.desc}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <HoverCard>
                          <HoverCardTrigger>
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 font-mono cursor-pointer">{tx.txId}</Badge>
                          </HoverCardTrigger>
                          <HoverCardContent className="w-64">
                            <div className="space-y-1.5">
                              <p className="text-xs font-mono text-muted-foreground">{tx.txId}</p>
                              <p className="text-sm">{tx.desc}</p>
                              <div className="flex justify-between text-xs text-muted-foreground">
                                <span>{tx.chain}</span>
                                <span className="font-medium text-foreground">{tx.amount}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Circle weight="fill" className={cn("h-1.5 w-1.5", statusDot[tx.status])} />
                                <span className="text-xs capitalize">{tx.status}</span>
                              </div>
                            </div>
                          </HoverCardContent>
                        </HoverCard>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">{tx.chain}</Badge>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-[13px] font-medium tabular-nums">{tx.amount}</div>
                      <div className="text-[11px] text-muted-foreground">{tx.time}</div>
                    </div>
                  </div>
                </ContextMenuTrigger>
                <ContextMenuContent>
                  <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.txId); toast.success("Copied to clipboard") }}>Copy TX ID</ContextMenuItem>
                  <ContextMenuItem onClick={() => { navigator.clipboard.writeText(tx.chain); toast.success("Copied to clipboard") }}>Copy Chain</ContextMenuItem>
                  <ContextMenuSeparator />
                  <ContextMenuItem onClick={() => toast.info(`Viewing details for ${tx.txId}...`)}>View Transaction Details</ContextMenuItem>
                  <ContextMenuItem onClick={() => toast.info(`Opening ${tx.chain} block explorer...`)}>View on Explorer</ContextMenuItem>
                </ContextMenuContent>
              </ContextMenu>
            ))}
          </CardContent>
        </Card>

        {/* Right — 2x2 Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Payment Types Donut */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Payment Types</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center gap-4">
              <div className="w-24 h-24 flex-shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={28}
                      outerRadius={42}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {pieData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 text-[12px]">
                {pieData.map((d) => (
                  <div key={d.name} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }} />
                    <span className="text-muted-foreground">{d.name}</span>
                    <span className="font-medium ml-auto">{d.value}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Network Health */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Network Health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {networkHealth.map((n) => (
                <ContextMenu key={n.chain}>
                  <ContextMenuTrigger>
                    <div className="flex items-center gap-2.5 text-[13px]">
                      <Circle
                        weight="fill"
                        className={cn("h-1.5 w-1.5 flex-shrink-0", n.ok ? "text-success" : "text-warning")}
                      />
                      <span className="flex-1">{n.chain}</span>
                      <span className={cn(
                        "tabular-nums font-mono text-[12px]",
                        n.ok ? "text-muted-foreground" : "text-warning font-medium"
                      )}>
                        {n.latency}
                      </span>
                    </div>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(n.chain); toast.success("Copied to clipboard") }}>Copy Chain Name</ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => toast.info(`Viewing ${n.chain} status...`)}>View Chain Status</ContextMenuItem>
                    <ContextMenuItem onClick={() => toast.info(`Opening ${n.chain} block explorer...`)}>Open Block Explorer</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </CardContent>
          </Card>

          {/* 7-Day Volume */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>7-Day Volume</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-28">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={volumeData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="volGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--chart-5)" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="var(--chart-5)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11 }} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid var(--border)", background: "var(--card)" }}
                      formatter={(v) => [`$${Number(v).toLocaleString()}`, "Volume"]}
                    />
                    <Area type="monotone" dataKey="vol" stroke="var(--chart-5)" fill="url(#volGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Volume by Chain */}
          <Card size="sm">
            <CardHeader>
              <CardTitle>Volume by Chain</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {chainVolume.map((c) => (
                <div key={c.chain} className="space-y-1">
                  <div className="flex items-center justify-between text-[12px]">
                    <span>{c.chain}</span>
                    <span className="text-muted-foreground tabular-nums">{c.amount}</span>
                  </div>
                  <Progress value={c.pct} className="h-1.5" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ---- Recent Activity ---- */}
      <Card size="sm">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto -mx-4 sm:mx-0">
            <Table className="min-w-[600px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Chain</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentActivity.map((row, i) => (
                  <ContextMenu key={i}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="font-medium">{row.type}</TableCell>
                      <TableCell className="text-muted-foreground truncate max-w-[200px]">{row.desc}</TableCell>
                      <TableCell className="text-right tabular-nums">{row.amount}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">{row.chain}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusBadgeVariant[row.status]}>
                          {row.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground">{row.time}</TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(row.desc); toast.success("Copied to clipboard") }}>Copy Description</ContextMenuItem>
                      <ContextMenuItem onClick={() => { navigator.clipboard.writeText(row.amount); toast.success("Copied to clipboard") }}>Copy Amount</ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem onClick={() => toast.info(`Viewing transaction details...`)}>View Transaction Details</ContextMenuItem>
                      <ContextMenuItem onClick={() => toast.info(`Opening ${row.chain} block explorer...`)}>View on Explorer</ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

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
