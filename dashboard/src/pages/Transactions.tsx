import { useState, useEffect, useCallback } from 'react'
import { Search, ArrowUpRight, ArrowDownLeft, ExternalLink, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { ledgerApi } from '../api/client'

interface Transaction {
  tx_id: string
  from_wallet: string
  to_wallet: string
  amount: string
  fee: string
  currency: string
  purpose: string
  status: 'completed' | 'pending' | 'failed'
  created_at: string
}

type StatusFilter = 'all' | 'completed' | 'pending' | 'failed'

export default function TransactionsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await ledgerApi.recent(100)
      setTransactions(data as Transaction[])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions')
      setTransactions([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTransactions()
  }, [fetchTransactions])

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch = 
      tx.tx_id.toLowerCase().includes(search.toLowerCase()) ||
      tx.purpose?.toLowerCase().includes(search.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || tx.status === statusFilter
    
    return matchesSearch && matchesStatus
  })
  
  const totalVolume = transactions
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
            {transactions.length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Completed</p>
          <p className="text-2xl font-bold text-green-500">
            {transactions.filter(t => t.status === 'completed').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Failed</p>
          <p className="text-2xl font-bold text-red-500">
            {transactions.filter(t => t.status === 'failed').length}
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
      
      {/* Loading / Error States */}
      {loading && (
        <div className="card p-12 text-center">
          <Loader2 className="w-8 h-8 text-sardis-500 mx-auto mb-4 animate-spin" />
          <p className="text-gray-400">Loading transactions...</p>
        </div>
      )}

      {error && (
        <div className="card p-6 border-red-500/30">
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={fetchTransactions} className="mt-2 text-sm text-sardis-500 hover:underline">
            Retry
          </button>
        </div>
      )}

      {/* Transactions Table */}
      {!loading && !error && <div className="card overflow-hidden">
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
      </div>}
    </div>
  )
}

