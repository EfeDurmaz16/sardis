import { useState, useEffect } from 'react'
import { Search, Clock, CheckCircle, XCircle, AlertTriangle, Lock, Unlock } from 'lucide-react'
import clsx from 'clsx'
import { format, formatDistanceToNow } from 'date-fns'

// Mock holds data
const mockHolds = [
  {
    hold_id: 'hold_a1b2c3d4e5f6',
    agent_id: 'agent_compute_001',
    merchant_id: 'gpu_provider_1',
    amount: '50.00',
    currency: 'USDC',
    purpose: 'GPU Computing: LLM inference job',
    status: 'active' as const,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 1800000).toISOString(), // 30 min
    captured_amount: null,
  },
  {
    hold_id: 'hold_g7h8i9j0k1l2',
    agent_id: 'agent_shopping_002',
    merchant_id: 'electronics_store',
    amount: '199.99',
    currency: 'USDC',
    purpose: 'Pre-auth for electronics purchase',
    status: 'active' as const,
    created_at: new Date(Date.now() - 600000).toISOString(),
    expires_at: new Date(Date.now() + 3600000).toISOString(),
    captured_amount: null,
  },
  {
    hold_id: 'hold_m3n4o5p6q7r8',
    agent_id: 'agent_data_003',
    merchant_id: 'data_provider',
    amount: '25.00',
    currency: 'USDC',
    purpose: 'API access pre-authorization',
    status: 'captured' as const,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    expires_at: new Date(Date.now() - 1800000).toISOString(),
    captured_amount: '22.50',
  },
  {
    hold_id: 'hold_s9t0u1v2w3x4',
    agent_id: 'agent_compute_001',
    merchant_id: 'gpu_provider_2',
    amount: '100.00',
    currency: 'USDC',
    purpose: 'Large compute job - cancelled',
    status: 'voided' as const,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    expires_at: new Date(Date.now() - 3600000).toISOString(),
    captured_amount: null,
  },
  {
    hold_id: 'hold_y5z6a7b8c9d0',
    agent_id: 'agent_shopping_004',
    merchant_id: 'subscription_service',
    amount: '15.00',
    currency: 'USDC',
    purpose: 'Monthly subscription hold',
    status: 'expired' as const,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    expires_at: new Date(Date.now() - 43200000).toISOString(),
    captured_amount: null,
  },
]

type StatusFilter = 'all' | 'active' | 'captured' | 'voided' | 'expired'

export default function HoldsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [now, setNow] = useState(new Date())
  
  // Update time every minute for expiry countdown
  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(interval)
  }, [])
  
  const filteredHolds = mockHolds.filter(hold => {
    const matchesSearch = 
      hold.hold_id.toLowerCase().includes(search.toLowerCase()) ||
      hold.agent_id.toLowerCase().includes(search.toLowerCase()) ||
      hold.purpose?.toLowerCase().includes(search.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || hold.status === statusFilter
    
    return matchesSearch && matchesStatus
  })
  
  const activeHoldsValue = mockHolds
    .filter(h => h.status === 'active')
    .reduce((sum, h) => sum + parseFloat(h.amount), 0)
  
  const getTimeRemaining = (expiresAt: string) => {
    const expires = new Date(expiresAt)
    if (expires < now) return 'Expired'
    return formatDistanceToNow(expires, { addSuffix: true })
  }
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <Lock className="w-4 h-4" />
      case 'captured':
        return <CheckCircle className="w-4 h-4" />
      case 'voided':
        return <XCircle className="w-4 h-4" />
      case 'expired':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <Clock className="w-4 h-4" />
    }
  }
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Payment Holds</h1>
        <p className="text-gray-400 mt-1">
          Manage pre-authorizations and fund holds
        </p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4 border-l-4 border-l-yellow-500">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <Lock className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Active Holds</p>
              <p className="text-2xl font-bold text-white">
                {mockHolds.filter(h => h.status === 'active').length}
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Held Amount</p>
          <p className="text-2xl font-bold text-yellow-500 mono-numbers">
            ${activeHoldsValue.toFixed(2)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Captured Today</p>
          <p className="text-2xl font-bold text-green-500">
            {mockHolds.filter(h => h.status === 'captured').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Voided/Expired</p>
          <p className="text-2xl font-bold text-gray-500">
            {mockHolds.filter(h => h.status === 'voided' || h.status === 'expired').length}
          </p>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search holds..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        
        <div className="flex gap-2 flex-wrap">
          {(['all', 'active', 'captured', 'voided', 'expired'] as StatusFilter[]).map(status => (
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
      
      {/* Holds Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-dark-300">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Hold ID
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Agent
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Purpose
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Expires
              </th>
              <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-100">
            {filteredHolds.map((hold) => (
              <tr key={hold.hold_id} className="hover:bg-dark-200/50 transition-colors">
                <td className="px-6 py-4">
                  <p className="text-sm font-mono text-white">{hold.hold_id}</p>
                  <p className="text-xs text-gray-500">
                    {format(new Date(hold.created_at), 'MMM d, HH:mm')}
                  </p>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-white">{hold.agent_id}</p>
                  <p className="text-xs text-gray-500">{hold.merchant_id}</p>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm font-medium text-white mono-numbers">
                    ${hold.amount} {hold.currency}
                  </p>
                  {hold.captured_amount && (
                    <p className="text-xs text-green-500">
                      Captured: ${hold.captured_amount}
                    </p>
                  )}
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-300 max-w-xs truncate">
                    {hold.purpose || '-'}
                  </p>
                </td>
                <td className="px-6 py-4">
                  <span className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                    hold.status === 'active' && 'bg-yellow-500/10 text-yellow-500',
                    hold.status === 'captured' && 'bg-green-500/10 text-green-500',
                    hold.status === 'voided' && 'bg-gray-500/10 text-gray-500',
                    hold.status === 'expired' && 'bg-red-500/10 text-red-500'
                  )}>
                    {getStatusIcon(hold.status)}
                    {hold.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <p className={clsx(
                    'text-sm',
                    hold.status === 'active' ? 'text-yellow-500' : 'text-gray-400'
                  )}>
                    {hold.status === 'active' ? getTimeRemaining(hold.expires_at) : '-'}
                  </p>
                </td>
                <td className="px-6 py-4 text-right">
                  {hold.status === 'active' && (
                    <div className="flex gap-2 justify-end">
                      <button className="px-3 py-1.5 bg-green-500/10 text-green-500 rounded-lg text-xs font-medium hover:bg-green-500/20 transition-colors">
                        Capture
                      </button>
                      <button className="px-3 py-1.5 bg-red-500/10 text-red-500 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-colors">
                        Void
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filteredHolds.length === 0 && (
          <div className="p-12 text-center">
            <Lock className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No holds found</p>
          </div>
        )}
      </div>
    </div>
  )
}

