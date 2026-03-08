import { useState, useMemo } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RotateCcw,
  ArrowUpRight,
  Clock,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  Loader2,
} from 'lucide-react'
import clsx from 'clsx'
import {
  useExceptions,
  useResolveException,
  useEscalateException,
  useRetryException,
} from '../hooks/useApi'

/* ─── Types ─── */

type ExceptionStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'ESCALATED' | 'ABANDONED'
type ExceptionType =
  | 'POLICY_BLOCKED'
  | 'CHAIN_FAILURE'
  | 'INSUFFICIENT_FUNDS'
  | 'COMPLIANCE_HOLD'
  | 'TIMEOUT'
  | 'MERCHANT_REJECTED'
  | 'KILL_SWITCH_ACTIVE'
type ExceptionStrategy =
  | 'RETRY'
  | 'RETRY_WITH_BACKOFF'
  | 'ESCALATE_TO_HUMAN'
  | 'AUTO_ADJUST'
  | 'REFUND'
  | 'WAIT_AND_RETRY'

interface Exception {
  id: string
  transaction_id: string
  agent_id: string
  exception_type: ExceptionType
  status: ExceptionStatus
  strategy: ExceptionStrategy
  retry_count: number
  max_retries: number
  metadata: Record<string, unknown>
  created_at: string
  resolved_at: string | null
  resolution_notes: string | null
}

/* ─── Helpers ─── */

