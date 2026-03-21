import { useState } from 'react'
import {
  Users,
  ArrowRightLeft,
  DollarSign,
  Wallet,
  Activity,
  TrendingUp,
  Zap,
  Globe,
  Shield,
  Clock,
  AlertTriangle,
  BarChart2,
  Rocket,
  X,
  Key,
  FlaskConical,
  ChevronRight
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import clsx from 'clsx'
import StatCard from '../components/StatCard'
import KYCBanner from '../components/KYCBanner'
import { FaucetButton } from '../components/FaucetButton'
import { OnboardingChecklist } from '../components/OnboardingChecklist'
import { useAgents, useMerchants, useWebhooks, useHealth, useTransactions, usePendingApprovals, useKillSwitchStatus, useBillingAccount, useDashboardMetrics } from '../hooks/useApi'
import type { Transaction } from '../types'

// Static chart structure — populated with real data when available, empty-state otherwise
const VOLUME_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const transactionsByChain = [
  { chain: 'Base', count: 0, color: '#0052FF' },
  { chain: 'Polygon', count: 0, color: '#8247E5' },
  { chain: 'Arbitrum', count: 0, color: '#28A0F0' },
  { chain: 'Optimism', count: 0, color: '#FF0420' },
  { chain: 'Ethereum', count: 0, color: '#627EEA' },
]

const paymentTypes = [
  { name: 'Agent → Merchant', value: 45, color: '#ff4f00' },
  { name: 'Agent → Agent', value: 30, color: '#3b82f6' },
  { name: 'Holds/Pre-auth', value: 15, color: '#f59e0b' },
  { name: 'Refunds', value: 10, color: '#ef4444' },
]

function formatAmount(amount: string): string {
  const n = parseFloat(amount)
  if (isNaN(n)) return amount
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes === 1) return '1 min ago'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours === 1) return '1 hr ago'
  if (hours < 24) return `${hours} hrs ago`
  return `${Math.floor(hours / 24)}d ago`
}

function compute24hVolume(transactions: Transaction[]): number {
  const cutoff = Date.now() - 86400000
  return transactions
    .filter(tx => new Date(tx.created_at).getTime() > cutoff && tx.status === 'completed')
    .reduce((sum, tx) => sum + parseFloat(tx.amount || '0'), 0)
}

function buildVolumeChartData(transactions: Transaction[]) {
  // Build last-7-days volume from real transactions
  const now = new Date()
  return VOLUME_DAYS.map((day, i) => {
    const dayOffset = 6 - i
    const start = new Date(now)
    start.setDate(start.getDate() - dayOffset)
    start.setHours(0, 0, 0, 0)
    const end = new Date(start)
    end.setHours(23, 59, 59, 999)

    const dayTxs = transactions.filter(tx => {
      const d = new Date(tx.created_at).getTime()
      return d >= start.getTime() && d <= end.getTime() && tx.status === 'completed'
    })

    const value = dayTxs.reduce((sum, tx) => sum + parseFloat(tx.amount || '0'), 0)
    return { date: day, value: Math.round(value * 100) / 100, transactions: dayTxs.length }
  })
}

function deriveTransactionType(tx: Transaction): string {
  if (tx.purpose) {
    const p = tx.purpose.toLowerCase()
    if (p.includes('refund')) return 'refund'
    if (p.includes('hold')) return 'hold'
  }
  return 'payment'
}

