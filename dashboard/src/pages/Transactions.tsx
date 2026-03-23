import { useState, useEffect, useCallback } from 'react'
import { Search, ArrowUpRight, ArrowDownLeft, ExternalLink, Loader2, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { ledgerApi } from '../api/client'

// Chain explorer URLs
const CHAIN_EXPLORERS: Record<string, string> = {
  base: 'https://basescan.org',
  base_sepolia: 'https://sepolia.basescan.org',
  polygon: 'https://polygonscan.com',
  arbitrum: 'https://arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  ethereum: 'https://etherscan.io',
}

function getExplorerTxUrl(chain: string | undefined, txHash: string | undefined): string | null {
  if (!chain || !txHash) return null
  const base = CHAIN_EXPLORERS[chain]
  return base ? `${base}/tx/${txHash}` : null
}

// Chain badge colors
const CHAIN_COLORS: Record<string, string> = {
  base: '#0052FF',
  base_sepolia: '#0052FF',
  polygon: '#8247E5',
  arbitrum: '#28A0F0',
  optimism: '#FF0420',
  ethereum: '#627EEA',
}

function ChainBadge({ chain }: { chain?: string }) {
  if (!chain) return null
  const color = CHAIN_COLORS[chain] || '#808080'
  const label = chain.replace('_sepolia', ' (testnet)')
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium capitalize"
      style={{ background: `${color}20`, color, border: `1px solid ${color}30` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  )
}

function CopyButton({ text, size = 14 }: { text: string; size?: number }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button onClick={handleCopy} className="p-1 text-gray-500 hover:text-white transition-colors" title="Copy">
      {copied ? <Check size={size} className="text-green-400" /> : <Copy size={size} />}
    </button>
  )
}

function truncateHash(hash: string, chars = 6): string {
  if (hash.length <= chars * 2 + 2) return hash
  return `${hash.slice(0, chars + 2)}...${hash.slice(-chars)}`
}

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
  chain?: string
  chain_tx_hash?: string
  tx_hash?: string
  block_number?: number
  gas_used?: string
}

type StatusFilter = 'all' | 'completed' | 'pending' | 'failed'

