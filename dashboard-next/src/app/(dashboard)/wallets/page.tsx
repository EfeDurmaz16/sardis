"use client";

import { useState } from 'react'
import {
  Wallet,
  Search,
  Plus,
  ArrowRight,
  Copy,
  Check,
  ExternalLink,
  Shield,
  DollarSign,
  X,
  Activity,
} from 'lucide-react'
import Link from 'next/link'
import clsx from 'clsx'
import { useWallets } from '@/hooks/useApi'

type WalletItem = {
  wallet_id: string
  agent_id?: string
  balance: string
  currency: string
  limit_per_tx?: string
  limit_total?: string
  spent_total?: string
  remaining_limit?: string
  is_active: boolean
  chain_address?: string
  created_at?: string
}

export default function WalletsPage() {
  const { data: apiWallets = [], isLoading } = useWallets()
  const [search, setSearch] = useState('')
  const [selectedWallet, setSelectedWallet] = useState<WalletItem | null>(null)

  const wallets: WalletItem[] = apiWallets as WalletItem[]
  const filtered = wallets.filter(
    (w) =>
      w.wallet_id?.toLowerCase().includes(search.toLowerCase()) ||
      w.agent_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Wallets</h1>
          <p className="text-gray-400 mt-1">Manage and fund your agent wallets</p>
        </div>
        <Link
          href="/wallets/fund"
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
        >
          <Plus className="w-5 h-5" />
          Add Funds
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <input
          type="text"
          placeholder="Search wallets by ID or agent..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
        />
      </div>

      {/* Wallet list */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-4 bg-dark-100 rounded w-3/4 mb-4" />
              <div className="h-3 bg-dark-100 rounded w-1/2 mb-2" />
              <div className="h-3 bg-dark-100 rounded w-1/4" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Wallet className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            {search ? 'No wallets found' : 'No wallets yet'}
          </h3>
          <p className="text-gray-400 mb-4">
            {search
              ? 'Try a different search term'
              : 'Create an agent to automatically provision a wallet'}
          </p>
          {!search && (
            <Link
              href="/agents"
              className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((wallet) => (
            <WalletCard
              key={wallet.wallet_id}
              wallet={wallet}
              onView={() => setSelectedWallet(wallet)}
            />
          ))}
        </div>
      )}

      {/* Detail panel */}
      {selectedWallet && (
        <WalletDetailPanel
          wallet={selectedWallet}
          onClose={() => setSelectedWallet(null)}
        />
      )}
    </div>
  )
}

