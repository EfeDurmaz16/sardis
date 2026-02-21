import { useState, useEffect } from 'react'
import {
  Shield,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  TrendingUp,
  Users,
  Settings,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'

// Mock data - will be replaced with API calls later
interface ConfidenceTransaction {
  id: string
  agent_id: string
  agent_name: string
  merchant: string
  amount: number
  confidence_score: number
  tier: 'auto' | 'manager' | 'multi_sig' | 'human'
  status: 'pending' | 'approved' | 'rejected' | 'completed'
  created_at: string
  approver?: string
}

interface ConfidenceThreshold {
  tier: 'auto' | 'manager' | 'multi_sig' | 'human'
  min_score: number
  max_score: number
  approvers_required: number
  description: string
  count_24h: number
}

export default function ConfidenceRouterPage() {
  const [transactions, setTransactions] = useState<ConfidenceTransaction[]>([
    {
      id: 'tx_1',
      agent_id: 'agent_001',
      agent_name: 'shopping_agent',
      merchant: 'AWS Marketplace',
      amount: 50.00,
      confidence_score: 0.98,
      tier: 'auto',
      status: 'completed',
      created_at: '2024-01-15T12:00:00Z',
    },
    {
      id: 'tx_2',
      agent_id: 'agent_002',
      agent_name: 'data_buyer',
      merchant: 'Data API Pro',
      amount: 250.00,
      confidence_score: 0.89,
      tier: 'manager',
      status: 'pending',
      created_at: '2024-01-15T11:55:00Z',
    },
    {
      id: 'tx_3',
      agent_id: 'agent_003',
      agent_name: 'research_ai',
      merchant: 'Unknown Vendor',
      amount: 1500.00,
      confidence_score: 0.65,
      tier: 'human',
      status: 'pending',
      created_at: '2024-01-15T11:50:00Z',
    },
    {
      id: 'tx_4',
      agent_id: 'agent_004',
      agent_name: 'compute_agent',
      merchant: 'GPU Cloud Services',
      amount: 800.00,
      confidence_score: 0.77,
      tier: 'multi_sig',
      status: 'pending',
      created_at: '2024-01-15T11:45:00Z',
    },
    {
      id: 'tx_5',
      agent_id: 'agent_005',
      agent_name: 'trading_bot',
      merchant: 'Stock Data Feed',
      amount: 100.00,
      confidence_score: 0.92,
      tier: 'manager',
      status: 'approved',
      created_at: '2024-01-15T11:40:00Z',
      approver: 'john@example.com',
    },
    {
      id: 'tx_6',
      agent_id: 'agent_001',
      agent_name: 'shopping_agent',
      merchant: 'GitHub',
      amount: 29.00,
      confidence_score: 0.99,
      tier: 'auto',
      status: 'completed',
      created_at: '2024-01-15T11:35:00Z',
    },
  ])

  const [thresholds, setThresholds] = useState<ConfidenceThreshold[]>([
    {
      tier: 'auto',
      min_score: 0.95,
      max_score: 1.0,
      approvers_required: 0,
      description: 'Auto-approved, high confidence',
      count_24h: 156,
    },
    {
      tier: 'manager',
      min_score: 0.85,
      max_score: 0.95,
      approvers_required: 1,
      description: 'Manager approval required',
      count_24h: 23,
    },
    {
      tier: 'multi_sig',
      min_score: 0.70,
      max_score: 0.85,
      approvers_required: 2,
      description: 'Multi-signature required',
      count_24h: 8,
    },
    {
      tier: 'human',
      min_score: 0.0,
      max_score: 0.70,
      approvers_required: 3,
      description: 'Manual review required',
      count_24h: 2,
    },
  ])

  const handleApprove = (txId: string) => {
    setTransactions(prev => prev.map(tx =>
      tx.id === txId
        ? { ...tx, status: 'approved', approver: 'current_user@example.com' }
        : tx
    ))
  }

  const handleReject = (txId: string) => {
    setTransactions(prev => prev.map(tx =>
      tx.id === txId
        ? { ...tx, status: 'rejected', approver: 'current_user@example.com' }
        : tx
    ))
  }

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'auto':
        return 'text-sardis-400'
      case 'manager':
        return 'text-yellow-500'
      case 'multi_sig':
        return 'text-orange-500'
      case 'human':
        return 'text-red-500'
      default:
        return 'text-gray-400'
    }
  }

  const getTierBgColor = (tier: string) => {
    switch (tier) {
      case 'auto':
        return 'bg-sardis-500/10 border-sardis-500/30'
      case 'manager':
        return 'bg-yellow-500/10 border-yellow-500/30'
      case 'multi_sig':
        return 'bg-orange-500/10 border-orange-500/30'
      case 'human':
        return 'bg-red-500/10 border-red-500/30'
      default:
        return 'bg-dark-200 border-dark-100'
    }
  }

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case 'auto':
        return <CheckCircle className="w-4 h-4" />
      case 'manager':
        return <Shield className="w-4 h-4" />
      case 'multi_sig':
        return <Users className="w-4 h-4" />
      case 'human':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <Settings className="w-4 h-4" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">Completed</span>
      case 'approved':
        return <span className="badge badge-info">Approved</span>
      case 'pending':
        return <span className="badge badge-warning">Pending</span>
      case 'rejected':
        return <span className="badge badge-error">Rejected</span>
      default:
        return <span className="badge">{status}</span>
    }
  }

  const pendingTransactions = transactions.filter(tx => tx.status === 'pending')
  const autoApproved24h = thresholds.find(t => t.tier === 'auto')?.count_24h || 0
  const avgConfidence = (transactions.reduce((sum, tx) => sum + tx.confidence_score, 0) / transactions.length).toFixed(3)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Confidence Router</h1>
        <p className="text-gray-400 mt-1">
          Confidence-based transaction routing and approval workflows
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Pending Approvals"
          value={pendingTransactions.length}
          change="Requires action"
          changeType={pendingTransactions.length > 0 ? 'negative' : 'positive'}
          icon={<Clock className="w-6 h-6" />}
        />
        <StatCard
          title="Auto-Approved (24h)"
          value={autoApproved24h}
          change="High confidence"
          changeType="positive"
          icon={<CheckCircle className="w-6 h-6" />}
        />
        <StatCard
          title="Avg Confidence"
          value={avgConfidence}
          change="Last 100 txns"
          changeType="positive"
          icon={<TrendingUp className="w-6 h-6" />}
        />
        <StatCard
          title="Approval Rate"
          value="94.2%"
          change="+2.1% from last week"
          changeType="positive"
          icon={<Shield className="w-6 h-6" />}
        />
      </div>

      {/* Confidence Thresholds */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Confidence Thresholds</h2>
            <p className="text-sm text-gray-400 mt-1">Configure routing tiers and approval requirements</p>
          </div>
          <Settings className="w-5 h-5 text-sardis-400" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {thresholds.map((threshold) => (
            <div
              key={threshold.tier}
              className={clsx(
                'p-4 border transition-all',
                getTierBgColor(threshold.tier)
              )}
            >
              <div className="flex items-center gap-2 mb-3">
                <div className={getTierColor(threshold.tier)}>
                  {getTierIcon(threshold.tier)}
                </div>
                <span className="text-sm font-semibold text-white capitalize">
                  {threshold.tier.replace('_', ' ')}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div>
                  <p className="text-gray-500 text-xs">Confidence Range</p>
                  <p className={clsx('font-medium mono-numbers', getTierColor(threshold.tier))}>
                    {threshold.min_score.toFixed(2)} - {threshold.max_score.toFixed(2)}
                  </p>
                </div>

                <div>
                  <p className="text-gray-500 text-xs">Approvers Required</p>
                  <p className="text-white font-medium mono-numbers">{threshold.approvers_required}</p>
                </div>

                <div>
                  <p className="text-gray-500 text-xs">24h Count</p>
                  <p className="text-white font-medium mono-numbers">{threshold.count_24h}</p>
                </div>

                <p className="text-xs text-gray-400 pt-2 border-t border-dark-100">
                  {threshold.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pending Approvals */}
      {pendingTransactions.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Pending Approvals</h2>
              <p className="text-sm text-gray-400 mt-1">Transactions awaiting review</p>
            </div>
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
          </div>

          <div className="space-y-3">
            {pendingTransactions.map((tx) => (
              <div
                key={tx.id}
                className={clsx(
                  'p-4 border transition-all',
                  getTierBgColor(tx.tier)
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-white">{tx.agent_name}</span>
                      <span className="text-xs text-gray-500">→ {tx.merchant}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs px-2 py-0.5 bg-dark-300 text-gray-400 rounded font-mono">
                        {tx.id}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(tx.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-sardis-400 mono-numbers">
                      ${tx.amount.toFixed(2)}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-3 pb-3 border-b border-dark-100">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Confidence Score</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-dark-300 rounded-full h-2">
                        <div
                          className={clsx(
                            'h-2 rounded-full',
                            tx.confidence_score >= 0.95 && 'bg-sardis-500',
                            tx.confidence_score >= 0.85 && tx.confidence_score < 0.95 && 'bg-yellow-500',
                            tx.confidence_score >= 0.70 && tx.confidence_score < 0.85 && 'bg-orange-500',
                            tx.confidence_score < 0.70 && 'bg-red-500'
                          )}
                          style={{ width: `${tx.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className={clsx('text-sm font-bold mono-numbers', getTierColor(tx.tier))}>
                        {tx.confidence_score.toFixed(3)}
                      </span>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 mb-1">Routing Tier</p>
                    <div className={clsx('flex items-center gap-1.5', getTierColor(tx.tier))}>
                      {getTierIcon(tx.tier)}
                      <span className="text-sm font-medium capitalize">
                        {tx.tier.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 mb-1">Approvers Needed</p>
                    <p className="text-sm font-medium text-white">
                      {thresholds.find(t => t.tier === tx.tier)?.approvers_required || 0}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleApprove(tx.id)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-sardis-500 text-white hover:bg-sardis-600 transition-colors text-sm font-medium"
                  >
                    <ThumbsUp className="w-4 h-4" />
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(tx.id)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/30 transition-colors text-sm font-medium"
                  >
                    <ThumbsDown className="w-4 h-4" />
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Transactions */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Recent Transactions</h2>
            <p className="text-sm text-gray-400 mt-1">All transactions with confidence scores</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase border-b border-dark-100">
                <th className="pb-3 font-medium">Transaction</th>
                <th className="pb-3 font-medium">Agent</th>
                <th className="pb-3 font-medium">Merchant</th>
                <th className="pb-3 font-medium">Amount</th>
                <th className="pb-3 font-medium">Confidence</th>
                <th className="pb-3 font-medium">Tier</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-dark-200/50 transition-colors">
                  <td className="py-3">
                    <span className="text-xs font-mono text-gray-400">{tx.id}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-white">{tx.agent_name}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-gray-400">{tx.merchant}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-sardis-400 font-medium mono-numbers">
                      ${tx.amount.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-dark-300 rounded-full h-1.5">
                        <div
                          className={clsx(
                            'h-1.5 rounded-full',
                            tx.confidence_score >= 0.95 && 'bg-sardis-500',
                            tx.confidence_score >= 0.85 && tx.confidence_score < 0.95 && 'bg-yellow-500',
                            tx.confidence_score >= 0.70 && tx.confidence_score < 0.85 && 'bg-orange-500',
                            tx.confidence_score < 0.70 && 'bg-red-500'
                          )}
                          style={{ width: `${tx.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-white mono-numbers">
                        {tx.confidence_score.toFixed(3)}
                      </span>
                    </div>
                  </td>
                  <td className="py-3">
                    <div className={clsx('flex items-center gap-1.5', getTierColor(tx.tier))}>
                      {getTierIcon(tx.tier)}
                      <span className="text-xs capitalize">{tx.tier.replace('_', ' ')}</span>
                    </div>
                  </td>
                  <td className="py-3">{getStatusBadge(tx.status)}</td>
                  <td className="py-3">
                    <span className="text-xs text-gray-500">
                      {new Date(tx.created_at).toLocaleTimeString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
