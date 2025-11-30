import { useState } from 'react'
import { Search, Filter, ArrowUpRight, ArrowDownLeft, ExternalLink } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'

// Mock transactions for demo
const mockTransactions = [
  {
    tx_id: 'tx_a1b2c3d4e5f6',
    from_wallet: 'wallet_agent_001',
    to_wallet: 'wallet_merchant_tech',
    amount: '25.50',
    fee: '0.10',
    currency: 'USDC',
    purpose: 'Premium Headphones Purchase',
    status: 'completed' as const,
    created_at: new Date().toISOString(),
  },
  {
    tx_id: 'tx_g7h8i9j0k1l2',
    from_wallet: 'wallet_agent_002',
    to_wallet: 'wallet_merchant_data',
    amount: '15.00',
    fee: '0.10',
    currency: 'USDC',
    purpose: 'Weather API Access',
    status: 'completed' as const,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    tx_id: 'tx_m3n4o5p6q7r8',
    from_wallet: 'wallet_agent_003',
    to_wallet: 'wallet_merchant_office',
    amount: '42.00',
    fee: '0.10',
    currency: 'USDC',
    purpose: 'Office Supplies Order',
    status: 'pending' as const,
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    tx_id: 'tx_s9t0u1v2w3x4',
    from_wallet: 'wallet_agent_001',
    to_wallet: 'wallet_merchant_tech',
    amount: '89.99',
    fee: '0.10',
    currency: 'USDC',
    purpose: 'Mechanical Keyboard',
    status: 'failed' as const,
    created_at: new Date(Date.now() - 14400000).toISOString(),
  },
  {
    tx_id: 'tx_y5z6a7b8c9d0',
    from_wallet: 'wallet_agent_004',
    to_wallet: 'wallet_agent_005',
    amount: '5.00',
    fee: '0.10',
    currency: 'USDC',
    purpose: 'Agent-to-Agent Transfer',
    status: 'completed' as const,
    created_at: new Date(Date.now() - 21600000).toISOString(),
  },
]

type StatusFilter = 'all' | 'completed' | 'pending' | 'failed'

export default function TransactionsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  
  const filteredTransactions = mockTransactions.filter(tx => {
    const matchesSearch = 
      tx.tx_id.toLowerCase().includes(search.toLowerCase()) ||
      tx.purpose?.toLowerCase().includes(search.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || tx.status === statusFilter
    
    return matchesSearch && matchesStatus
  })
  
  const totalVolume = mockTransactions
    .filter(tx => tx.status === 'completed')
    .reduce((sum, tx) => sum + parseFloat(tx.amount), 0)
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Transactions</h1>
        <p className="text-gray-400 mt-1">
          View all payment activity
        </p>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Volume</p>
          <p className="text-2xl font-bold text-white mono-numbers">
            ${totalVolume.toFixed(2)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Transactions</p>
          <p className="text-2xl font-bold text-white">
            {mockTransactions.length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Completed</p>
          <p className="text-2xl font-bold text-green-500">
            {mockTransactions.filter(t => t.status === 'completed').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Failed</p>
          <p className="text-2xl font-bold text-red-500">
            {mockTransactions.filter(t => t.status === 'failed').length}
          </p>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search transactions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        
        <div className="flex gap-2">
          {(['all', 'completed', 'pending', 'failed'] as StatusFilter[]).map(status => (
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
      
      {/* Transactions Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-dark-300">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Transaction
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
                Time
              </th>
              <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-100">
            {filteredTransactions.map((tx) => (
              <tr key={tx.tx_id} className="hover:bg-dark-200/50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center',
                      tx.from_wallet.includes('agent') 
                        ? 'bg-red-500/10 text-red-500'
                        : 'bg-green-500/10 text-green-500'
                    )}>
                      {tx.from_wallet.includes('agent') 
                        ? <ArrowUpRight className="w-4 h-4" />
                        : <ArrowDownLeft className="w-4 h-4" />
                      }
                    </div>
                    <div>
                      <p className="text-sm font-mono text-white">{tx.tx_id}</p>
                      <p className="text-xs text-gray-500">
                        {tx.from_wallet.slice(0, 20)}...
                      </p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm font-medium text-white mono-numbers">
                    ${tx.amount} {tx.currency}
                  </p>
                  <p className="text-xs text-gray-500">
                    Fee: ${tx.fee}
                  </p>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-300 max-w-xs truncate">
                    {tx.purpose || '-'}
                  </p>
                </td>
                <td className="px-6 py-4">
                  <span className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                    tx.status === 'completed' && 'bg-green-500/10 text-green-500',
                    tx.status === 'pending' && 'bg-yellow-500/10 text-yellow-500',
                    tx.status === 'failed' && 'bg-red-500/10 text-red-500'
                  )}>
                    <div className={clsx(
                      'w-1.5 h-1.5 rounded-full',
                      tx.status === 'completed' && 'bg-green-500',
                      tx.status === 'pending' && 'bg-yellow-500 animate-pulse',
                      tx.status === 'failed' && 'bg-red-500'
                    )} />
                    {tx.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <p className="text-sm text-gray-400">
                    {format(new Date(tx.created_at), 'MMM d, HH:mm')}
                  </p>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="p-2 text-gray-400 hover:text-white transition-colors">
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filteredTransactions.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-gray-400">No transactions found</p>
          </div>
        )}
      </div>
    </div>
  )
}