function formatTimeAgo(isoString: string): string {
  const now = Date.now()
  const ts = new Date(isoString).getTime()
  const diffMinutes = Math.floor((now - ts) / 60000)
  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`
  return `${Math.floor(diffMinutes / 1440)}d ago`
}

function truncate(str: string, len = 16): string {
  if (str.length <= len) return str
  return `${str.slice(0, len)}…`
}

/* ─── Badge helpers ─── */

function statusBadgeClass(status: ExceptionStatus): string {
  switch (status) {
    case 'OPEN':        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
    case 'IN_PROGRESS': return 'bg-blue-500/10 text-blue-400 border-blue-500/30'
    case 'RESOLVED':    return 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
    case 'ESCALATED':   return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'ABANDONED':   return 'bg-gray-500/10 text-gray-400 border-gray-500/30'
  }
}

function typeBadgeClass(type: ExceptionType): string {
  switch (type) {
    case 'POLICY_BLOCKED':    return 'bg-orange-500/10 text-orange-400 border-orange-500/30'
    case 'CHAIN_FAILURE':     return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'INSUFFICIENT_FUNDS':return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
    case 'COMPLIANCE_HOLD':   return 'bg-purple-500/10 text-purple-400 border-purple-500/30'
    case 'TIMEOUT':           return 'bg-gray-500/10 text-gray-400 border-gray-500/30'
    case 'MERCHANT_REJECTED': return 'bg-red-500/10 text-red-400 border-red-500/30'
    case 'KILL_SWITCH_ACTIVE':return 'bg-red-500/10 text-red-400 border-red-500/30'
  }
}

function StatusIcon({ status }: { status: ExceptionStatus }) {
  switch (status) {
    case 'OPEN':        return <Clock className="w-3 h-3" />
    case 'IN_PROGRESS': return <RotateCcw className="w-3 h-3" />
    case 'RESOLVED':    return <CheckCircle2 className="w-3 h-3" />
    case 'ESCALATED':   return <ArrowUpRight className="w-3 h-3" />
    case 'ABANDONED':   return <XCircle className="w-3 h-3" />
  }
}

/* ─── Stat Card ─── */

interface StatCardProps {
  label: string
  value: number
  color: string
  icon: React.ReactNode
}

function StatCard({ label, value, color, icon }: StatCardProps) {
  return (
    <div className="bg-dark-300 border border-dark-100 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className={clsx('text-3xl font-bold mt-1', color)}>{value}</p>
        </div>
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', `${color.replace('text-', 'bg-').replace('-400', '-500')}/10`)}>
          {icon}
        </div>
      </div>
    </div>
  )
}

/* ─── Resolve Dialog (inline) ─── */

interface ResolveInputProps {
  value: string
  onChange: (v: string) => void
  onConfirm: () => void
  onCancel: () => void
  loading: boolean
}

function ResolveInput({ value, onChange, onConfirm, onCancel, loading }: ResolveInputProps) {
  return (
    <div className="flex flex-col gap-2 mt-3">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Resolution notes (optional)..."
        rows={2}
        className="w-full px-3 py-2 bg-dark-400 border border-dark-100 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 resize-none"
      />
      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          disabled={loading}
          className={clsx(
            'px-4 py-1.5 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-sm font-medium flex items-center gap-1 transition-all',
            loading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-sardis-500/20'
          )}
        >
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
          Confirm Resolve
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-1.5 bg-dark-400 text-gray-400 border border-dark-100 text-sm font-medium hover:text-white transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

/* ─── Main Component ─── */

export default function ExceptionsPage() {
  const [statusFilter, setStatusFilter] = useState<ExceptionStatus | 'ALL'>('ALL')
  const [typeFilter, setTypeFilter] = useState<ExceptionType | 'ALL'>('ALL')
  const [agentSearch, setAgentSearch] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const [resolveNotes, setResolveNotes] = useState('')
  const [actionLoadingIds, setActionLoadingIds] = useState<Set<string>>(new Set())

  const { data, isLoading, isError } = useExceptions()
  const resolveException = useResolveException()
  const escalateException = useEscalateException()
  const retryException = useRetryException()

  const exceptions: Exception[] = Array.isArray(data) ? (data as unknown as Exception[]) : []

  /* ─── Stats ─── */

  const stats = useMemo(() => {
    const dayAgo = Date.now() - 24 * 3600000
    return {
      open: exceptions.filter(e => e.status === 'OPEN').length,
      inProgress: exceptions.filter(e => e.status === 'IN_PROGRESS').length,
      resolvedToday: exceptions.filter(e => {
        if (e.status !== 'RESOLVED') return false
        if (!e.resolved_at) return false
        return new Date(e.resolved_at).getTime() > dayAgo
      }).length,
      escalated: exceptions.filter(e => e.status === 'ESCALATED').length,
    }
  }, [exceptions])

  /* ─── Filtered list ─── */

  const filtered = useMemo(() => {
    return exceptions.filter(e => {
      const matchesStatus = statusFilter === 'ALL' || e.status === statusFilter
      const matchesType = typeFilter === 'ALL' || e.exception_type === typeFilter
      const matchesAgent = agentSearch === '' || e.agent_id.toLowerCase().includes(agentSearch.toLowerCase())
      return matchesStatus && matchesType && matchesAgent
    })
  }, [exceptions, statusFilter, typeFilter, agentSearch])

  /* ─── Actions ─── */

  function setLoading(id: string, on: boolean) {
    setActionLoadingIds(prev => {
      const next = new Set(prev)
      on ? next.add(id) : next.delete(id)
      return next
    })
  }

  async function handleResolve(id: string) {
    setLoading(id, true)
    try {
      await resolveException.mutateAsync({ id, notes: resolveNotes || undefined })
      setResolvingId(null)
      setResolveNotes('')
    } finally {
      setLoading(id, false)
    }
  }

  async function handleEscalate(id: string) {
    setLoading(id, true)
    try {
      await escalateException.mutateAsync({ id })
    } finally {
      setLoading(id, false)
    }
  }

  async function handleRetry(id: string) {
    setLoading(id, true)
    try {
      await retryException.mutateAsync(id)
    } finally {
      setLoading(id, false)
    }
  }

  function toggleExpanded(id: string) {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
        if (resolvingId === id) setResolvingId(null)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const isTerminal = (status: ExceptionStatus) =>
    status === 'RESOLVED' || status === 'ABANDONED'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold font-display text-gradient flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 text-yellow-500" />
          Exception Handling
        </h1>
        <p className="text-gray-400 mt-1">
          View and resolve failed, blocked, or exceptional payments
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Open Exceptions"
          value={stats.open}
          color="text-yellow-400"
          icon={<Clock className="w-5 h-5 text-yellow-400" />}
        />
        <StatCard
          label="In Progress"
          value={stats.inProgress}
          color="text-blue-400"
          icon={<RotateCcw className="w-5 h-5 text-blue-400" />}
        />
        <StatCard
          label="Resolved Today"
          value={stats.resolvedToday}
          color="text-sardis-400"
          icon={<CheckCircle2 className="w-5 h-5 text-sardis-400" />}
        />
        <StatCard
          label="Escalated"
          value={stats.escalated}
          color="text-red-400"
          icon={<ArrowUpRight className="w-5 h-5 text-red-400" />}
        />
      </div>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Agent search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by agent ID..."
            value={agentSearch}
            onChange={(e) => setAgentSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-dark-300 border border-dark-100 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            className="px-3 py-2.5 bg-dark-300 border border-dark-100 text-white text-sm focus:outline-none focus:border-sardis-500/30"
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="RESOLVED">Resolved</option>
            <option value="ESCALATED">Escalated</option>
            <option value="ABANDONED">Abandoned</option>
          </select>
        </div>

        {/* Type filter */}
        <div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as typeof typeFilter)}
            className="px-3 py-2.5 bg-dark-300 border border-dark-100 text-white text-sm focus:outline-none focus:border-sardis-500/30"
          >
            <option value="ALL">All Types</option>
            <option value="POLICY_BLOCKED">Policy Blocked</option>
            <option value="CHAIN_FAILURE">Chain Failure</option>
            <option value="INSUFFICIENT_FUNDS">Insufficient Funds</option>
            <option value="COMPLIANCE_HOLD">Compliance Hold</option>
            <option value="TIMEOUT">Timeout</option>
            <option value="MERCHANT_REJECTED">Merchant Rejected</option>
            <option value="KILL_SWITCH_ACTIVE">Kill Switch Active</option>
          </select>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="bg-dark-300 border border-dark-100 p-12 text-center">
          <Loader2 className="w-8 h-8 text-sardis-500 mx-auto mb-3 animate-spin" />
          <p className="text-gray-400 text-sm">Loading exceptions...</p>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-dark-300 border border-red-500/30 p-6">
          <div className="flex items-center gap-2 text-red-400 mb-1">
            <XCircle className="w-5 h-5" />
            <span className="font-medium">Failed to load exceptions</span>
          </div>
          <p className="text-sm text-gray-500">Check API connectivity and try refreshing.</p>
        </div>
      )}

      {/* Exceptions list */}
      {!isLoading && !isError && (
        <div className="space-y-2">
          {filtered.length === 0 ? (
            <div className="bg-dark-300 border border-dark-100 p-16 text-center">
              <AlertTriangle className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 font-medium">No exceptions found</p>
              <p className="text-gray-600 text-sm mt-1">Try adjusting your filters</p>
            </div>
          ) : (
            filtered.map((exc) => {
              const isExpanded = expandedIds.has(exc.id)
              const isActioning = actionLoadingIds.has(exc.id)
              const terminal = isTerminal(exc.status)
              const isResolvingThis = resolvingId === exc.id

              return (
                <div
                  key={exc.id}
                  className={clsx(
                    'border transition-all',
                    isExpanded
                      ? 'bg-dark-300 border-sardis-500/20'
                      : 'bg-dark-300 border-dark-100 hover:border-sardis-500/20'
                  )}
                >
                  {/* Row */}
                  <div
                    className="flex items-center gap-3 px-4 py-3 cursor-pointer select-none"
                    onClick={() => toggleExpanded(exc.id)}
                  >
                    {/* Status badge */}
                    <span className={clsx(
                      'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border shrink-0',
                      statusBadgeClass(exc.status)
                    )}>
                      <StatusIcon status={exc.status} />
                      {exc.status.replace('_', ' ')}
                    </span>

                    {/* Type badge */}
                    <span className={clsx(
                      'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border shrink-0',
                      typeBadgeClass(exc.exception_type),
                      exc.exception_type === 'KILL_SWITCH_ACTIVE' && 'animate-pulse'
                    )}>
                      {exc.exception_type.replace(/_/g, ' ')}
                    </span>

                    {/* Core info */}
                    <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 min-w-0">
                      <div className="min-w-0">
                        <p className="text-xs text-gray-500">Agent</p>
                        <p className="text-sm font-medium text-white font-mono truncate">
                          {exc.agent_id}
                        </p>
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs text-gray-500">Transaction</p>
                        <p className="text-sm text-gray-300 font-mono" title={exc.transaction_id}>
                          {truncate(exc.transaction_id, 18)}
                        </p>
                      </div>
                      <div className="hidden md:block">
                        <p className="text-xs text-gray-500">Strategy</p>
                        <p className="text-sm text-gray-300">{exc.strategy.replace(/_/g, ' ')}</p>
                      </div>
                      <div className="hidden md:block">
                        <p className="text-xs text-gray-500">Retries</p>
                        <p className={clsx(
                          'text-sm font-medium',
                          exc.retry_count >= exc.max_retries ? 'text-red-400' : 'text-gray-300'
                        )}>
                          {exc.retry_count} / {exc.max_retries}
                        </p>
                      </div>
                    </div>

                    {/* Time + chevron */}
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-gray-500 hidden sm:inline">
                        {formatTimeAgo(exc.created_at)}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-500" />
                      )}
                    </div>
                  </div>

                  {/* Expanded detail panel */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-3 border-t border-dark-100 bg-dark-400/40">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-4">
                        {/* Metadata */}
                        <div>
                          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Metadata</p>
                          {Object.keys(exc.metadata).length === 0 ? (
                            <p className="text-gray-600 text-xs">No metadata</p>
                          ) : (
                            <div className="bg-dark-500/50 border border-dark-100 p-3 space-y-1">
                              {Object.entries(exc.metadata).map(([k, v]) => (
                                <div key={k} className="flex gap-2 text-xs">
                                  <span className="text-gray-500 shrink-0">{k}:</span>
                                  <span className="text-gray-200 break-all font-mono">
                                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Details */}
                        <div className="space-y-3">
                          <div>
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Created</p>
                            <p className="text-gray-200 text-xs font-mono">{exc.created_at}</p>
                          </div>
                          {exc.resolved_at && (
                            <div>
                              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Resolved At</p>
                              <p className="text-gray-200 text-xs font-mono">{exc.resolved_at}</p>
                            </div>
                          )}
                          {exc.resolution_notes && (
                            <div>
                              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Resolution Notes</p>
                              <p className="text-gray-200 text-sm">{exc.resolution_notes}</p>
                            </div>
                          )}
                          <div className="md:hidden">
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Strategy</p>
                            <p className="text-gray-200">{exc.strategy.replace(/_/g, ' ')}</p>
                          </div>
                          <div className="md:hidden">
                            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Retries</p>
                            <p className={clsx(
                              'font-medium',
                              exc.retry_count >= exc.max_retries ? 'text-red-400' : 'text-gray-200'
                            )}>
                              {exc.retry_count} / {exc.max_retries}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Actions — only for non-terminal */}
                      {!terminal && (
                        <div className="border-t border-dark-100 pt-3">
                          {/* Inline resolve input */}
                          {isResolvingThis && (
                            <ResolveInput
                              value={resolveNotes}
                              onChange={setResolveNotes}
                              onConfirm={() => handleResolve(exc.id)}
                              onCancel={() => { setResolvingId(null); setResolveNotes('') }}
                              loading={isActioning}
                            />
                          )}

                          {!isResolvingThis && (
                            <div className="flex flex-wrap gap-2">
                              <button
                                onClick={() => { setResolvingId(exc.id); setResolveNotes('') }}
                                disabled={isActioning}
                                className={clsx(
                                  'px-4 py-2 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-sm font-medium flex items-center gap-1.5 transition-all',
                                  isActioning ? 'opacity-50 cursor-not-allowed' : 'hover:bg-sardis-500/20'
                                )}
                              >
                                <CheckCircle2 className="w-4 h-4" />
                                Resolve
                              </button>

                              <button
                                onClick={() => handleEscalate(exc.id)}
                                disabled={isActioning || exc.status === 'ESCALATED'}
                                className={clsx(
                                  'px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 text-sm font-medium flex items-center gap-1.5 transition-all',
                                  isActioning || exc.status === 'ESCALATED'
                                    ? 'opacity-50 cursor-not-allowed'
                                    : 'hover:bg-red-500/20'
                                )}
                              >
                                {isActioning ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <ArrowUpRight className="w-4 h-4" />
                                )}
                                Escalate
                              </button>

                              <button
                                onClick={() => handleRetry(exc.id)}
                                disabled={isActioning || exc.retry_count >= exc.max_retries}
                                className={clsx(
                                  'px-4 py-2 bg-blue-500/10 text-blue-400 border border-blue-500/30 text-sm font-medium flex items-center gap-1.5 transition-all',
                                  isActioning || exc.retry_count >= exc.max_retries
                                    ? 'opacity-50 cursor-not-allowed'
                                    : 'hover:bg-blue-500/20'
                                )}
                              >
                                {isActioning ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <RotateCcw className="w-4 h-4" />
                                )}
                                Retry
                                {exc.retry_count >= exc.max_retries && (
                                  <span className="text-xs opacity-60">(max reached)</span>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
