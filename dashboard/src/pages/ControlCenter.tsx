import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Activity,
  Lock,
  Clock,
  Power,
  ExternalLink,
  TrendingDown,
  Zap,
  RefreshCw,
} from 'lucide-react'
import clsx from 'clsx'
import {
  usePendingApprovals,
  useApprovals,
  useApproveApproval,
  useDenyApproval,
  useKillSwitchStatus,
  useTransactions,
  useHealth,
} from '../hooks/useApi'
import type { Transaction } from '../types'

/* ─── Types ─── */

interface ApiApproval {
  id: string
  agent_id: string
  action: string
  amount: string
  token: string
  destination: string
  urgency: 'low' | 'medium' | 'high' | 'critical'
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'cancelled'
  created_at: string
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
}

/* ─── Helpers ─── */

function formatTimeAgo(isoString: string): string {
  const now = Date.now()
  const timestamp = new Date(isoString).getTime()
  const diffMinutes = Math.floor((now - timestamp) / 60000)
  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`
  return `${Math.floor(diffMinutes / 1440)}d ago`
}

function formatAmount(amount: string): string {
  const n = parseFloat(amount)
  if (isNaN(n)) return amount
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function normalizeRisk(urgency: string): 'low' | 'medium' | 'high' {
  if (urgency === 'critical' || urgency === 'high') return 'high'
  if (urgency === 'medium') return 'medium'
  return 'low'
}

function txRiskFromStatus(status: string): 'low' | 'medium' | 'high' {
  if (status === 'failed') return 'high'
  if (status === 'pending') return 'medium'
  return 'low'
}

/* ─── Top Stats Row ─── */

interface TopStatsProps {
  pendingCount: number
  txToday: number
  denialRate: string
  healthStatus: string
}

function TopStats({ pendingCount, txToday, denialRate, healthStatus }: TopStatsProps) {
  const healthColor =
    healthStatus === 'ok'
      ? 'text-sardis-400'
      : healthStatus === 'degraded'
      ? 'text-yellow-400'
      : 'text-red-400'

  const healthDot =
    healthStatus === 'ok'
      ? 'bg-sardis-500'
      : healthStatus === 'degraded'
      ? 'bg-yellow-500'
      : 'bg-red-500'

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Pending Approvals */}
      <div className="bg-dark-300 border border-dark-100 p-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Pending Approvals</p>
          <p className={clsx('text-2xl font-bold', pendingCount > 0 ? 'text-yellow-400' : 'text-white')}>
            {pendingCount}
          </p>
        </div>
        {pendingCount > 0 ? (
          <span className="px-2 py-0.5 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-bold animate-pulse">
            NEEDS ACTION
          </span>
        ) : (
          <CheckCircle2 className="w-6 h-6 text-sardis-500 opacity-60" />
        )}
      </div>

      {/* Transactions Today */}
      <div className="bg-dark-300 border border-dark-100 p-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Transactions Today</p>
          <p className="text-2xl font-bold text-white">{txToday}</p>
        </div>
        <Activity className="w-6 h-6 text-sardis-500 opacity-60" />
      </div>

      {/* Denial Rate */}
      <div className="bg-dark-300 border border-dark-100 p-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Denial Rate (24h)</p>
          <p className={clsx('text-2xl font-bold', denialRate !== '0%' ? 'text-yellow-400' : 'text-white')}>
            {denialRate}
          </p>
        </div>
        <TrendingDown className="w-6 h-6 text-gray-500 opacity-60" />
      </div>

      {/* System Health */}
      <div className="bg-dark-300 border border-dark-100 p-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">System Health</p>
          <p className={clsx('text-2xl font-bold capitalize', healthColor)}>
            {healthStatus || 'Unknown'}
          </p>
        </div>
        <div className="relative">
          <div className={clsx('w-4 h-4', healthDot)} />
          {healthStatus === 'ok' && (
            <div className="absolute inset-0 bg-sardis-500 animate-ping opacity-40" />
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── Action Queue (Left Column) ─── */

interface ActionQueueProps {
  pending: ApiApproval[]
  isLoading: boolean
  isError: boolean
  actionLoadingIds: Set<string>
  onApprove: (id: string) => void
  onDeny: (id: string) => void
}

function ActionQueue({
  pending,
  isLoading,
  isError,
  actionLoadingIds,
  onApprove,
  onDeny,
}: ActionQueueProps) {
  const top5 = pending.slice(0, 5)

  return (
    <div className="bg-dark-300 border border-dark-100 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-dark-100">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-yellow-400" />
          <h2 className="text-sm font-semibold text-white">Action Queue</h2>
          {pending.length > 0 && (
            <span className="px-1.5 py-0.5 bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 text-xs font-bold">
              {pending.length}
            </span>
          )}
        </div>
        <Link
          to="/approvals"
          className="text-xs text-sardis-400 hover:text-sardis-300 flex items-center gap-1 transition-colors"
        >
          View all
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isError ? (
          <div className="flex flex-col items-center justify-center py-10 text-red-400 gap-2">
            <XCircle className="w-8 h-8 opacity-50" />
            <p className="text-xs">Failed to load approvals</p>
          </div>
        ) : isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-500 gap-2">
            <RefreshCw className="w-6 h-6 animate-spin opacity-50" />
            <p className="text-xs">Loading...</p>
          </div>
        ) : top5.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-500 gap-2">
            <Shield className="w-8 h-8 opacity-30" />
            <p className="text-xs">No pending approvals</p>
          </div>
        ) : (
          <div className="divide-y divide-dark-100">
            {top5.map((item) => {
              const risk = normalizeRisk(item.urgency)
              const isActioning = actionLoadingIds.has(item.id)
              const amountNum = parseFloat(item.amount)

              return (
                <div key={item.id} className="p-4 hover:bg-dark-400/50 transition-colors">
                  {/* Row 1: agent + risk badge */}
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-medium text-white font-mono truncate max-w-[120px]">
                      {item.agent_id}
                    </p>
                    <span
                      className={clsx(
                        'px-1.5 py-0.5 text-xs font-medium border',
                        risk === 'high' && 'text-red-400 bg-red-500/10 border-red-500/30',
                        risk === 'medium' && 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
                        risk === 'low' && 'text-sardis-400 bg-sardis-500/10 border-sardis-500/30'
                      )}
                    >
                      {item.urgency.toUpperCase()}
                    </span>
                  </div>

                  {/* Row 2: amount + destination */}
                  <p className="text-sm font-bold text-white mb-0.5">
                    {isNaN(amountNum) ? item.amount : formatAmount(item.amount)}{' '}
                    <span className="text-xs text-gray-500 font-normal">{item.token}</span>
                  </p>
                  <p className="text-xs text-gray-400 truncate mb-3">{item.destination}</p>

                  {/* Row 3: time + actions */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">{formatTimeAgo(item.created_at)}</span>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => onApprove(item.id)}
                        disabled={isActioning}
                        className={clsx(
                          'px-2.5 py-1 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-xs font-medium flex items-center gap-1 transition-all',
                          isActioning ? 'opacity-50 cursor-not-allowed' : 'hover:bg-sardis-500/20'
                        )}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        {isActioning ? '...' : 'Approve'}
                      </button>
                      <button
                        onClick={() => onDeny(item.id)}
                        disabled={isActioning}
                        className={clsx(
                          'px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/30 text-xs font-medium flex items-center gap-1 transition-all',
                          isActioning ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-500/20'
                        )}
                      >
                        <XCircle className="w-3 h-3" />
                        {isActioning ? '...' : 'Deny'}
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}

            {pending.length > 5 && (
              <div className="px-4 py-3 bg-dark-400/30">
                <Link
                  to="/approvals"
                  className="text-xs text-sardis-400 hover:text-sardis-300 transition-colors"
                >
                  + {pending.length - 5} more pending — view all approvals
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Risk Feed (Center Column) ─── */

interface RiskFeedProps {
  transactions: Transaction[]
  isLoading: boolean
}

function RiskFeed({ transactions, isLoading }: RiskFeedProps) {
  // Sort by urgency: failed/rejected first, then pending, then others
  const sorted = useMemo(() => {
    return [...transactions].sort((a, b) => {
      const order = { failed: 0, pending: 1, completed: 2 }
      const oa = order[a.status as keyof typeof order] ?? 3
      const ob = order[b.status as keyof typeof order] ?? 3
      if (oa !== ob) return oa - ob
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  }, [transactions])

  const feed = sorted.slice(0, 15)

  return (
    <div className="bg-dark-300 border border-dark-100 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-dark-100">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sardis-400" />
          <h2 className="text-sm font-semibold text-white">Risk Feed</h2>
          <span className="text-xs text-gray-500">sorted by urgency</span>
        </div>
        <Link
          to="/evidence"
          className="text-xs text-sardis-400 hover:text-sardis-300 flex items-center gap-1 transition-colors"
        >
          Evidence
          <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-500 gap-2">
            <RefreshCw className="w-6 h-6 animate-spin opacity-50" />
            <p className="text-xs">Loading transactions...</p>
          </div>
        ) : feed.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-gray-500 gap-2">
            <Zap className="w-8 h-8 opacity-30" />
            <p className="text-xs">No transactions yet</p>
          </div>
        ) : (
          <div className="divide-y divide-dark-100">
            {feed.map((tx) => {
              const risk = txRiskFromStatus(tx.status)
              const isHighRisk = risk === 'high'
              const isMedium = risk === 'medium'

              return (
                <div
                  key={tx.tx_id}
                  className={clsx(
                    'px-4 py-3 flex items-center gap-3 hover:bg-dark-400/50 transition-colors',
                    isHighRisk && 'bg-red-950/20'
                  )}
                >
                  {/* Status dot */}
                  <div className="relative flex-shrink-0">
                    <div
                      className={clsx(
                        'w-2 h-2',
                        isHighRisk
                          ? 'bg-red-500'
                          : isMedium
                          ? 'bg-yellow-500'
                          : 'bg-sardis-500'
                      )}
                    />
                    {isMedium && (
                      <div className="absolute inset-0 bg-yellow-500 animate-ping opacity-50" />
                    )}
                    {isHighRisk && (
                      <div className="absolute inset-0 bg-red-500 animate-ping opacity-50" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-white font-mono truncate">
                        {tx.from_wallet}
                      </p>
                      <span
                        className={clsx(
                          'text-xs font-bold flex-shrink-0',
                          isHighRisk && 'text-red-400',
                          isMedium && 'text-yellow-400',
                          !isHighRisk && !isMedium && 'text-sardis-400'
                        )}
                      >
                        {formatAmount(tx.amount)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2 mt-0.5">
                      <p className="text-xs text-gray-500 truncate">
                        {tx.purpose || `→ ${tx.to_wallet || 'unknown'}`}
                      </p>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span
                          className={clsx(
                            'text-xs px-1.5 py-0.5 border capitalize',
                            isHighRisk && 'text-red-400 bg-red-500/10 border-red-500/20',
                            isMedium && 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
                            !isHighRisk &&
                              !isMedium &&
                              'text-sardis-400 bg-sardis-500/10 border-sardis-500/20'
                          )}
                        >
                          {tx.status}
                        </span>
                        <span className="text-xs text-gray-600">
                          {formatTimeAgo(tx.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── System Posture (Right Column) ─── */

interface SystemPostureProps {
  killSwitchData: {
    global: Record<string, unknown> | null
    rails: Record<string, unknown>
    chains: Record<string, unknown>
    agents: Record<string, unknown>
  } | undefined
  isKillSwitchLoading: boolean
  pendingCount: number
  approvals: ApiApproval[]
}

function SystemPosture({ killSwitchData, isKillSwitchLoading, approvals }: SystemPostureProps) {
  const rails = killSwitchData?.rails ?? {}
  const chains = killSwitchData?.chains ?? {}
  const agents = killSwitchData?.agents ?? {}

  const activeRailCount = Object.values(rails).filter(Boolean).length
  const activeChainCount = Object.values(chains).filter(Boolean).length
  const frozenAgentCount = Object.values(agents).filter(Boolean).length
  const anyKillSwitchActive = Boolean(
    killSwitchData?.global || activeRailCount > 0 || activeChainCount > 0
  )

  const dayAgo = Date.now() - 86400000
  const recentApprovals = approvals.filter(
    (a) => new Date(a.reviewed_at ?? a.created_at).getTime() > dayAgo
  )
  const deniedToday = recentApprovals.filter((a) => a.status === 'rejected').length
  const approvedToday = recentApprovals.filter((a) => a.status === 'approved').length
  const denialSpike = deniedToday > 3

  return (
    <div className="bg-dark-300 border border-dark-100 flex flex-col gap-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-dark-100">
        <Shield className="w-4 h-4 text-sardis-400" />
        <h2 className="text-sm font-semibold text-white">System Posture</h2>
      </div>

      {/* Kill Switch Status */}
      <div className="px-5 py-4 border-b border-dark-100">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">Kill Switch</p>
        {isKillSwitchLoading ? (
          <div className="flex items-center gap-2 text-gray-500 text-xs">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Checking...
          </div>
        ) : (
          <div
            className={clsx(
              'flex items-center gap-3 p-3 border',
              anyKillSwitchActive
                ? 'bg-red-950/40 border-red-500/40'
                : 'bg-dark-400 border-dark-100'
            )}
          >
            <div className="relative flex-shrink-0">
              <div
                className={clsx(
                  'w-3 h-3',
                  anyKillSwitchActive ? 'bg-red-500' : 'bg-sardis-500'
                )}
              />
              {anyKillSwitchActive && (
                <div className="absolute inset-0 bg-red-500 animate-ping opacity-60" />
              )}
            </div>
            <div className="flex-1">
              {anyKillSwitchActive ? (
                <>
                  <p className="text-sm font-bold text-red-400">SUSPENDED</p>
                  {activeRailCount > 0 && (
                    <p className="text-xs text-red-300/70">{activeRailCount} rail(s) blocked</p>
                  )}
                  {activeChainCount > 0 && (
                    <p className="text-xs text-red-300/70">{activeChainCount} chain(s) blocked</p>
                  )}
                </>
              ) : (
                <p className="text-sm font-medium text-sardis-400">All Operational</p>
              )}
            </div>
            <Link
              to="/kill-switch"
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        )}
      </div>

      {/* Frozen Wallets */}
      <div className="px-5 py-4 border-b border-dark-100">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Frozen Agents</p>
            <p
              className={clsx(
                'text-2xl font-bold',
                frozenAgentCount > 0 ? 'text-red-400' : 'text-white'
              )}
            >
              {frozenAgentCount}
            </p>
          </div>
          <Lock
            className={clsx(
              'w-6 h-6',
              frozenAgentCount > 0 ? 'text-red-400' : 'text-gray-600'
            )}
          />
        </div>
      </div>

      {/* Denial Spike */}
      <div className="px-5 py-4 border-b border-dark-100">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Decisions (24h)</p>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-400">Approved</span>
              <span className="text-sardis-400 font-medium">{approvedToday}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">Denied</span>
              <span
                className={clsx(
                  'font-medium',
                  denialSpike ? 'text-red-400' : 'text-gray-300'
                )}
              >
                {deniedToday}
                {denialSpike && (
                  <AlertTriangle className="inline w-3 h-3 ml-1 text-red-400" />
                )}
              </span>
            </div>
          </div>
        </div>
        {denialSpike && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-1">
            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
            Denial spike detected
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="px-5 py-4 space-y-2.5">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">Quick Actions</p>

        <Link
          to="/kill-switch"
          className="flex items-center gap-2 w-full px-3 py-2.5 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-all"
        >
          <Power className="w-3.5 h-3.5" />
          Kill Switch Controls
          <ExternalLink className="w-3 h-3 ml-auto" />
        </Link>

        <Link
          to="/exceptions"
          className="flex items-center gap-2 w-full px-3 py-2.5 bg-dark-400 border border-dark-100 text-gray-300 text-xs font-medium hover:border-sardis-500/30 hover:text-sardis-400 transition-all"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          View Exceptions
          <ExternalLink className="w-3 h-3 ml-auto" />
        </Link>

        <Link
          to="/anomaly"
          className="flex items-center gap-2 w-full px-3 py-2.5 bg-dark-400 border border-dark-100 text-gray-300 text-xs font-medium hover:border-sardis-500/30 hover:text-sardis-400 transition-all"
        >
          <Activity className="w-3.5 h-3.5" />
          Anomaly Detection
          <ExternalLink className="w-3 h-3 ml-auto" />
        </Link>
      </div>
    </div>
  )
}

/* ─── Page ─── */

export default function ControlCenterPage() {
  const [actionLoadingIds, setActionLoadingIds] = useState<Set<string>>(new Set())

  const {
    data: pendingData,
    isLoading: pendingLoading,
    isError: pendingError,
  } = usePendingApprovals()

  const { data: allApprovalsData } = useApprovals({ limit: 50 })

  const { data: transactions = [], isLoading: txLoading } = useTransactions(50)

  const { data: killSwitchData, isLoading: ksLoading } = useKillSwitchStatus()

  const { data: health } = useHealth()

  const approveMutation = useApproveApproval()
  const denyMutation = useDenyApproval()

  /* ─── Derived data ─── */

  const pendingEnvelope = pendingData as unknown as { approvals?: ApiApproval[] } | undefined
  const pending: ApiApproval[] =
    pendingEnvelope?.approvals ??
    (Array.isArray(pendingData) ? (pendingData as unknown as ApiApproval[]) : [])

  const allEnvelope = allApprovalsData as unknown as { approvals?: ApiApproval[] } | undefined
  const allApprovals: ApiApproval[] =
    allEnvelope?.approvals ??
    (Array.isArray(allApprovalsData) ? (allApprovalsData as unknown as ApiApproval[]) : [])

  // Transactions today
  const dayAgo = Date.now() - 86400000
  const txToday = useMemo(
    () => transactions.filter((tx) => new Date(tx.created_at).getTime() > dayAgo).length,
    [transactions]
  )

  // Denial rate
  const denialRate = useMemo(() => {
    const recent = allApprovals.filter(
      (a) => new Date(a.reviewed_at ?? a.created_at).getTime() > dayAgo
    )
    if (recent.length === 0) return '0%'
    const denied = recent.filter((a) => a.status === 'rejected').length
    return `${Math.round((denied / recent.length) * 100)}%`
  }, [allApprovals])

  /* ─── Handlers ─── */

  const handleApprove = async (id: string) => {
    setActionLoadingIds((prev) => new Set(prev).add(id))
    try {
      await approveMutation.mutateAsync({ id })
    } finally {
      setActionLoadingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleDeny = async (id: string) => {
    setActionLoadingIds((prev) => new Set(prev).add(id))
    try {
      await denyMutation.mutateAsync({ id })
    } finally {
      setActionLoadingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  /* ─── Render ─── */

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold font-display text-gradient flex items-center gap-3">
          <Shield className="w-8 h-8 text-sardis-500" />
          Control Center
        </h1>
        <p className="text-gray-400 mt-1">
          Unified operator view — pending approvals, risk feed, and system posture in one place.
        </p>
      </div>

      {/* Top Stats */}
      <TopStats
        pendingCount={pending.length}
        txToday={txToday}
        denialRate={denialRate}
        healthStatus={health?.status ?? 'unknown'}
      />

      {/* 3-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
        {/* Left: Action Queue */}
        <ActionQueue
          pending={pending}
          isLoading={pendingLoading}
          isError={pendingError}
          actionLoadingIds={actionLoadingIds}
          onApprove={handleApprove}
          onDeny={handleDeny}
        />

        {/* Center: Risk Feed */}
        <RiskFeed transactions={transactions} isLoading={txLoading} />

        {/* Right: System Posture */}
        <SystemPosture
          killSwitchData={
            killSwitchData as
              | {
                  global: Record<string, unknown> | null
                  rails: Record<string, unknown>
                  chains: Record<string, unknown>
                  agents: Record<string, unknown>
                }
              | undefined
          }
          isKillSwitchLoading={ksLoading}
          pendingCount={pending.length}
          approvals={allApprovals}
        />
      </div>
    </div>
  )
}
