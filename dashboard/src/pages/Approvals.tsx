import { useState, useMemo } from 'react'
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Calendar,
  Filter,
} from 'lucide-react'
import clsx from 'clsx'
import { usePendingApprovals, useApprovals, useApproveApproval, useDenyApproval } from '../hooks/useApi'
import type { ApprovalRecord } from '../api/client'

/* ─── Types ─── */

type ApiApproval = ApprovalRecord

/* ─── Helpers ─── */

function formatTimeAgo(isoString: string): string {
  const now = Date.now()
  const timestamp = new Date(isoString).getTime()
  const diffMinutes = Math.floor((now - timestamp) / 60000)

  if (diffMinutes < 1) return 'Just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`
  return `${Math.floor(diffMinutes / 1440)}d ago`
}

function normalizeRisk(urgency: string): 'low' | 'medium' | 'high' {
  if (urgency === 'high') return 'high'
  if (urgency === 'medium') return 'medium'
  return 'low'
}

function approvalAgent(item: ApiApproval): string {
  return item.agent_id ?? item.requested_by
}

function approvalAmount(item: ApiApproval): string {
  return item.amount ?? item.card_limit ?? '0'
}

function approvalToken(item: ApiApproval): string {
  const token = item.metadata?.token
  return typeof token === 'string' && token ? token : 'USDC'
}

function approvalDestination(item: ApiApproval): string {
  const destination =
    item.vendor ??
    (typeof item.metadata?.destination === 'string' ? item.metadata.destination : null) ??
    (typeof item.metadata?.recipient_address === 'string' ? item.metadata.recipient_address : null) ??
    item.purpose
  return destination ?? '—'
}

function approvalNotes(item: ApiApproval): string | null {
  return item.reason ?? null
}

function getRiskBadgeColor(risk: 'low' | 'medium' | 'high'): string {
  switch (risk) {
    case 'low': return 'text-sardis-400 bg-sardis-500/10 border-sardis-500/30'
    case 'medium': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
    case 'high': return 'text-red-400 bg-red-500/10 border-red-500/30'
  }
}

function getRiskIcon(risk: 'low' | 'medium' | 'high') {
  switch (risk) {
    case 'low': return ShieldCheck
    case 'medium': return AlertTriangle
    case 'high': return AlertTriangle
  }
}

/* ─── Component ─── */

