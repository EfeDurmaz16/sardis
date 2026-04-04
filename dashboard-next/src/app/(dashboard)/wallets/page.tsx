"use client";

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Wallet,
  Search,
  Plus,
  ArrowRight,
  ArrowLeftRight,
  Copy,
  Check,
  ExternalLink,
  Shield,
  DollarSign,
  Activity,
  Loader2,
  CreditCard,
  ChevronDown,
  X,
} from 'lucide-react'
import Link from 'next/link'
import clsx from 'clsx'
import { useWallets } from '@/hooks/useApi'
import { walletsApi, bridgeApi } from '@/api/client'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuSeparator, ContextMenuTrigger } from "@/components/ui/context-menu"

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

const BRIDGE_CHAINS = [
  { chain_id: 8453, name: 'Base', icon: '🔵' },
  { chain_id: 4217, name: 'Tempo', icon: '⚡' },
  { chain_id: 1, name: 'Ethereum', icon: '💠' },
  { chain_id: 137, name: 'Polygon', icon: '🟣' },
  { chain_id: 42161, name: 'Arbitrum', icon: '🔷' },
  { chain_id: 10, name: 'Optimism', icon: '🔴' },
] as const

type BridgeStatus = 'idle' | 'quoting' | 'executing' | 'polling' | 'success' | 'error'

export default function WalletsPage() {
  const { data: apiWallets = [], isLoading } = useWallets()
  const [search, setSearch] = useState('')
  const [selectedWallet, setSelectedWallet] = useState<WalletItem | null>(null)
  const [bridgeWallet, setBridgeWallet] = useState<WalletItem | null>(null)

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
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-white font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
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
              onBridge={() => setBridgeWallet(wallet)}
            />
          ))}
        </div>
      )}

      {/* Detail panel */}
      <WalletDetailPanel
        wallet={selectedWallet}
        open={!!selectedWallet}
        onOpenChange={(open) => { if (!open) setSelectedWallet(null) }}
        onBridge={(w) => { setSelectedWallet(null); setBridgeWallet(w) }}
      />

      {/* Bridge modal */}
      <BridgeModal
        wallet={bridgeWallet}
        open={!!bridgeWallet}
        onClose={() => setBridgeWallet(null)}
      />
    </div>
  )
}

function WalletCard({
  wallet,
  onView,
  onBridge,
}: {
  wallet: WalletItem
  onView: () => void
  onBridge: () => void
}) {
  const balance = parseFloat(wallet.balance || '0')
  const [copied, setCopied] = useState(false)
  const [fundingWallet, setFundingWallet] = useState(false)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(wallet.wallet_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleStripeFund = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const address = wallet.chain_address
    if (!address) {
      window.location.href = `/wallets/fund?wallet=${wallet.wallet_id}`
      return
    }
    // Build Stripe hosted onramp URL directly — no API call needed
    const params = new URLSearchParams({
      destination_currency: 'usdc',
      destination_network: 'base',
      source_currency: 'usd',
      'wallet_addresses[ethereum]': address,
    })
    window.open(`https://crypto.link.com?${params.toString()}`, '_blank', 'noopener,noreferrer')
  }, [wallet.wallet_id, wallet.chain_address])

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
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
            <div className="flex items-center gap-2">
              <button
                onClick={handleStripeFund}
                disabled={fundingWallet}
                className="flex items-center gap-1 text-sm text-sardis-400 hover:text-sardis-300 transition-colors px-3 py-1.5 bg-sardis-500/10 rounded-lg hover:bg-sardis-500/20 disabled:opacity-50"
                title="Buy USDC via Stripe (opens in new tab)"
              >
                {fundingWallet ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CreditCard className="w-4 h-4" />
                )}
                Fund
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onBridge() }}
                className="flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors px-3 py-1.5 bg-blue-500/10 rounded-lg hover:bg-blue-500/20"
                title="Bridge USDC to another chain"
              >
                <ArrowLeftRight className="w-4 h-4" />
                Bridge
              </button>
            </div>
            <button
              onClick={onView}
              className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5 hover:bg-dark-100 rounded-lg"
            >
              Details
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={() => navigator.clipboard.writeText(wallet.wallet_id)}>Copy Wallet ID</ContextMenuItem>
        {wallet.chain_address && <ContextMenuItem onClick={() => navigator.clipboard.writeText(wallet.chain_address!)}>Copy Chain Address</ContextMenuItem>}
        <ContextMenuItem onClick={onView}>View Details</ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem onClick={(e) => handleStripeFund(e as unknown as React.MouseEvent)}>Fund via Stripe</ContextMenuItem>
        <ContextMenuItem onClick={() => window.location.href = `/wallets/fund?wallet=${wallet.wallet_id}`}>Fund via Other Provider</ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem onClick={onBridge}>Bridge to Another Chain</ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

