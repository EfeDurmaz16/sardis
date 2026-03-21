/**
 * MPP Sessions — View and manage Machine Payments Protocol sessions
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Loader2,
  Search,
  Zap,
  Clock,
  DollarSign,
  Hash,
} from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { mppApi } from '../api/client'

/* ─── Types ─── */

interface MPPSession {
  session_id: string
  status: 'active' | 'closed' | 'expired' | 'exhausted'
  spending_limit: string
  remaining: string
  payment_count: number
  created_at: string
  updated_at?: string
  agent_id?: string
  description?: string
}

/* ─── Status Badge ─── */

function StatusBadge({ status }: { status: MPPSession['status'] }) {
  const config: Record<string, { bg: string; text: string; dot: string }> = {
    active: { bg: 'bg-green-500/10', text: 'text-green-500', dot: 'bg-green-500' },
    closed: { bg: 'bg-gray-500/10', text: 'text-gray-400', dot: 'bg-gray-400' },
    expired: { bg: 'bg-amber-500/10', text: 'text-amber-500', dot: 'bg-amber-500' },
    exhausted: { bg: 'bg-red-500/10', text: 'text-red-500', dot: 'bg-red-500' },
  }
  const c = config[status] || config.closed
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize', c.bg, c.text)}>
      <div className={clsx('w-1.5 h-1.5 rounded-full', c.dot)} />
      {status}
    </span>
  )
}

/* ─── Budget Bar ─── */

function BudgetBar({ remaining, limit }: { remaining: string; limit: string }) {
  const r = parseFloat(remaining)
  const l = parseFloat(limit)
  if (l <= 0) return <span className="text-xs text-gray-500">No limit</span>
  const spent = l - r
  const pct = Math.min(100, (spent / l) * 100)
  return (
    <div className="space-y-1 w-full">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">${spent.toFixed(2)} spent</span>
        <span className="text-gray-500">${l.toFixed(2)} limit</span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-dark-100">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            background: pct > 80 ? '#EF4444' : pct > 60 ? '#F59E0B' : '#22C55E',
          }}
        />
      </div>
    </div>
  )
}

/* ─── Main Page ─── */

type StatusFilter = 'all' | 'active' | 'closed' | 'expired' | 'exhausted'

export default function MPPSessionsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const { data: sessions = [], isLoading, error } = useQuery<MPPSession[]>({
    queryKey: ['mpp-sessions'],
    queryFn: mppApi.listSessions,
  })

  const filteredSessions = sessions.filter(s => {
    const matchesSearch =
      s.session_id.toLowerCase().includes(search.toLowerCase()) ||
      (s.agent_id || '').toLowerCase().includes(search.toLowerCase()) ||
      (s.description || '').toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || s.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const activeSessions = sessions.filter(s => s.status === 'active').length
  const totalLimit = sessions.reduce((s, m) => s + parseFloat(m.spending_limit || '0'), 0)
  const totalRemaining = sessions.reduce((s, m) => s + parseFloat(m.remaining || '0'), 0)
  const totalPayments = sessions.reduce((s, m) => s + m.payment_count, 0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
          <Zap className="w-8 h-8 text-sardis-400" />
          MPP Sessions
        </h1>
        <p className="text-gray-400 mt-1">
          Machine Payments Protocol session management
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Active Sessions</p>
              <p className="text-2xl font-bold text-green-500">{activeSessions}</p>
            </div>
            <Zap className="w-8 h-8 text-green-500/30" />
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Total Limit</p>
              <p className="text-2xl font-bold text-white mono-numbers">${totalLimit.toFixed(2)}</p>
            </div>
            <DollarSign className="w-8 h-8 text-sardis-400/30" />
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Remaining</p>
              <p className="text-2xl font-bold text-sardis-400 mono-numbers">${totalRemaining.toFixed(2)}</p>
            </div>
            <DollarSign className="w-8 h-8 text-blue-400/30" />
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Total Payments</p>
              <p className="text-2xl font-bold text-white">{totalPayments}</p>
            </div>
            <Hash className="w-8 h-8 text-purple-400/30" />
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search by session ID, agent, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'active', 'closed', 'expired', 'exhausted'] as StatusFilter[]).map(status => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize',
                statusFilter === status
                  ? 'bg-sardis-500 text-dark-400'
                  : 'bg-dark-200 text-gray-400 hover:bg-dark-100'
              )}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="card p-12 text-center">
          <Loader2 className="w-8 h-8 text-sardis-500 mx-auto mb-4 animate-spin" />
          <p className="text-gray-400">Loading MPP sessions...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card p-6 border-red-500/30">
          <p className="text-red-400 text-sm">
            {error instanceof Error ? error.message : 'Failed to load MPP sessions'}
          </p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !error && sessions.length === 0 && (
        <div className="card p-12 text-center">
          <Zap className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-2">No MPP sessions found</p>
          <p className="text-sm text-gray-500">
            MPP sessions will appear here when agents initiate Machine Payments Protocol flows.
          </p>
        </div>
      )}

      {/* Sessions Table */}
      {!isLoading && !error && filteredSessions.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-dark-300">
              <tr>
                <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Session
                </th>
                <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Budget
                </th>
                <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Payments
                </th>
                <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {filteredSessions.map((session) => (
                <tr
                  key={session.session_id}
                  className="hover:bg-dark-200/50 transition-colors"
                >
                  <td className="px-4 py-4">
                    <div>
                      <p className="text-sm font-mono text-white">{session.session_id}</p>
                      {session.agent_id && (
                        <p className="text-xs text-gray-500 font-mono mt-0.5">{session.agent_id}</p>
                      )}
                      {session.description && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">{session.description}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={session.status} />
                  </td>
                  <td className="px-4 py-4 min-w-[200px]">
                    <BudgetBar remaining={session.remaining} limit={session.spending_limit} />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-gray-500" />
                      <span className="text-sm text-white mono-numbers">{session.payment_count}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-gray-500" />
                      <span className="text-sm text-gray-400">
                        {format(new Date(session.created_at), 'MMM d, HH:mm')}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredSessions.length === 0 && (
            <div className="p-12 text-center">
              <p className="text-gray-400">No sessions match your filters</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