export default function ApprovalsPage() {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [filterRisk, setFilterRisk] = useState<'all' | 'low' | 'medium' | 'high'>('all')
  const [actionLoadingIds, setActionLoadingIds] = useState<Set<string>>(new Set())

  const {
    data: pendingData,
    isLoading: pendingLoading,
    isError: pendingError,
  } = usePendingApprovals()

  const {
    data: allApprovalsData,
    isLoading: historyLoading,
  } = useApprovals({ limit: 50 })

  const approveMutation = useApproveApproval()
  const denyMutation = useDenyApproval()

  const pending: ApiApproval[] = pendingData?.approvals ?? []
  const allApprovals: ApiApproval[] = allApprovalsData?.approvals ?? []
  const history = allApprovals.filter(item => item.status !== 'pending')

  const filteredPending = useMemo(() => {
    if (filterRisk === 'all') return pending
    return pending.filter(item => normalizeRisk(item.urgency) === filterRisk)
  }, [pending, filterRisk])

  const stats = useMemo(() => {
    const dayAgo = Date.now() - 24 * 3600000
    const approvedToday = history.filter(h => {
      const t = new Date(h.reviewed_at ?? h.created_at).getTime()
      return h.status === 'approved' && t > dayAgo
    })
    const deniedToday = history.filter(h => {
      const t = new Date(h.reviewed_at ?? h.created_at).getTime()
      return h.status === 'denied' && t > dayAgo
    })

    return {
      pending: pending.length,
      approvedToday: approvedToday.length,
      deniedToday: deniedToday.length,
    }
  }, [pending, history])

  const handleApprove = async (id: string) => {
    setActionLoadingIds(prev => new Set(prev).add(id))
    try {
      await approveMutation.mutateAsync({ id })
      setSelectedItems(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    } finally {
      setActionLoadingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleReject = async (id: string) => {
    setActionLoadingIds(prev => new Set(prev).add(id))
    try {
      await denyMutation.mutateAsync({ id })
      setSelectedItems(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    } finally {
      setActionLoadingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleBulkApprove = () => {
    selectedItems.forEach(id => handleApprove(id))
  }

  const handleBulkReject = () => {
    selectedItems.forEach(id => handleReject(id))
  }

  const toggleSelection = (id: string) => {
    setSelectedItems(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const toggleExpanded = (id: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedItems.size === filteredPending.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(filteredPending.map(p => p.id)))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display text-gradient flex items-center gap-3">
            <ShieldCheck className="w-8 h-8 text-sardis-500" />
            Approval Flow
          </h1>
          <p className="text-gray-400 mt-1">
            Human-in-the-loop approval for payments exceeding policy thresholds with 4-eyes reviewer controls
          </p>
        </div>
      </div>

      <div className="bg-dark-300 border border-dark-100 p-4">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Runtime policy posture</p>
        <p className="text-sm text-gray-200">
          High-risk PAN execution requires approval quorum and distinct reviewers. Policy or auth uncertainty is treated as deny by default.
        </p>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Pending</p>
              <p className="text-3xl font-bold text-white mt-1">
                {pendingLoading ? '—' : stats.pending}
              </p>
            </div>
            <Clock className="w-8 h-8 text-yellow-400" />
          </div>
        </div>

        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Approved Today</p>
              <p className="text-3xl font-bold text-sardis-400 mt-1">
                {historyLoading ? '—' : stats.approvedToday}
              </p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-sardis-500" />
          </div>
        </div>

        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Denied Today</p>
              <p className="text-3xl font-bold text-red-400 mt-1">
                {historyLoading ? '—' : stats.deniedToday}
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-blue-400" />
          </div>
        </div>
      </div>

      {/* Pending Approvals Queue */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-400" />
              Pending Approvals
              <span className="text-sm font-normal text-gray-500">({filteredPending.length})</span>
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <select
                value={filterRisk}
                onChange={(e) => setFilterRisk(e.target.value as typeof filterRisk)}
                className="px-3 py-1.5 bg-dark-400 border border-dark-100 text-white text-sm focus:outline-none focus:border-sardis-500/30"
              >
                <option value="all">All Risk Levels</option>
                <option value="low">Low Risk</option>
                <option value="medium">Medium Risk</option>
                <option value="high">High Risk</option>
              </select>
            </div>
            {selectedItems.size > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">{selectedItems.size} selected</span>
                <button
                  onClick={handleBulkApprove}
                  className="px-3 py-1.5 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-sm font-medium hover:bg-sardis-500/20 transition-all flex items-center gap-1"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Approve All
                </button>
                <button
                  onClick={handleBulkReject}
                  className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/30 text-sm font-medium hover:bg-red-500/20 transition-all flex items-center gap-1"
                >
                  <XCircle className="w-4 h-4" />
                  Reject All
                </button>
              </div>
            )}
          </div>
        </div>

        {pendingError ? (
          <div className="text-center py-12 text-red-400">
            <XCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Failed to load pending approvals. Please refresh.</p>
          </div>
        ) : pendingLoading ? (
          <div className="text-center py-12 text-gray-500">
            <Clock className="w-12 h-12 mx-auto mb-3 opacity-50 animate-pulse" />
            <p className="text-sm">Loading pending approvals...</p>
          </div>
        ) : filteredPending.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <ShieldCheck className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No pending approvals</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Select All Row */}
            <div className="flex items-center gap-3 p-3 bg-dark-400 border border-dark-100">
              <input
                type="checkbox"
                checked={selectedItems.size === filteredPending.length && filteredPending.length > 0}
                onChange={toggleSelectAll}
                className="w-4 h-4 accent-sardis-500"
              />
              <span className="text-sm text-gray-400 font-medium">Select All</span>
            </div>

            {filteredPending.map((item) => {
              const risk = normalizeRisk(item.urgency)
              const RiskIcon = getRiskIcon(risk)
              const isExpanded = expandedItems.has(item.id)
              const isSelected = selectedItems.has(item.id)
              const isActioning = actionLoadingIds.has(item.id)
              const amountNum = parseFloat(approvalAmount(item))

              return (
                <div
                  key={item.id}
                  className={clsx(
                    'border transition-all',
                    isSelected
                      ? 'bg-sardis-500/5 border-sardis-500/30'
                      : 'bg-dark-400 border-dark-100 hover:border-sardis-500/20'
                  )}
                >
                  <div className="flex items-center gap-3 p-4">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelection(item.id)}
                      className="w-4 h-4 accent-sardis-500"
                    />

                    <div className="flex-1 grid grid-cols-5 gap-4">
                      <div>
                        <p className="text-xs text-gray-500">Agent</p>
                        <p className="text-sm font-medium text-white font-mono">{approvalAgent(item)}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Amount</p>
                        <p className="text-sm font-bold text-white">
                          ${isNaN(amountNum) ? approvalAmount(item) : amountNum.toFixed(2)} {approvalToken(item)}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Counterparty</p>
                        <p className="text-sm font-medium text-white truncate">{approvalDestination(item)}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Time</p>
                        <p className="text-sm font-medium text-white">{formatTimeAgo(item.created_at)}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Risk</p>
                        <div className={clsx(
                          'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border',
                          getRiskBadgeColor(risk)
                        )}>
                          <RiskIcon className="w-3 h-3" />
                          {item.urgency.toUpperCase()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleApprove(item.id)}
                        disabled={isActioning}
                        className={clsx(
                          'px-4 py-2 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-sm font-medium transition-all flex items-center gap-1',
                          isActioning ? 'opacity-50 cursor-not-allowed' : 'hover:bg-sardis-500/20'
                        )}
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        {isActioning ? '...' : 'Approve'}
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        disabled={isActioning}
                        className={clsx(
                          'px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 text-sm font-medium transition-all flex items-center gap-1',
                          isActioning ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-500/20'
                        )}
                      >
                        <XCircle className="w-4 h-4" />
                        {isActioning ? '...' : 'Reject'}
                      </button>
                      <button
                        onClick={() => toggleExpanded(item.id)}
                        className="p-2 bg-dark-300 border border-dark-100 text-gray-400 hover:text-white hover:border-sardis-500/30 transition-all"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4 pt-2 border-t border-dark-100 bg-dark-500/50">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Action / Purpose</p>
                          <p className="text-white">{item.purpose ?? item.action}</p>
                        </div>
                        {approvalNotes(item) && (
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Notes</p>
                            <p className="text-white">{approvalNotes(item)}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Approval History */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            Approval History
            <span className="text-sm font-normal text-gray-500">({history.length})</span>
          </h2>
        </div>

        {historyLoading ? (
          <div className="text-center py-12 text-gray-500">
            <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50 animate-pulse" />
            <p className="text-sm">Loading history...</p>
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No approval history</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-100">
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Agent
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Destination
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Decision
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reviewed By
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-100">
                {history.map((item) => {
                  const amountNum = parseFloat(approvalAmount(item))
                  const isApproved = item.status === 'approved'
                  const decisionAt = item.reviewed_at ?? item.created_at

                  return (
                    <tr key={item.id} className="hover:bg-dark-400 transition-colors">
                      <td className="py-3 px-4">
                        <p className="text-white font-medium font-mono text-xs">{approvalAgent(item)}</p>
                      </td>
                      <td className="py-3 px-4">
                        <p className="text-white font-medium">
                          ${isNaN(amountNum) ? approvalAmount(item) : amountNum.toFixed(2)}
                        </p>
                        <p className="text-xs text-gray-500">{approvalToken(item)}</p>
                      </td>
                      <td className="py-3 px-4 text-white">{approvalDestination(item)}</td>
                      <td className="py-3 px-4 text-gray-400 max-w-xs truncate">{item.purpose ?? item.action}</td>
                      <td className="py-3 px-4">
                        <div className={clsx(
                          'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border',
                          isApproved
                            ? 'text-sardis-400 bg-sardis-500/10 border-sardis-500/30'
                            : 'text-red-400 bg-red-500/10 border-red-500/30'
                        )}>
                          {isApproved ? (
                            <CheckCircle2 className="w-3 h-3" />
                          ) : (
                            <XCircle className="w-3 h-3" />
                          )}
                          {item.status.toUpperCase()}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-xs">
                        {item.reviewed_by ?? '—'}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-xs">
                        {formatTimeAgo(decisionAt)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
