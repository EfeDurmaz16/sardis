import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import SardisLogo from "../components/SardisLogo";

// Mock data
const AGENTS = [
  {
    id: "agent_shopping_01",
    name: "Shopping Agent",
    status: "active",
    wallet: "0x7a3b…f92e",
    balance: 847.52,
    spent_today: 152.48,
    daily_limit: 1000,
    policy: "Max $200/tx, only SaaS + retail",
    last_active: "2 min ago",
  },
  {
    id: "agent_infra_02",
    name: "Infrastructure Agent",
    status: "active",
    wallet: "0x9c4d…a31b",
    balance: 3241.0,
    spent_today: 759.0,
    daily_limit: 5000,
    policy: "Max $500/tx, cloud providers only",
    last_active: "30 sec ago",
  },
  {
    id: "agent_research_03",
    name: "Research Agent",
    status: "paused",
    wallet: "0x2f8e…c67d",
    balance: 125.0,
    spent_today: 0,
    daily_limit: 200,
    policy: "Max $50/tx, API services only",
    last_active: "1 hour ago",
  },
];

const TRANSACTIONS = [
  { id: "tx_001", agent: "Shopping Agent", merchant: "OpenAI", amount: 45.0, status: "completed", time: "2 min ago", type: "API Credits" },
  { id: "tx_002", agent: "Infrastructure Agent", amount: 234.5, merchant: "AWS", status: "completed", time: "5 min ago", type: "Compute" },
  { id: "tx_003", agent: "Shopping Agent", amount: 12.99, merchant: "Notion", status: "completed", time: "12 min ago", type: "SaaS" },
  { id: "tx_004", agent: "Infrastructure Agent", amount: 89.0, merchant: "Vercel", status: "completed", time: "18 min ago", type: "Hosting" },
  { id: "tx_005", agent: "Research Agent", amount: 150.0, merchant: "Anthropic", status: "blocked", time: "1 hour ago", type: "API Credits" },
  { id: "tx_006", agent: "Infrastructure Agent", amount: 435.5, merchant: "GCP", status: "completed", time: "2 hours ago", type: "Compute" },
  { id: "tx_007", agent: "Shopping Agent", amount: 29.0, merchant: "GitHub", status: "completed", time: "3 hours ago", type: "Developer Tools" },
  { id: "tx_008", agent: "Shopping Agent", amount: 65.49, merchant: "Figma", status: "pending_approval", time: "3 hours ago", type: "Design Tools" },
];

const POLICY_EVENTS = [
  { type: "blocked", message: "Research Agent exceeded $50/tx limit ($150 attempted)", time: "1 hour ago" },
  { type: "approval", message: "Shopping Agent requesting $65.49 for Figma — awaiting human approval", time: "3 hours ago" },
  { type: "warning", message: "Infrastructure Agent at 76% of daily limit ($3,800/$5,000)", time: "4 hours ago" },
  { type: "info", message: "Shopping Agent policy updated: added 'design tools' to allowed categories", time: "6 hours ago" },
];

