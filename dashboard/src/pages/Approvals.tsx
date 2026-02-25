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
  DollarSign,
  User,
  Calendar,
  Tag,
  Settings,
  Filter,
} from 'lucide-react'
import clsx from 'clsx'

/* ─── Types ─── */

interface PendingApproval {
  id: string
  agent_id: string
  agent_name: string
  amount: number
  token: string
  destination: string
  purpose: string
  timestamp: string
  risk_score: 'low' | 'medium' | 'high'
  metadata?: {
    daily_spend?: number
    monthly_spend?: number
    last_similar_tx?: string
  }
}

interface ApprovalHistory {
  id: string
  agent_id: string
  agent_name: string
  amount: number
  token: string
  destination: string
  purpose: string
  decision: 'approved' | 'rejected'
  decided_by: string
  decided_at: string
  processing_time_seconds: number
}

interface AutoApproveRule {
  id: string
  agent_id: string
  agent_name: string
  threshold: number
  enabled: boolean
}

/* ─── Mock Data ─── */

const MOCK_PENDING: PendingApproval[] = [
  {
    id: 'pending_001',
    agent_id: 'agent_001',
    agent_name: 'Research Agent',
    amount: 250.00,
    token: 'USDC',
    destination: 'OpenAI',
    purpose: 'GPT-4 API fine-tuning batch',
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    risk_score: 'medium',
    metadata: {
      daily_spend: 450,
      monthly_spend: 2100,
      last_similar_tx: '2 days ago',
    },
  },
  {
    id: 'pending_002',
    agent_id: 'agent_003',
    agent_name: 'Data Scraper',
    amount: 850.00,
    token: 'USDC',
    destination: 'AWS',
    purpose: 'EC2 GPU instances for data processing',
    timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    risk_score: 'high',
    metadata: {
      daily_spend: 1200,
      monthly_spend: 8500,
    },
  },
  {
    id: 'pending_003',
    agent_id: 'agent_002',
    agent_name: 'Trading Bot',
    amount: 125.50,
    token: 'USDT',
    destination: 'Anthropic',
    purpose: 'Claude API usage for market analysis',
    timestamp: new Date(Date.now() - 2 * 60000).toISOString(),
    risk_score: 'low',
    metadata: {
      daily_spend: 75,
      monthly_spend: 420,
      last_similar_tx: '4 hours ago',
    },
  },
  {
    id: 'pending_004',
    agent_id: 'agent_005',
    agent_name: 'Content Generator',
    amount: 180.00,
    token: 'USDC',
    destination: 'Midjourney',
    purpose: 'Image generation credits',
    timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
    risk_score: 'medium',
  },
  {
    id: 'pending_005',
    agent_id: 'agent_001',
    agent_name: 'Research Agent',
    amount: 320.00,
    token: 'USDC',
    destination: 'Google Cloud',
    purpose: 'BigQuery data analysis',
    timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
    risk_score: 'medium',
    metadata: {
      daily_spend: 770,
      monthly_spend: 2420,
    },
  },
]

const MOCK_HISTORY: ApprovalHistory[] = [
  {
    id: 'hist_001',
    agent_id: 'agent_001',
    agent_name: 'Research Agent',
    amount: 150.00,
    token: 'USDC',
    destination: 'OpenAI',
    purpose: 'API inference calls',
    decision: 'approved',
    decided_by: 'admin@sardis.sh',
    decided_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    processing_time_seconds: 45,
  },
  {
    id: 'hist_002',
    agent_id: 'agent_004',
    agent_name: 'Email Agent',
    amount: 500.00,
    token: 'USDC',
    destination: 'SendGrid',
    purpose: 'Bulk email campaign',
    decision: 'rejected',
    decided_by: 'admin@sardis.sh',
    decided_at: new Date(Date.now() - 4 * 3600000).toISOString(),
    processing_time_seconds: 120,
  },
  {
    id: 'hist_003',
    agent_id: 'agent_002',
    agent_name: 'Trading Bot',
    amount: 200.00,
    token: 'USDT',
    destination: 'Anthropic',
    purpose: 'Market sentiment analysis',
    decision: 'approved',
    decided_by: 'operator@sardis.sh',
    decided_at: new Date(Date.now() - 6 * 3600000).toISOString(),
    processing_time_seconds: 30,
  },
  {
    id: 'hist_004',
    agent_id: 'agent_003',
    agent_name: 'Data Scraper',
    amount: 750.00,
    token: 'USDC',
    destination: 'AWS',
    purpose: 'S3 storage expansion',
    decision: 'approved',
    decided_by: 'admin@sardis.sh',
    decided_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    processing_time_seconds: 180,
  },
]