export default function TransactionsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedTxId, setExpandedTxId] = useState<string | null>(null)

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
      tx.purpose?.toLowerCase().includes(search.toLowerCase()) ||
      (tx.chain_tx_hash || '').toLowerCase().includes(search.toLowerCase())

    const matchesStatus = statusFilter === 'all' || tx.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const totalVolume = transactions
    .filter(tx => tx.status === 'completed')
    .reduce((sum, tx) => sum + parseFloat(tx.amount), 0)

  const toggleExpand = (txId: string) => {
    setExpandedTxId(prev => prev === txId ? null : txId)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Transactions</h1>
        <p className="text-gray-400 mt-1">
          View all payment activity with on-chain details
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
            placeholder="Search by TX ID, purpose, or hash..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:border-sardis-500/50"
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
          <caption className="sr-only">Transaction history</caption>
          <thead className="bg-dark-300">
            <tr>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-8" />
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Transaction
              </th>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Chain
              </th>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Purpose
              </th>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Time
              </th>
              <th className="px-4 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Explorer
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-100">
            {filteredTransactions.map((tx) => {
              const txHash = tx.chain_tx_hash || tx.tx_hash
              const explorerUrl = getExplorerTxUrl(tx.chain, txHash)
              const isExpanded = expandedTxId === tx.tx_id

              return (
                <>
                  <tr
                    key={tx.tx_id}
                    className={clsx(
                      'hover:bg-dark-200/50 transition-colors cursor-pointer',
                      isExpanded && 'bg-dark-200/30'
                    )}
                    onClick={() => toggleExpand(tx.tx_id)}
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleExpand(tx.tx_id); } }}
                  >
                    <td className="px-4 py-4">
                      {isExpanded
                        ? <ChevronDown className="w-4 h-4 text-gray-500" />
                        : <ChevronRight className="w-4 h-4 text-gray-500" />
                      }
                    </td>
                    <td className="px-4 py-4">
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
                          <div className="flex items-center gap-1">
                            <p className="text-sm font-mono text-white">{tx.tx_id}</p>
                            <CopyButton text={tx.tx_id} size={12} />
                          </div>
                          {txHash && (
                            <div className="flex items-center gap-1">
                              <p className="text-xs font-mono text-gray-500">{truncateHash(txHash)}</p>
                              <CopyButton text={txHash} size={10} />
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <ChainBadge chain={tx.chain} />
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm font-medium text-white mono-numbers">
                        ${tx.amount} {tx.currency}
                      </p>
                      {tx.fee && tx.fee !== '0' && (
                        <p className="text-xs text-gray-500">
                          Fee: ${tx.fee}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <p className="text-sm text-gray-300 max-w-xs truncate">
                        {tx.purpose || '-'}
                      </p>
                    </td>
                    <td className="px-4 py-4">
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
                    <td className="px-4 py-4">
                      <p className="text-sm text-gray-400">
                        {format(new Date(tx.created_at), 'MMM d, HH:mm')}
                      </p>
                    </td>
                    <td className="px-4 py-4 text-right" onClick={e => e.stopPropagation()}>
                      {explorerUrl ? (
                        <a
                          href={explorerUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 text-sardis-400 hover:text-white transition-colors inline-flex"
                          title="View on explorer"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      ) : (
                        <span className="p-2 text-gray-600 inline-flex" title="No on-chain data">
                          <ExternalLink className="w-4 h-4" />
                        </span>
                      )}
                    </td>
                  </tr>

                  {/* Expandable Detail Panel */}
                  {isExpanded && (
                    <tr key={`${tx.tx_id}-detail`}>
                      <td colSpan={8} className="px-6 py-4 bg-dark-300/50">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          {/* Transaction Details */}
                          <div>
                            <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Transaction Details</h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-500">TX ID</span>
                                <div className="flex items-center gap-1">
                                  <span className="font-mono text-white">{tx.tx_id}</span>
                                  <CopyButton text={tx.tx_id} size={12} />
                                </div>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-500">From</span>
                                <span className="font-mono text-gray-300 text-xs">{tx.from_wallet}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-500">To</span>
                                <span className="font-mono text-gray-300 text-xs">{tx.to_wallet || '-'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-500">Amount</span>
                                <span className="text-white">${tx.amount} {tx.currency}</span>
                              </div>
                              {tx.fee && tx.fee !== '0' && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">Fee</span>
                                  <span className="text-gray-300">${tx.fee}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Chain Details */}
                          <div>
                            <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Chain Details</h4>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-500">Chain</span>
                                <ChainBadge chain={tx.chain} />
                              </div>
                              {txHash && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">TX Hash</span>
                                  <div className="flex items-center gap-1">
                                    <span className="font-mono text-xs text-gray-300">{truncateHash(txHash, 8)}</span>
                                    <CopyButton text={txHash} size={12} />
                                  </div>
                                </div>
                              )}
                              {tx.block_number && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">Block</span>
                                  <span className="font-mono text-gray-300">#{tx.block_number}</span>
                                </div>
                              )}
                              {tx.gas_used && (
                                <div className="flex justify-between">
                                  <span className="text-gray-500">Gas Used</span>
                                  <span className="font-mono text-gray-300">{tx.gas_used}</span>
                                </div>
                              )}
                              {explorerUrl && (
                                <a
                                  href={explorerUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sardis-400 hover:text-sardis-300 text-xs flex items-center gap-1"
                                >
                                  View on block explorer <ExternalLink size={12} />
                                </a>
                              )}
                            </div>
                          </div>

                          {/* Timeline */}
                          <div>
                            <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">Lifecycle</h4>
                            <div className="space-y-3">
                              {[
                                { label: 'Created', done: true },
                                { label: 'Policy Check', done: tx.status !== 'failed' || true },
                                { label: 'Submitted', done: tx.status === 'completed' || tx.status === 'pending' },
                                { label: 'Confirmed', done: tx.status === 'completed' },
                              ].map((step, i) => (
                                <div key={step.label} className="flex items-center gap-2">
                                  <div className={clsx(
                                    'w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold',
                                    step.done ? 'bg-green-500/20 text-green-500' : 'bg-dark-100 text-gray-600'
                                  )}>
                                    {step.done ? '✓' : i + 1}
                                  </div>
                                  <span className={clsx('text-sm', step.done ? 'text-gray-300' : 'text-gray-600')}>
                                    {step.label}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
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