function BarChart({ value, max, color = "var(--sardis-orange)" }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="w-full h-2 bg-muted overflow-hidden">
      <div
        className="h-full transition-all duration-500"
        style={{ width: `${pct}%`, backgroundColor: pct > 90 ? "#dc2626" : color }}
      />
    </div>
  );
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  const totalBalance = AGENTS.reduce((s, a) => s + a.balance, 0);
  const totalSpent = AGENTS.reduce((s, a) => s + a.spent_today, 0);
  const activeAgents = AGENTS.filter((a) => a.status === "active").length;

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Top bar */}
      <header className="border-b border-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg font-display">
            <SardisLogo size="small" />
            <span>Sardis</span>
          </Link>
          <div className="hidden md:flex items-center gap-1 text-sm font-mono">
            {["overview", "agents", "transactions", "policies"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-4 py-2 transition-colors capitalize",
                  activeTab === tab
                    ? "text-[var(--sardis-orange)] border-b-2 border-[var(--sardis-orange)]"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="rounded-none font-mono text-xs border-emerald-600 text-emerald-600">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 animate-pulse" />
            SIMULATED
          </Badge>
          <Button variant="outline" className="rounded-none text-sm" asChild>
            <Link to="/docs">Docs</Link>
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Summary cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "TOTAL BALANCE", value: `$${totalBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, sub: "across all wallets" },
            { label: "SPENT TODAY", value: `$${totalSpent.toLocaleString("en-US", { minimumFractionDigits: 2 })}`, sub: `${TRANSACTIONS.filter((t) => t.status === "completed").length} transactions` },
            { label: "ACTIVE AGENTS", value: activeAgents.toString(), sub: `${AGENTS.length} total` },
            { label: "POLICY BLOCKS", value: "1", sub: "last 24 hours", alert: true },
          ].map((stat, i) => (
            <div key={i} className={cn("p-5 border transition-colors", stat.alert ? "border-destructive/50 bg-destructive/5" : "border-border")}>
              <div className="text-[10px] font-bold tracking-[0.2em] text-muted-foreground mb-1 font-mono">{stat.label}</div>
              <div className={cn("text-2xl font-bold font-display", stat.alert && "text-destructive")}>{stat.value}</div>
              <div className="text-xs text-muted-foreground font-mono mt-1">{stat.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left column: Agent cards */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold font-display">Agent Wallets</h2>
              <span className="text-xs text-muted-foreground font-mono">Live balances</span>
            </div>

            {AGENTS.map((agent) => (
              <Card key={agent.id} className="rounded-none border-border hover:border-[var(--sardis-orange)] transition-colors">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold font-display">{agent.name}</h3>
                        <Badge
                          variant="outline"
                          className={cn(
                            "rounded-none text-[10px] font-mono",
                            agent.status === "active"
                              ? "border-emerald-600 text-emerald-600"
                              : "border-yellow-600 text-yellow-600"
                          )}
                        >
                          {agent.status.toUpperCase()}
                        </Badge>
                      </div>
                      <code className="text-xs text-muted-foreground">{agent.wallet}</code>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold font-display">${agent.balance.toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
                      <div className="text-xs text-muted-foreground font-mono">{agent.last_active}</div>
                    </div>
                  </div>

                  {/* Spending bar */}
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-muted-foreground font-mono mb-1">
                      <span>Daily spend: ${agent.spent_today.toFixed(2)}</span>
                      <span>Limit: ${agent.daily_limit.toLocaleString()}</span>
                    </div>
                    <BarChart value={agent.spent_today} max={agent.daily_limit} />
                  </div>

                  {/* Policy */}
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-mono">Policy:</span>
                    <span className="text-foreground font-mono">{agent.policy}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Right column: Activity feed */}
          <div className="space-y-6">
            {/* Recent transactions */}
            <div>
              <h2 className="text-lg font-semibold font-display mb-3">Recent Transactions</h2>
              <div className="border border-border divide-y divide-border">
                {TRANSACTIONS.slice(0, 6).map((tx) => (
                  <div key={tx.id} className="px-4 py-3 hover:bg-muted/50 transition-colors">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{tx.merchant}</span>
                      <span className={cn(
                        "text-sm font-mono font-bold",
                        tx.status === "blocked" ? "text-destructive" : "text-foreground"
                      )}>
                        {tx.status === "blocked" ? "BLOCKED" : `-$${tx.amount.toFixed(2)}`}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground font-mono">{tx.agent}</span>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            "rounded-none text-[10px] font-mono",
                            tx.status === "completed" && "border-emerald-600/30 text-emerald-600",
                            tx.status === "blocked" && "border-destructive/30 text-destructive",
                            tx.status === "pending_approval" && "border-yellow-600/30 text-yellow-600"
                          )}
                        >
                          {tx.status === "pending_approval" ? "PENDING" : tx.status.toUpperCase()}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground font-mono">{tx.time}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Policy events */}
            <div>
              <h2 className="text-lg font-semibold font-display mb-3">Policy Events</h2>
              <div className="space-y-2">
                {POLICY_EVENTS.map((event, i) => (
                  <div
                    key={i}
                    className={cn(
                      "px-4 py-3 border text-sm",
                      event.type === "blocked" && "border-destructive/30 bg-destructive/5",
                      event.type === "approval" && "border-yellow-600/30 bg-yellow-500/5",
                      event.type === "warning" && "border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5",
                      event.type === "info" && "border-border"
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <span className={cn(
                        "text-[10px] font-bold font-mono tracking-wider mt-0.5 shrink-0",
                        event.type === "blocked" && "text-destructive",
                        event.type === "approval" && "text-yellow-600",
                        event.type === "warning" && "text-[var(--sardis-orange)]",
                        event.type === "info" && "text-muted-foreground"
                      )}>
                        {event.type.toUpperCase()}
                      </span>
                      <p className="text-muted-foreground leading-snug">{event.message}</p>
                    </div>
                    <div className="text-[10px] text-muted-foreground font-mono mt-1 pl-12">{event.time}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Approval queue */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold font-display mb-3">Pending Approvals</h2>
          <div className="border border-yellow-600/30 bg-yellow-500/5 p-5">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="outline" className="rounded-none text-[10px] font-mono border-yellow-600/30 text-yellow-600">AWAITING APPROVAL</Badge>
                  <span className="text-sm font-semibold">Shopping Agent</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  $65.49 to <strong className="text-foreground">Figma</strong> — Design Tools subscription renewal
                </p>
                <code className="text-xs text-muted-foreground mt-1 block">tx_008 &middot; 3 hours ago</code>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="rounded-none border-destructive text-destructive hover:bg-destructive hover:text-white">
                  Reject
                </Button>
                <Button size="sm" className="rounded-none bg-emerald-600 hover:bg-emerald-700 text-white">
                  Approve
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom note */}
        <div className="mt-8 p-4 border border-border text-center">
          <p className="text-xs text-muted-foreground font-mono">
            Dashboard is running in <strong>simulated mode</strong>. Data shown is synthetic.
            <Link to="/docs/quickstart" className="text-[var(--sardis-orange)] hover:underline ml-1">Connect a live API key</Link> to see real agent activity.
          </p>
        </div>
      </main>
    </div>
  );
}