function WalletCard({
  wallet,
  onView,
}: {
  wallet: WalletItem
  onView: () => void
}) {
  const balance = parseFloat(wallet.balance || '0')
  const [copied, setCopied] = useState(false)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(wallet.wallet_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card card-hover p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <Wallet className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-mono text-white truncate max-w-[140px]">
                {wallet.wallet_id}
              </p>
              <button
                onClick={handleCopy}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-sardis-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
            {wallet.agent_id && (
              <p className="text-xs text-gray-500">Agent: {wallet.agent_id}</p>
            )}
          </div>
        </div>
        <div className={clsx('status-dot', wallet.is_active ? 'success' : 'error')} />
      </div>

      {/* Balance */}
      <div className="bg-dark-200 rounded-lg p-3 mb-4">
        <p className="text-xs text-gray-500 mb-0.5">Balance</p>
        <p className="text-xl font-bold text-white mono-numbers">
          ${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          <span className="text-sm text-gray-500 font-normal ml-1">{wallet.currency || 'USDC'}</span>
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-dark-100">
        <Link
          href={`/wallets/fund?wallet=${wallet.wallet_id}`}
          className="flex items-center gap-1 text-sm text-sardis-400 hover:text-sardis-300 transition-colors px-3 py-1.5 bg-sardis-500/10 rounded-lg hover:bg-sardis-500/20"
        >
          <DollarSign className="w-4 h-4" />
          Add Funds
        </Link>
        <button
          onClick={onView}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5 hover:bg-dark-100 rounded-lg"
        >
          Details
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

function WalletDetailPanel({
  wallet,
  onClose,
}: {
  wallet: WalletItem
  onClose: () => void
}) {
  const balance = parseFloat(wallet.balance || '0')
  const spent = parseFloat(wallet.spent_total || '0')
  const limitTotal = parseFloat(wallet.limit_total || '0')
  const remaining = parseFloat(wallet.remaining_limit || '0')
  const usagePercent = limitTotal > 0 ? Math.min((spent / limitTotal) * 100, 100) : 0

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute top-0 right-0 h-full w-full max-w-md bg-dark-300 border-l border-dark-100 shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-100">
          <h2 className="text-xl font-bold text-white font-display">Wallet Details</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-dark-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Wallet ID */}
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-sardis-500/10 rounded-lg flex items-center justify-center">
              <Wallet className="w-6 h-6 text-sardis-400" />
            </div>
            <div>
              <p className="text-sm font-mono text-white">{wallet.wallet_id}</p>
              <p className="text-xs text-gray-500">
                {wallet.is_active ? 'Active' : 'Inactive'} --{' '}
                {wallet.currency || 'USDC'}
              </p>
            </div>
          </div>

          {/* Balance card */}
          <div className="bg-dark-200 rounded-lg p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Current Balance</p>
            <p className="text-3xl font-bold text-white mono-numbers">
              ${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <Link
              href={`/wallets/fund?wallet=${wallet.wallet_id}`}
              className="inline-flex items-center gap-2 mt-3 text-sm text-sardis-400 hover:text-sardis-300 transition-colors"
            >
              <DollarSign className="w-4 h-4" />
              Add Funds
            </Link>
          </div>

          {/* Spending */}
          <div className="bg-dark-200 rounded-lg p-4 space-y-3">
            <h4 className="text-sm font-medium text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-sardis-400" />
              Spending Limits
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Per Transaction</span>
                <span className="text-sm text-white font-mono">
                  {wallet.limit_per_tx ? `$${wallet.limit_per_tx}` : 'Not set'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Total Limit</span>
                <span className="text-sm text-white font-mono">
                  {wallet.limit_total ? `$${wallet.limit_total}` : 'Not set'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Spent</span>
                <span className="text-sm text-white font-mono">${spent.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Remaining</span>
                <span className="text-sm text-sardis-400 font-mono">${remaining.toFixed(2)}</span>
              </div>

              {/* Usage bar */}
              {limitTotal > 0 && (
                <div className="pt-2">
                  <div className="w-full h-2 bg-dark-300 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full transition-all',
                        usagePercent > 80 ? 'bg-red-500' : usagePercent > 50 ? 'bg-yellow-500' : 'bg-sardis-500'
                      )}
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{usagePercent.toFixed(0)}% used</p>
                </div>
              )}
            </div>
          </div>

          {/* Agent */}
          {wallet.agent_id && (
            <div className="flex items-center gap-3">
              <Activity className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-400">Agent</span>
              <span className="ml-auto text-sm text-gray-300 font-mono">{wallet.agent_id}</span>
            </div>
          )}

          {/* Chain address */}
          {wallet.chain_address && (
            <div className="flex items-center gap-3">
              <ExternalLink className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-400">On-chain</span>
              <a
                href={`https://basescan.org/address/${wallet.chain_address}`}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-sm text-sardis-400 hover:text-sardis-300 font-mono truncate max-w-[180px]"
              >
                {wallet.chain_address}
              </a>
            </div>
          )}

          {/* Created */}
          {wallet.created_at && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400">Created</span>
              <span className="ml-auto text-sm text-gray-300">
                {new Date(wallet.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </span>
            </div>
          )}

          {/* Fund CTA */}
          <Link
            href={`/wallets/fund?wallet=${wallet.wallet_id}`}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
          >
            <DollarSign className="w-5 h-5" />
            Add Funds
          </Link>
        </div>
      </div>
    </div>
  )
}