function WalletDetailPanel({
  wallet,
  open,
  onOpenChange,
  onBridge,
}: {
  wallet: WalletItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onBridge: (wallet: WalletItem) => void
}) {
  const balance = parseFloat(wallet?.balance || '0')
  const spent = parseFloat(wallet?.spent_total || '0')
  const limitTotal = parseFloat(wallet?.limit_total || '0')
  const remaining = parseFloat(wallet?.remaining_limit || '0')
  const usagePercent = limitTotal > 0 ? Math.min((spent / limitTotal) * 100, 100) : 0
  const [fundingViaStripe, setFundingViaStripe] = useState(false)

  const handleStripeFund = useCallback(() => {
    if (!wallet) return
    const address = wallet.chain_address
    if (!address) {
      window.location.href = `/wallets/fund?wallet=${wallet.wallet_id}`
      return
    }
    const params = new URLSearchParams({
      destination_currency: 'usdc',
      destination_network: 'base',
      source_currency: 'usd',
      'wallet_addresses[ethereum]': address,
    })
    window.open(`https://crypto.link.com?${params.toString()}`, '_blank', 'noopener,noreferrer')
  }, [wallet])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Wallet Details</SheetTitle>
        </SheetHeader>

        {wallet && (
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

          {/* Fund & Bridge CTAs */}
          <div className="space-y-2">
            <button
              onClick={handleStripeFund}
              disabled={fundingViaStripe}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-sardis-500 text-white font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50"
            >
              {fundingViaStripe ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <CreditCard className="w-5 h-5" />
              )}
              Fund via Stripe
            </button>
            <button
              onClick={() => wallet && onBridge(wallet)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-blue-500/30 text-blue-400 font-medium rounded-lg hover:bg-blue-500/10 hover:text-blue-300 transition-colors"
            >
              <ArrowLeftRight className="w-4 h-4" />
              Bridge to Another Chain
            </button>
            <Link
              href={`/wallets/fund?wallet=${wallet.wallet_id}`}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-dark-100 text-gray-400 font-medium rounded-lg hover:bg-dark-200 hover:text-white transition-colors"
            >
              <DollarSign className="w-4 h-4" />
              More Funding Options
            </Link>
          </div>
        </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

// ── Bridge Modal ────────────────────────────────────────────────────

function ChainSelect({
  label,
  value,
  onChange,
  excludeChainId,
}: {
  label: string
  value: number
  onChange: (chainId: number) => void
  excludeChainId?: number
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs text-gray-500 uppercase tracking-wider">{label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full appearance-none bg-dark-200 border border-dark-100 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-sardis-500/50 pr-10"
        >
          {BRIDGE_CHAINS.filter((c) => c.chain_id !== excludeChainId).map((chain) => (
            <option key={chain.chain_id} value={chain.chain_id}>
              {chain.icon} {chain.name}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
      </div>
    </div>
  )
}

function BridgeModal({
  wallet,
  open,
  onClose,
}: {
  wallet: WalletItem | null
  open: boolean
  onClose: () => void
}) {
  const [sourceChain, setSourceChain] = useState(8453)
  const [destChain, setDestChain] = useState(4217)
  const [amount, setAmount] = useState('')
  const [bridgeStatus, setBridgeStatus] = useState<BridgeStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [quote, setQuote] = useState<{
    output_amount: string
    fee_usd: string
    estimated_time_seconds: number
  } | null>(null)
  const [result, setResult] = useState<{
    bridge_id: string
    status: string
    source_tx_hash: string | null
    destination_tx_hash: string | null
  } | null>(null)
  const quoteTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-fetch quote when params change
  useEffect(() => {
    if (!wallet || !amount || !open) {
      setQuote(null)
      return
    }
    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setQuote(null)
      return
    }
    if (sourceChain === destChain) {
      setQuote(null)
      return
    }

    if (quoteTimeout.current) clearTimeout(quoteTimeout.current)
    quoteTimeout.current = setTimeout(async () => {
      setBridgeStatus('quoting')
      setError(null)
      try {
        const q = await bridgeApi.getQuote({
          source_chain_id: sourceChain,
          dest_chain_id: destChain,
          token: 'USDC',
          amount,
          wallet_id: wallet.wallet_id,
        })
        setQuote({
          output_amount: q.output_amount,
          fee_usd: q.fee_usd,
          estimated_time_seconds: q.estimated_time_seconds,
        })
        setBridgeStatus('idle')
      } catch (err: any) {
        setError(err.message || 'Failed to fetch quote')
        setBridgeStatus('idle')
        setQuote(null)
      }
    }, 600)

    return () => {
      if (quoteTimeout.current) clearTimeout(quoteTimeout.current)
    }
  }, [wallet, amount, sourceChain, destChain, open])

  // Reset when modal closes
  useEffect(() => {
    if (!open) {
      setBridgeStatus('idle')
      setError(null)
      setQuote(null)
      setResult(null)
      setAmount('')
    }
  }, [open])

  const handleSwapChains = () => {
    setSourceChain(destChain)
    setDestChain(sourceChain)
  }

  const handleExecute = async () => {
    if (!wallet || !amount) return
    setBridgeStatus('executing')
    setError(null)
    setResult(null)

    try {
      const res = await bridgeApi.execute({
        source_chain_id: sourceChain,
        dest_chain_id: destChain,
        token: 'USDC',
        amount,
        wallet_id: wallet.wallet_id,
      })

      setResult(res)

      // If status is not final, start polling
      if (res.status !== 'success' && res.status !== 'failure') {
        setBridgeStatus('polling')
        let polls = 0
        const maxPolls = 40
        const interval = setInterval(async () => {
          polls++
          try {
            const statusRes = await bridgeApi.getStatus(res.bridge_id)
            if (statusRes.status === 'success' || statusRes.status === 'failure' || statusRes.status === 'refunded') {
              setResult((prev) => prev ? {
                ...prev,
                status: statusRes.status,
                source_tx_hash: statusRes.source_tx_hash || prev.source_tx_hash,
                destination_tx_hash: statusRes.destination_tx_hash || prev.destination_tx_hash,
              } : prev)
              setBridgeStatus(statusRes.status === 'success' ? 'success' : 'error')
              clearInterval(interval)
            }
          } catch {
            // Polling error — continue
          }
          if (polls >= maxPolls) {
            setBridgeStatus('success') // Optimistic — tx was broadcast
            clearInterval(interval)
          }
        }, 2000)
      } else {
        setBridgeStatus(res.status === 'success' ? 'success' : 'error')
      }
    } catch (err: any) {
      setError(err.message || 'Bridge execution failed')
      setBridgeStatus('error')
    }
  }

  if (!open) return null

  const sourceName = BRIDGE_CHAINS.find((c) => c.chain_id === sourceChain)?.name || 'Unknown'
  const destName = BRIDGE_CHAINS.find((c) => c.chain_id === destChain)?.name || 'Unknown'
  const isExecuting = bridgeStatus === 'executing' || bridgeStatus === 'polling'
  const canExecute = bridgeStatus === 'idle' && quote && amount && sourceChain !== destChain

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg mx-4 bg-dark-300 border border-dark-100 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <ArrowLeftRight className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Bridge USDC</h2>
              <p className="text-xs text-gray-500">
                {wallet?.wallet_id ? `Wallet: ${wallet.wallet_id.slice(0, 12)}...` : ''}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-5">
          {/* Chain selectors */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-end">
            <ChainSelect
              label="From"
              value={sourceChain}
              onChange={setSourceChain}
              excludeChainId={destChain}
            />
            <button
              onClick={handleSwapChains}
              className="mb-1 p-2 rounded-lg bg-dark-200 hover:bg-dark-100 text-gray-400 hover:text-white transition-colors"
              title="Swap chains"
            >
              <ArrowLeftRight className="w-4 h-4" />
            </button>
            <ChainSelect
              label="To"
              value={destChain}
              onChange={setDestChain}
              excludeChainId={sourceChain}
            />
          </div>

          {/* Amount */}
          <div className="space-y-1.5">
            <label className="text-xs text-gray-500 uppercase tracking-wider">Amount (USD)</label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="100.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={isExecuting}
                className="w-full pl-9 pr-16 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 disabled:opacity-50"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500 font-mono">USDC</span>
            </div>
          </div>

          {/* Quote preview */}
          {bridgeStatus === 'quoting' && (
            <div className="bg-dark-200 rounded-lg p-4 flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              <span className="text-sm text-gray-400">Fetching quote...</span>
            </div>
          )}

          {quote && bridgeStatus !== 'quoting' && (
            <div className="bg-dark-200 rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">You receive</span>
                <span className="text-sm text-white font-mono">{quote.output_amount} USDC</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Bridge fee</span>
                <span className="text-sm text-gray-400 font-mono">{quote.fee_usd}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Est. time</span>
                <span className="text-sm text-gray-400">~{quote.estimated_time_seconds}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Route</span>
                <span className="text-sm text-gray-400">{sourceName} &rarr; {destName} via Relay</span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div role="alert" aria-live="polite" className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Result */}
          {result && (
            <div className={clsx(
              'rounded-lg p-4 space-y-2',
              result.status === 'success' ? 'bg-sardis-500/10 border border-sardis-500/20' : 'bg-blue-500/10 border border-blue-500/20'
            )}>
              <div className="flex items-center gap-2">
                {bridgeStatus === 'polling' ? (
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                ) : result.status === 'success' ? (
                  <Check className="w-4 h-4 text-sardis-400" />
                ) : (
                  <Activity className="w-4 h-4 text-blue-400" />
                )}
                <span className={clsx(
                  'text-sm font-medium',
                  result.status === 'success' ? 'text-sardis-400' : 'text-blue-400'
                )}>
                  {bridgeStatus === 'polling' ? 'Bridging in progress...' : result.status === 'success' ? 'Bridge complete!' : `Status: ${result.status}`}
                </span>
              </div>
              {result.source_tx_hash && (
                <div className="flex justify-between">
                  <span className="text-xs text-gray-500">Source tx</span>
                  <span className="text-xs text-gray-400 font-mono truncate max-w-[200px]">{result.source_tx_hash}</span>
                </div>
              )}
              {result.destination_tx_hash && (
                <div className="flex justify-between">
                  <span className="text-xs text-gray-500">Destination tx</span>
                  <span className="text-xs text-gray-400 font-mono truncate max-w-[200px]">{result.destination_tx_hash}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-dark-100 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-dark-100 text-gray-400 font-medium rounded-lg hover:bg-dark-200 hover:text-white transition-colors"
          >
            {result?.status === 'success' ? 'Done' : 'Cancel'}
          </button>
          {!result?.status || result.status !== 'success' ? (
            <button
              onClick={handleExecute}
              disabled={!canExecute && !isExecuting}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {bridgeStatus === 'polling' ? 'Bridging...' : 'Signing...'}
                </>
              ) : (
                <>
                  <ArrowLeftRight className="w-4 h-4" />
                  Bridge
                </>
              )}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