function QuickStartCard({ transactionCount }: { transactionCount: number }) {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem('sardis_quickstart_dismissed') === '1');

  if (dismissed || transactionCount >= 3) return null;

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem('sardis_quickstart_dismissed', '1');
  };

  const steps = [
    { label: 'Create your first wallet', href: '/agents', icon: Wallet, color: '#818CF8' },
    { label: 'Set a spending policy', href: '/policy-management', icon: Shield, color: '#22C55E' },
    { label: 'Make a test payment', href: '/simulation', icon: FlaskConical, color: '#F59E0B' },
    { label: 'View your API keys', href: '/api-keys', icon: Key, color: '#60A5FA' },
  ];

  return (
    <div className="rounded-xl p-5 relative" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(79,70,229,0.04) 100%)', border: '1px solid rgba(99,102,241,0.2)' }}>
      <button onClick={handleDismiss} className="absolute top-3 right-3 text-gray-500 hover:text-white transition-colors">
        <X size={16} />
      </button>
      <div className="flex items-center gap-2 mb-3">
        <Rocket size={18} color="#818CF8" />
        <h3 className="text-sm font-semibold text-white">Quick Start</h3>
      </div>
      <p className="text-xs text-gray-400 mb-4">Get up and running in minutes. Complete these steps to start processing payments.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {steps.map((step, i) => (
          <Link
            key={step.label}
            to={step.href}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0" style={{ background: `${step.color}20` }}>
              <span className="text-xs font-bold" style={{ color: step.color }}>{i + 1}</span>
            </div>
            <span className="text-xs text-gray-300 group-hover:text-white transition-colors flex-1">{step.label}</span>
            <ChevronRight size={12} className="text-gray-600 group-hover:text-gray-400 transition-colors" />
          </Link>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: agents = [] } = useAgents()
  const { data: merchants = [] } = useMerchants()
  const { data: webhooks = [] } = useWebhooks()
  const { data: health } = useHealth()
  const { data: transactions = [], isLoading: txLoading } = useTransactions(50)
  const { data: pendingApprovals = [] } = usePendingApprovals()
  const { data: killSwitchStatus } = useKillSwitchStatus()
  const { data: billing, isError: billingError } = useBillingAccount()
  const { data: metrics } = useDashboardMetrics()

  const activeAgents = metrics?.active_agents ?? agents.filter((agent) => agent.is_active).length

  // Compute real stats from transactions — prefer metrics endpoint when available
  const volume24h = metrics?.volume_24h ?? compute24hVolume(transactions)
  const volumeChartData = buildVolumeChartData(transactions)

  // Kill switch: check if global switch or any rail is active
  const killSwitchActive = Boolean(
    killSwitchStatus?.global ||
    Object.values(killSwitchStatus?.rails ?? {}).some(Boolean) ||
    Object.values(killSwitchStatus?.chains ?? {}).some(Boolean)
  )

  // Live feed: most recent 10 transactions
  const feedTransactions = transactions.slice(0, 10)

  // Recent activity table: first 5
  const recentActivity = transactions.slice(0, 5)

  return (
    <div className="space-y-8">
      {/* KYC verification banner */}
      <KYCBanner />

      {/* Onboarding Checklist — shown for test environments */}
      <OnboardingChecklist />

      {/* Quick Start Card — shown for new users */}
      <QuickStartCard transactionCount={transactions.length} />

      {/* Header with Live Indicator */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Monitor your AI agent payment network
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <div className={clsx(
              "w-2 h-2 rounded-full",
              health?.status === 'ok' ? "bg-sardis-500 animate-pulse" : "bg-yellow-500"
            )} />
            <span className="text-sm text-gray-400">
              {health?.status === 'ok' ? 'Live' : health ? health.status : 'Connecting'}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-white mono-numbers">
              {transactions.length > 0 ? `${transactions.length} tx` : '— tx'}
            </span>
          </div>
          <FaucetButton />
        </div>
      </div>

      {/* Runtime security posture */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4 border border-dark-100">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Pending Approvals</p>
          <p className={clsx(
            "text-sm font-medium",
            pendingApprovals.length > 0 ? "text-yellow-400" : "text-white"
          )}>
            {pendingApprovals.length > 0
              ? `${pendingApprovals.length} pending approval${pendingApprovals.length !== 1 ? 's' : ''}`
              : 'No pending approvals'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {pendingApprovals.length > 0
              ? 'Distinct reviewer (4-eyes) required on high-risk approvals.'
              : 'All approvals cleared. Distinct reviewer (4-eyes) on high-risk.'}
          </p>
        </div>
        <div className="card p-4 border border-dark-100">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Kill Switch</p>
          <div className="flex items-center gap-2">
            {killSwitchActive && <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />}
            <p className={clsx(
              "text-sm font-medium",
              killSwitchActive ? "text-red-400" : "text-white"
            )}>
              Kill switch {killSwitchActive ? 'active' : 'inactive'}
            </p>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {killSwitchActive
              ? 'One or more rails or chains are currently halted.'
              : 'All payment rails and chains operational.'}
          </p>
        </div>
        <div className="card p-4 border border-dark-100">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Multi-Agent Trust</p>
          <p className="text-sm text-white font-medium">Wallet-aware peer directory</p>
          <p className="text-xs text-gray-400 mt-1">Trusted broadcast targets visible for orchestration fan-out.</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Agents"
          value={metrics?.total_agents ?? agents.length ?? 0}
          change={`${activeAgents} online`}
          changeType="positive"
          icon={<Users className="w-6 h-6" />}
        />
        <StatCard
          title="Volume (24h)"
          value={volume24h > 0
            ? `$${volume24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : '—'}
          change={volume24h > 0 ? 'last 24 hours' : 'no completed transactions'}
          changeType={volume24h > 0 ? 'positive' : 'neutral'}
          icon={<DollarSign className="w-6 h-6" />}
        />
        <StatCard
          title="Transactions"
          value={(metrics?.total_transactions ?? transactions.length) > 0
            ? (metrics?.total_transactions ?? transactions.length)
            : '—'}
          change={(metrics?.total_transactions ?? transactions.length) > 0
            ? `${metrics?.completed_transactions ?? transactions.filter(t => t.status === 'completed').length} completed`
            : 'no data yet'}
          changeType={(metrics?.total_transactions ?? transactions.length) > 0 ? 'positive' : 'neutral'}
          icon={<ArrowRightLeft className="w-6 h-6" />}
        />
        <StatCard
          title="Merchants"
          value={metrics?.total_merchants ?? merchants.length ?? 0}
          change={`${metrics?.total_webhooks ?? webhooks.length} webhooks`}
          changeType="neutral"
          icon={<Wallet className="w-6 h-6" />}
        />
      </div>

      {/* Live Transaction Feed + Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Feed */}
        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Live Transaction Feed</h2>
            </div>
            <span className="text-xs text-gray-500">
              {txLoading ? 'Loading...' : 'Most recent transactions'}
            </span>
          </div>

          <div className="space-y-2 max-h-[320px] overflow-y-auto custom-scrollbar">
            {txLoading ? (
              <div className="text-center py-8 text-gray-500">
                Loading transactions...
              </div>
            ) : feedTransactions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No transactions yet
              </div>
            ) : (
              feedTransactions.map((tx, i) => (
                <div
                  key={tx.tx_id}
                  className={clsx(
                    "flex items-center justify-between p-3 rounded-lg transition-all duration-500",
                    i === 0 ? "bg-sardis-500/10 border border-sardis-500/30" : "bg-dark-200/50"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      "w-2 h-2 rounded-full",
                      tx.status === 'completed' ? 'bg-sardis-500' :
                      tx.status === 'pending' ? 'bg-yellow-500 animate-pulse' :
                      'bg-red-500'
                    )} />
                    <div>
                      <p className="text-sm font-medium text-white font-mono truncate max-w-[140px]">
                        {tx.from_wallet}
                      </p>
                      <p className="text-xs text-gray-500 truncate max-w-[140px]">
                        {tx.purpose || `→ ${tx.to_wallet}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs px-2 py-0.5 bg-dark-300 text-gray-400 rounded">
                      {tx.currency}
                    </span>
                    <div className="text-right">
                      <p className="text-sm font-medium text-sardis-400 mono-numbers">
                        {formatAmount(tx.amount)}
                      </p>
                      <p className="text-xs text-gray-500">{formatRelativeTime(tx.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          {/* Payment Types Pie */}
          <div className="card p-6">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Payment Types</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={paymentTypes}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {paymentTypes.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#1f1e1c',
                      border: '1px solid #2f2e2c',
                      borderRadius: '0px',
                      fontSize: '12px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {paymentTypes.map((type, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: type.color }} />
                  <span className="text-xs text-gray-400">{type.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Network Health */}
          <div className="card p-6">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Network Health</h3>
            <div className="space-y-2.5 max-h-[200px] overflow-y-auto custom-scrollbar">
              {transactionsByChain.map((chain) => {
                const isHalted = Boolean(killSwitchStatus?.chains?.[chain.chain.toLowerCase()])
                return (
                  <div key={chain.chain} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-sardis-400" />
                      <span className="text-sm text-gray-300">{chain.chain}</span>
                    </div>
                    {isHalted ? (
                      <span className="badge badge-danger">Halted</span>
                    ) : (
                      <span className="badge badge-success">Healthy</span>
                    )}
                  </div>
                )
              })}
              <div className="flex items-center justify-between pt-2 border-t border-dark-100">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-gray-300">Risk Engine</span>
                </div>
                <span className={clsx(
                  "badge",
                  health?.status === 'ok' ? "badge-info" : "badge-warning"
                )}>
                  {health?.status === 'ok' ? 'Active' : 'Checking'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volume Chart */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Transaction Volume</h2>
              <p className="text-sm text-gray-400">Last 7 days</p>
            </div>
            <div className="flex items-center gap-2 text-sardis-400">
              <TrendingUp className="w-5 h-5" />
              <span className="text-sm font-medium">
                {volumeChartData.some(d => d.value > 0) ? 'Live data' : 'No data yet'}
              </span>
            </div>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeChartData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ff4f00" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ff4f00" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" />
                <XAxis
                  dataKey="date"
                  stroke="#444341"
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis
                  stroke="#444341"
                  fontSize={12}
                  tickLine={false}
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1f1e1c',
                    border: '1px solid #2f2e2c',
                    borderRadius: '0px'
                  }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#ff4f00"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorValue)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Transactions by Chain */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">By Chain</h2>
              <p className="text-sm text-gray-400">Transaction distribution</p>
            </div>
            <Activity className="w-5 h-5 text-gray-400" />
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={transactionsByChain} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" horizontal={false} />
                <XAxis type="number" stroke="#444341" fontSize={12} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="chain"
                  stroke="#444341"
                  fontSize={12}
                  tickLine={false}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1f1e1c',
                    border: '1px solid #2f2e2c',
                    borderRadius: '0px'
                  }}
                  cursor={{ fill: 'rgba(255, 79, 0, 0.1)' }}
                />
                <Bar
                  dataKey="count"
                  fill="#ff4f00"
                  radius={[0, 0, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Usage Quota Widget */}
      {!billingError && billing && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Usage</h2>
            </div>
            <div className="flex items-center gap-3">
              <span className={clsx(
                "px-2.5 py-0.5 rounded text-xs font-medium uppercase tracking-wide",
                billing.plan === 'free' && "bg-gray-700 text-gray-300",
                billing.plan === 'starter' && "bg-blue-500/20 text-blue-400",
                billing.plan === 'growth' && "bg-purple-500/20 text-purple-400",
                billing.plan === 'enterprise' && "bg-sardis-500/20 text-sardis-400",
                !['free', 'starter', 'growth', 'enterprise'].includes(billing.plan) && "bg-gray-700 text-gray-300"
              )}>
                {billing.plan}
              </span>
              {(() => {
                const u = billing.usage
                const apiPct = u.api_calls_limit ? u.api_calls_used / u.api_calls_limit * 100 : 0
                const volPct = u.tx_volume_limit_cents ? u.tx_volume_cents / u.tx_volume_limit_cents * 100 : 0
                const agentPct = u.agents_limit ? u.agents_used / u.agents_limit * 100 : 0
                const anyHigh = Math.max(apiPct, volPct, agentPct) > 80
                return anyHigh ? (
                  <Link
                    to="/billing"
                    className="text-xs font-medium text-sardis-400 hover:text-sardis-300 border border-sardis-500/40 hover:border-sardis-400 px-2.5 py-0.5 rounded transition-colors"
                  >
                    Upgrade
                  </Link>
                ) : null
              })()}
            </div>
          </div>

          <div className="space-y-5">
            {/* API Calls */}
            {(() => {
              const used = billing.usage.api_calls_used
              const limit = billing.usage.api_calls_limit
              const pct = limit ? Math.min(used / limit * 100, 100) : 0
              const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-400' : 'bg-sardis-500'
              const textColor = pct >= 90 ? 'text-red-400' : pct >= 70 ? 'text-amber-400' : 'text-sardis-400'
              return (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-gray-400">API Calls</span>
                    <span className={clsx("text-sm font-medium mono-numbers", limit ? textColor : "text-gray-500")}>
                      {limit
                        ? `${used.toLocaleString()} / ${limit.toLocaleString()} (${Math.round(pct)}%)`
                        : `${used.toLocaleString()} / Unlimited`}
                    </span>
                  </div>
                  <div className="h-1.5 bg-dark-100 rounded-full overflow-hidden">
                    {limit && (
                      <div
                        className={clsx("h-full rounded-full transition-all", color)}
                        style={{ width: `${pct}%` }}
                      />
                    )}
                  </div>
                </div>
              )
            })()}

            {/* Transaction Volume */}
            {(() => {
              const usedCents = billing.usage.tx_volume_cents
              const limitCents = billing.usage.tx_volume_limit_cents
              const pct = limitCents ? Math.min(usedCents / limitCents * 100, 100) : 0
              const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-400' : 'bg-sardis-500'
              const textColor = pct >= 90 ? 'text-red-400' : pct >= 70 ? 'text-amber-400' : 'text-sardis-400'
              const fmt = (cents: number) =>
                `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              return (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-gray-400">Transaction Volume</span>
                    <span className={clsx("text-sm font-medium mono-numbers", limitCents ? textColor : "text-gray-500")}>
                      {limitCents
                        ? `${fmt(usedCents)} / ${fmt(limitCents)} (${Math.round(pct)}%)`
                        : `${fmt(usedCents)} / Unlimited`}
                    </span>
                  </div>
                  <div className="h-1.5 bg-dark-100 rounded-full overflow-hidden">
                    {limitCents && (
                      <div
                        className={clsx("h-full rounded-full transition-all", color)}
                        style={{ width: `${pct}%` }}
                      />
                    )}
                  </div>
                </div>
              )
            })()}

            {/* Agents */}
            {(() => {
              const used = billing.usage.agents_used
              const limit = billing.usage.agents_limit
              const pct = limit ? Math.min(used / limit * 100, 100) : 0
              const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-400' : 'bg-sardis-500'
              const textColor = pct >= 90 ? 'text-red-400' : pct >= 70 ? 'text-amber-400' : 'text-sardis-400'
              return (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm text-gray-400">Agents</span>
                    <span className={clsx("text-sm font-medium mono-numbers", limit ? textColor : "text-gray-500")}>
                      {limit
                        ? `${used} / ${limit} (${Math.round(pct)}%)`
                        : `${used} / Unlimited`}
                    </span>
                  </div>
                  <div className="h-1.5 bg-dark-100 rounded-full overflow-hidden">
                    {limit && (
                      <div
                        className={clsx("h-full rounded-full transition-all", color)}
                        style={{ width: `${pct}%` }}
                      />
                    )}
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
          <button className="text-sm text-sardis-400 hover:text-sardis-300">View all →</button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase">
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Wallet</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Amount</th>
                <th className="pb-3 font-medium">Currency</th>
                <th className="pb-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {txLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500 text-sm">
                    Loading transactions...
                  </td>
                </tr>
              ) : recentActivity.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-500 text-sm">
                    No transactions yet
                  </td>
                </tr>
              ) : (
                recentActivity.map((tx) => (
                  <tr key={tx.tx_id} className="hover:bg-dark-200/50 transition-colors">
                    <td className="py-3">
                      <span className={clsx(
                        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium",
                        tx.status === 'completed' && "bg-sardis-500/10 text-sardis-400",
                        tx.status === 'pending' && "bg-yellow-500/10 text-yellow-500",
                        tx.status === 'failed' && "bg-red-500/10 text-red-400"
                      )}>
                        <div className={clsx(
                          "w-1.5 h-1.5 rounded-full",
                          tx.status === 'completed' && "bg-sardis-500",
                          tx.status === 'pending' && "bg-yellow-500 animate-pulse",
                          tx.status === 'failed' && "bg-red-500"
                        )} />
                        {tx.status}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-sm text-white font-mono truncate max-w-[140px] block">
                        {tx.from_wallet}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-sm text-gray-400 capitalize">
                        {deriveTransactionType(tx)}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-sm text-sardis-400 font-medium mono-numbers">
                        {formatAmount(tx.amount)}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-xs px-2 py-0.5 bg-dark-200 text-gray-400 rounded">
                        {tx.currency}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="text-sm text-gray-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatRelativeTime(tx.created_at)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