const MOCK_AUTO_RULES: AutoApproveRule[] = [
  {
    id: 'rule_001',
    agent_id: 'agent_001',
    agent_name: 'Research Agent',
    threshold: 50,
    enabled: true,
  },
  {
    id: 'rule_002',
    agent_id: 'agent_002',
    agent_name: 'Trading Bot',
    threshold: 100,
    enabled: true,
  },
  {
    id: 'rule_003',
    agent_id: 'agent_003',
    agent_name: 'Data Scraper',
    threshold: 200,
    enabled: false,
  },
]

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
  const [pending, setPending] = useState<PendingApproval[]>(MOCK_PENDING)
  const [history, setHistory] = useState<ApprovalHistory[]>(MOCK_HISTORY)
  const [autoRules, setAutoRules] = useState<AutoApproveRule[]>(MOCK_AUTO_RULES)
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const [showAutoRules, setShowAutoRules] = useState(false)
  const [filterRisk, setFilterRisk] = useState<'all' | 'low' | 'medium' | 'high'>('all')

  const filteredPending = useMemo(() => {
    if (filterRisk === 'all') return pending
    return pending.filter(item => item.risk_score === filterRisk)
  }, [pending, filterRisk])

  const stats = useMemo(() => {
    const approvedToday = history.filter(h => {
      const decidedTime = new Date(h.decided_at).getTime()
      const dayAgo = Date.now() - 24 * 3600000
      return h.decision === 'approved' && decidedTime > dayAgo
    })

    const rejectedToday = history.filter(h => {
      const decidedTime = new Date(h.decided_at).getTime()
      const dayAgo = Date.now() - 24 * 3600000
      return h.decision === 'rejected' && decidedTime > dayAgo
    })

    const avgTime = history.length > 0
      ? Math.round(history.reduce((sum, h) => sum + h.processing_time_seconds, 0) / history.length)
      : 0

    return {
      pending: pending.length,
      approvedToday: approvedToday.length,
      rejectedToday: rejectedToday.length,
      avgResponseTime: avgTime,
    }
  }, [pending, history])

  const handleApprove = (id: string) => {
    const item = pending.find(p => p.id === id)
    if (!item) return

    const newHistoryItem: ApprovalHistory = {
      id: `hist_${Date.now()}`,
      agent_id: item.agent_id,
      agent_name: item.agent_name,
      amount: item.amount,
      token: item.token,
      destination: item.destination,
      purpose: item.purpose,
      decision: 'approved',
      decided_by: 'admin@sardis.sh',
      decided_at: new Date().toISOString(),
      processing_time_seconds: Math.floor(Math.random() * 120) + 30,
    }

    setPending(prev => prev.filter(p => p.id !== id))
    setHistory(prev => [newHistoryItem, ...prev])
    setSelectedItems(prev => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
  }

  const handleReject = (id: string) => {
    const item = pending.find(p => p.id === id)
    if (!item) return

    const newHistoryItem: ApprovalHistory = {
      id: `hist_${Date.now()}`,
      agent_id: item.agent_id,
      agent_name: item.agent_name,
      amount: item.amount,
      token: item.token,
      destination: item.destination,
      purpose: item.purpose,
      decision: 'rejected',
      decided_by: 'admin@sardis.sh',
      decided_at: new Date().toISOString(),
      processing_time_seconds: Math.floor(Math.random() * 120) + 30,
    }

    setPending(prev => prev.filter(p => p.id !== id))
    setHistory(prev => [newHistoryItem, ...prev])
    setSelectedItems(prev => {
      const next = new Set(prev)
      next.delete(id)
      return next
    })
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

  const toggleAutoRule = (ruleId: string) => {
    setAutoRules(prev =>
      prev.map(rule =>
        rule.id === ruleId ? { ...rule, enabled: !rule.enabled } : rule
      )
    )
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
        <button
          onClick={() => setShowAutoRules(!showAutoRules)}
          className={clsx(
            'px-4 py-2 text-sm font-medium border transition-all flex items-center gap-2',
            showAutoRules
              ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
              : 'bg-dark-300 text-gray-400 border-dark-100 hover:border-sardis-500/30'
          )}
        >
          <Settings className="w-4 h-4" />
          Auto-Approve Rules
        </button>
      </div>

      <div className="bg-dark-300 border border-dark-100 p-4">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Runtime policy posture</p>
        <p className="text-sm text-gray-200">
          High-risk PAN execution requires approval quorum and distinct reviewers. Policy or auth uncertainty is treated as deny by default.
        </p>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Pending</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.pending}</p>
            </div>
            <Clock className="w-8 h-8 text-yellow-400" />
          </div>
        </div>

        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Approved Today</p>
              <p className="text-3xl font-bold text-sardis-400 mt-1">{stats.approvedToday}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-sardis-500" />
          </div>
        </div>

        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Rejected Today</p>
              <p className="text-3xl font-bold text-red-400 mt-1">{stats.rejectedToday}</p>
            </div>
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
        </div>

        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Avg Response Time</p>
              <p className="text-3xl font-bold text-white mt-1">{stats.avgResponseTime}s</p>
            </div>
            <TrendingUp className="w-8 h-8 text-blue-400" />
          </div>
        </div>
      </div>

      {/* Auto-Approve Rules Section */}
      {showAutoRules && (
        <div className="bg-dark-300 border border-dark-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Settings className="w-5 h-5 text-sardis-500" />
                Auto-Approve Thresholds
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                Automatically approve transactions below these thresholds per agent
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {autoRules.map(rule => (
              <div
                key={rule.id}
                className="flex items-center justify-between p-4 bg-dark-400 border border-dark-100"
              >
                <div className="flex items-center gap-4 flex-1">
                  <User className="w-5 h-5 text-gray-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{rule.agent_name}</p>
                    <p className="text-xs text-gray-500 font-mono">{rule.agent_id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      value={rule.threshold}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value)
                        setAutoRules(prev =>
                          prev.map(r =>
                            r.id === rule.id ? { ...r, threshold: val } : r
                          )
                        )
                      }}
                      className="w-24 px-2 py-1 bg-dark-300 border border-dark-100 text-white text-sm focus:outline-none focus:border-sardis-500/30"
                    />
                  </div>
                </div>
                <button
                  onClick={() => toggleAutoRule(rule.id)}
                  className={clsx(
                    'px-3 py-1 text-xs font-medium border transition-all',
                    rule.enabled
                      ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                      : 'bg-dark-300 text-gray-500 border-dark-100'
                  )}
                >
                  {rule.enabled ? 'Enabled' : 'Disabled'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

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
                onChange={(e) => setFilterRisk(e.target.value as any)}
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

        {filteredPending.length === 0 ? (
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
              const RiskIcon = getRiskIcon(item.risk_score)
              const isExpanded = expandedItems.has(item.id)
              const isSelected = selectedItems.has(item.id)

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
                        <p className="text-sm font-medium text-white">{item.agent_name}</p>
                        <p className="text-xs text-gray-600 font-mono">{item.agent_id}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Amount</p>
                        <p className="text-sm font-bold text-white">
                          ${item.amount.toFixed(2)} {item.token}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Destination</p>
                        <p className="text-sm font-medium text-white">{item.destination}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Time</p>
                        <p className="text-sm font-medium text-white">{formatTimeAgo(item.timestamp)}</p>
                      </div>

                      <div>
                        <p className="text-xs text-gray-500">Risk</p>
                        <div className={clsx(
                          'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border',
                          getRiskBadgeColor(item.risk_score)
                        )}>
                          <RiskIcon className="w-3 h-3" />
                          {item.risk_score.toUpperCase()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleApprove(item.id)}
                        className="px-4 py-2 bg-sardis-500/10 text-sardis-400 border border-sardis-500/30 text-sm font-medium hover:bg-sardis-500/20 transition-all flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        className="px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 text-sm font-medium hover:bg-red-500/20 transition-all flex items-center gap-1"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject
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
                          <p className="text-xs text-gray-500 mb-1">Purpose</p>
                          <p className="text-white">{item.purpose}</p>
                        </div>
                        {item.metadata && (
                          <div className="space-y-2">
                            {item.metadata.daily_spend && (
                              <div>
                                <p className="text-xs text-gray-500">Daily Spend</p>
                                <p className="text-white">${item.metadata.daily_spend.toFixed(2)}</p>
                              </div>
                            )}
                            {item.metadata.monthly_spend && (
                              <div>
                                <p className="text-xs text-gray-500">Monthly Spend</p>
                                <p className="text-white">${item.metadata.monthly_spend.toFixed(2)}</p>
                              </div>
                            )}
                            {item.metadata.last_similar_tx && (
                              <div>
                                <p className="text-xs text-gray-500">Last Similar Transaction</p>
                                <p className="text-white">{item.metadata.last_similar_tx}</p>
                              </div>
                            )}
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

        {history.length === 0 ? (
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
                    Purpose
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Decision
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Decided By
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Response Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-100">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-dark-400 transition-colors">
                    <td className="py-3 px-4">
                      <p className="text-white font-medium">{item.agent_name}</p>
                      <p className="text-xs text-gray-600 font-mono">{item.agent_id}</p>
                    </td>
                    <td className="py-3 px-4">
                      <p className="text-white font-medium">
                        ${item.amount.toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-500">{item.token}</p>
                    </td>
                    <td className="py-3 px-4 text-white">{item.destination}</td>
                    <td className="py-3 px-4 text-gray-400 max-w-xs truncate">{item.purpose}</td>
                    <td className="py-3 px-4">
                      <div className={clsx(
                        'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border',
                        item.decision === 'approved'
                          ? 'text-sardis-400 bg-sardis-500/10 border-sardis-500/30'
                          : 'text-red-400 bg-red-500/10 border-red-500/30'
                      )}>
                        {item.decision === 'approved' ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        {item.decision.toUpperCase()}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-xs">{item.decided_by}</td>
                    <td className="py-3 px-4 text-gray-400 text-xs">
                      {formatTimeAgo(item.decided_at)}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-xs">
                      {item.processing_time_seconds}s
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
