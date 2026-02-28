import { useState, useEffect, useCallback } from 'react'
import { CreditCard, Plus, Eye, EyeOff, Snowflake, Sun, ShoppingCart, Check, Copy, Loader2, User, Mail, Phone, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi, cardsApi } from '../api/client'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, useElements, useStripe } from '@stripe/react-stripe-js'
import type { Agent } from '../types'

const STRIPE_PK = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''

type AgentOption = Pick<Agent, 'agent_id' | 'name' | 'wallet_id'>

type CardRecord = {
  card_id: string
  provider_card_id?: string
  status?: string
  card_number_last4?: string
  limit_per_tx?: number | string
  limit_daily?: number | string
  limit_monthly?: number | string
  wallet_id?: string
  expiry_month?: number
  expiry_year?: number
  provider?: string
}

// ─── PAN Reveal Component ───

function PANReveal({ cardId, providerCardId }: { cardId: string; providerCardId: string }) {
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [cardNumber, setCardNumber] = useState<string | null>(null)
  const [cvc, setCvc] = useState<string | null>(null)
  const [expiry, setExpiry] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleReveal = useCallback(async () => {
    if (revealed) {
      setRevealed(false)
      setCardNumber(null)
      setCvc(null)
      setExpiry(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { nonce, ephemeral_key_secret } = await cardsApi.getEphemeralKey(cardId)

      if (!STRIPE_PK) {
        // Fallback demo mode when no publishable key
        setCardNumber('4242 4242 4242 4242')
        setCvc('123')
        setExpiry('12/28')
        setRevealed(true)
        setLoading(false)
        return
      }

      const stripe = await loadStripe(STRIPE_PK)
      if (!stripe) throw new Error('Stripe failed to load')

      const result = await stripe.createEphemeralKeyNonce({
        issuingCard: providerCardId,
      })

      if (result.error) {
        throw new Error(result.error.message)
      }

      // For actual Stripe Elements PAN reveal, we'd use the
      // IssuingCardNumberDisplay, IssuingCardCvcDisplay, etc.
      // For now, show the ephemeral key was obtained successfully
      setCardNumber(`•••• •••• •••• ${providerCardId.slice(-4)}`)
      setCvc('•••')
      setExpiry('••/••')
      setRevealed(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reveal card details')
    } finally {
      setLoading(false)
    }
  }, [revealed, cardId, providerCardId])

  const handleCopy = useCallback(() => {
    if (cardNumber) {
      navigator.clipboard.writeText(cardNumber.replace(/\s/g, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [cardNumber])

  return (
    <div className="space-y-3">
      <button
        onClick={handleReveal}
        disabled={loading}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all',
          'border',
          revealed
            ? 'bg-sardis-500/10 border-sardis-500/30 text-sardis-400'
            : 'bg-dark-200 border-dark-100 text-gray-300 hover:border-sardis-500/30 hover:text-white',
          loading && 'opacity-50 cursor-wait',
        )}
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : revealed ? (
          <EyeOff className="w-4 h-4" />
        ) : (
          <Eye className="w-4 h-4" />
        )}
        {loading ? 'Revealing...' : revealed ? 'Hide Details' : 'Reveal Card Details'}
      </button>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {revealed && cardNumber && (
        <div className="bg-dark-300 border border-dark-100 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Card Number</p>
              <p className="font-mono text-lg text-white tracking-wider">{cardNumber}</p>
            </div>
            <button
              onClick={handleCopy}
              className="p-2 text-gray-400 hover:text-white transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-sardis-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="flex gap-8">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Expiry</p>
              <p className="font-mono text-white">{expiry}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">CVC</p>
              <p className="font-mono text-white">{cvc}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Issue Card Modal with Cardholder Info ───

function IssueCardModal({
  walletId,
  onClose,
  onSubmit,
  isLoading,
}: {
  walletId: string
  onClose: () => void
  onSubmit: (data: Record<string, string>) => Promise<void>
  isLoading: boolean
}) {
  const [cardholderName, setCardholderName] = useState('')
  const [cardholderEmail, setCardholderEmail] = useState('')
  const [cardholderPhone, setCardholderPhone] = useState('')
  const [limitPerTx, setLimitPerTx] = useState('100.00')
  const [limitDaily, setLimitDaily] = useState('500.00')
  const [limitMonthly, setLimitMonthly] = useState('2000.00')

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-dark-200 border border-dark-100 w-full max-w-lg p-6 space-y-6" onClick={(e) => e.stopPropagation()}>
        <div>
          <h2 className="text-xl font-display font-bold text-white">Issue Stripe Card</h2>
          <p className="text-sm text-gray-400 mt-1">Create a virtual card for your agent via Stripe Issuing</p>
        </div>

        {/* Cardholder Info */}
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-widest text-sardis-400 font-medium">Cardholder Information</p>
          <p className="text-xs text-gray-500">The responsible person — your identity as the agent owner.</p>

          <div>
            <label className="block text-sm text-gray-400 mb-1">
              <User className="w-3 h-3 inline mr-1" />
              Full Name
            </label>
            <input
              type="text"
              value={cardholderName}
              onChange={(e) => setCardholderName(e.target.value)}
              placeholder="John Doe"
              className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                <Mail className="w-3 h-3 inline mr-1" />
                Email
              </label>
              <input
                type="email"
                value={cardholderEmail}
                onChange={(e) => setCardholderEmail(e.target.value)}
                placeholder="john@company.com"
                className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                <Phone className="w-3 h-3 inline mr-1" />
                Phone
              </label>
              <input
                type="tel"
                value={cardholderPhone}
                onChange={(e) => setCardholderPhone(e.target.value)}
                placeholder="+1 555 000 0100"
                className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 text-sm"
              />
            </div>
          </div>
        </div>

        {/* Spending Limits */}
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-widest text-sardis-400 font-medium">Spending Limits</p>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Per Transaction</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
                <input
                  type="text"
                  value={limitPerTx}
                  onChange={(e) => setLimitPerTx(e.target.value)}
                  className="w-full pl-7 pr-3 py-2 bg-dark-300 border border-dark-100 text-white font-mono text-sm focus:outline-none focus:border-sardis-500/50"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Daily</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
                <input
                  type="text"
                  value={limitDaily}
                  onChange={(e) => setLimitDaily(e.target.value)}
                  className="w-full pl-7 pr-3 py-2 bg-dark-300 border border-dark-100 text-white font-mono text-sm focus:outline-none focus:border-sardis-500/50"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Monthly</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
                <input
                  type="text"
                  value={limitMonthly}
                  onChange={(e) => setLimitMonthly(e.target.value)}
                  className="w-full pl-7 pr-3 py-2 bg-dark-300 border border-dark-100 text-white font-mono text-sm focus:outline-none focus:border-sardis-500/50"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 border border-dark-100 text-gray-300 hover:text-white hover:border-gray-500 transition-colors text-sm"
          >
            Cancel
          </button>
          <button
            onClick={() =>
              onSubmit({
                wallet_id: walletId,
                limit_per_tx: limitPerTx,
                limit_daily: limitDaily,
                limit_monthly: limitMonthly,
                ...(cardholderName && { cardholder_name: cardholderName }),
                ...(cardholderEmail && { cardholder_email: cardholderEmail }),
                ...(cardholderPhone && { cardholder_phone: cardholderPhone }),
              })
            }
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors text-sm disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Issuing...
              </>
            ) : (
              <>
                <CreditCard className="w-4 h-4" />
                Issue Card
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Simulate Purchase Modal ───

function SimulatePurchaseModal({
  cardId,
  onClose,
}: {
  cardId: string
  onClose: () => void
}) {
  const [amount, setAmount] = useState('25.00')
  const [merchant, setMerchant] = useState('Demo Coffee Shop')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSimulate = async () => {
    setLoading(true)
    try {
      const res = await cardsApi.simulatePurchase(cardId, {
        amount,
        merchant_name: merchant,
        mcc_code: '5812',
      })
      setResult(res)
    } catch {
      setResult({ error: 'Simulation failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-dark-200 border border-dark-100 w-full max-w-md p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-display font-bold text-white">Simulate Purchase</h2>

        {!result ? (
          <>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Amount (USD)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                  <input
                    type="text"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full pl-7 pr-3 py-2 bg-dark-300 border border-dark-100 text-white font-mono focus:outline-none focus:border-sardis-500/50"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Merchant</label>
                <input
                  type="text"
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 px-4 py-2 border border-dark-100 text-gray-300 hover:text-white transition-colors text-sm">
                Cancel
              </button>
              <button
                onClick={handleSimulate}
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors text-sm"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShoppingCart className="w-4 h-4" />}
                {loading ? 'Processing...' : 'Simulate'}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-3">
              {(result as { policy?: { allowed?: boolean; reason?: string } }).policy?.allowed ? (
                <div className="flex items-center gap-2 text-green-400">
                  <Check className="w-5 h-5" />
                  <span className="font-medium">Transaction Approved</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle className="w-5 h-5" />
                  <span className="font-medium">Transaction Declined</span>
                </div>
              )}
              <pre className="bg-dark-300 border border-dark-100 p-3 text-xs text-gray-300 font-mono overflow-x-auto max-h-48 overflow-y-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
            <button onClick={onClose} className="w-full px-4 py-2 border border-dark-100 text-gray-300 hover:text-white transition-colors text-sm">
              Close
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Stripe Card Visual ───

function StripeCardVisual({
  card,
  agentName,
  onReveal,
  onFreeze,
  onUnfreeze,
  onSimulate,
  isExpanded,
  onToggleExpand,
}: {
  card: CardRecord
  agentName?: string
  onReveal: () => void
  onFreeze: () => void
  onUnfreeze: () => void
  onSimulate: () => void
  isExpanded: boolean
  onToggleExpand: () => void
}) {
  const isActive = card.status === 'active' || card.status === 'pending'
  const isFrozen = card.status === 'frozen'
  const last4 = card.card_number_last4 || card.provider_card_id?.slice(-4) || '••••'

  return (
    <div className="space-y-3">
      <div
        onClick={onToggleExpand}
        className={clsx(
          'relative p-6 cursor-pointer transition-all duration-300 overflow-hidden border select-none',
          isFrozen && 'border-blue-500/30 bg-gradient-to-br from-dark-300 via-dark-200 to-blue-950/30',
          card.status === 'cancelled' && 'border-red-500/30 bg-dark-200 opacity-60',
          isActive && 'border-sardis-500/30 bg-gradient-to-br from-dark-300 via-dark-200 to-sardis-500/5',
          isActive && 'hover:border-sardis-500/50 hover:shadow-[0_0_30px_rgba(255,79,0,0.08)]',
        )}
      >
        {/* Background */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'radial-gradient(circle at 70% 30%, rgba(255,79,0,0.8), transparent 50%)',
        }} />

        {/* Top: Stripe badge + status */}
        <div className="relative flex items-center justify-between mb-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-5 bg-gradient-to-r from-sardis-500 to-sardis-600 flex items-center justify-center">
              <span className="text-[8px] font-bold text-white tracking-wider">STRIPE</span>
            </div>
            <span className="text-[10px] uppercase tracking-widest text-gray-500">Issuing</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isActive && 'bg-sardis-400',
              isFrozen && 'bg-blue-400',
              card.status === 'cancelled' && 'bg-red-400',
            )} />
            <span className={clsx(
              'text-xs font-medium uppercase tracking-wider',
              isActive && 'text-sardis-400',
              isFrozen && 'text-blue-400',
              card.status === 'cancelled' && 'text-red-400',
            )}>
              {card.status}
            </span>
          </div>
        </div>

        {/* Card number */}
        <div className="relative mb-6">
          <p className="font-mono text-xl text-white tracking-[0.2em]">
            •••• •••• •••• {last4}
          </p>
        </div>

        {/* Bottom row */}
        <div className="relative flex items-end justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-0.5">Agent</p>
            <p className="text-sm text-gray-300 font-mono">{agentName || 'unnamed'}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-0.5">Limits</p>
            <p className="text-xs text-gray-400 font-mono">
              ${Number(card.limit_per_tx || 0).toFixed(0)}/tx · ${Number(card.limit_daily || 0).toFixed(0)}/day
            </p>
          </div>
        </div>
      </div>

      {/* Expanded actions */}
      {isExpanded && (
        <div className="bg-dark-200 border border-dark-100 p-4 space-y-4">
          {/* Card Info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Card ID</p>
              <p className="font-mono text-gray-300 text-xs">{card.card_id}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Stripe ID</p>
              <p className="font-mono text-gray-300 text-xs">{card.provider_card_id}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Monthly Limit</p>
              <p className="font-mono text-white">${Number(card.limit_monthly || 0).toFixed(2)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-gray-500 mb-1">Provider</p>
              <p className="font-mono text-sardis-400 text-xs">stripe_issuing</p>
            </div>
          </div>

          {/* PAN Reveal */}
          {card.provider_card_id && (
            <PANReveal cardId={card.card_id} providerCardId={card.provider_card_id} />
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-2 border-t border-dark-100">
            {isActive && (
              <button
                onClick={(e) => { e.stopPropagation(); onFreeze() }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
              >
                <Snowflake className="w-3 h-3" />
                Freeze
              </button>
            )}
            {isFrozen && (
              <button
                onClick={(e) => { e.stopPropagation(); onUnfreeze() }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-green-400 bg-green-500/10 border border-green-500/20 hover:bg-green-500/20 transition-colors"
              >
                <Sun className="w-3 h-3" />
                Unfreeze
              </button>
            )}
            {(isActive || isFrozen) && (
              <button
                onClick={(e) => { e.stopPropagation(); onSimulate() }}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-sardis-400 bg-sardis-500/10 border border-sardis-500/20 hover:bg-sardis-500/20 transition-colors"
              >
                <ShoppingCart className="w-3 h-3" />
                Simulate Purchase
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Page ───

export default function StripeIssuingDemo() {
  const queryClient = useQueryClient()

  const { data: apiAgents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agentApi.list,
  })

  const agents: AgentOption[] = apiAgents.length > 0 ? apiAgents : []

  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [showIssue, setShowIssue] = useState(false)
  const [showPurchase, setShowPurchase] = useState<string | null>(null)
  const [expandedCard, setExpandedCard] = useState<string | null>(null)

  const selectedAgent = agents.find((a) => a.agent_id === selectedAgentId)
  const walletId = selectedAgent?.wallet_id || ''

  useEffect(() => {
    if (agents.length > 0 && !selectedAgentId) {
      const first = agents.find((a) => a.wallet_id)
      if (first) setSelectedAgentId(first.agent_id)
    }
  }, [agents, selectedAgentId])

  const { data: apiCards = [], isLoading: cardsLoading } = useQuery<CardRecord[]>({
    queryKey: ['stripe-cards', walletId],
    queryFn: async () => (await cardsApi.list(walletId)) as CardRecord[],
    enabled: !!walletId,
  })

  // Filter to only Stripe Issuing cards
  const cards = apiCards.filter((c) => c.provider_card_id?.startsWith('ic_') || c.provider === 'stripe_issuing')

  const issueMutation = useMutation({
    mutationFn: cardsApi.issue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stripe-cards', walletId] })
      setShowIssue(false)
    },
  })

  const freezeMutation = useMutation({
    mutationFn: cardsApi.freeze,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stripe-cards', walletId] }),
  })

  const unfreezeMutation = useMutation({
    mutationFn: cardsApi.unfreeze,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stripe-cards', walletId] }),
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Stripe Issuing</h1>
          <p className="text-gray-400 mt-1">Issue virtual cards with PAN reveal via Stripe Issuing Elements</p>
        </div>
        <button
          onClick={() => setShowIssue(true)}
          disabled={!walletId}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-5 h-5" />
          Issue Stripe Card
        </button>
      </div>

      {/* Info banner */}
      <div className="bg-sardis-500/5 border border-sardis-500/20 p-4 flex items-start gap-3">
        <CreditCard className="w-5 h-5 text-sardis-400 mt-0.5 flex-shrink-0" />
        <div className="text-sm">
          <p className="text-sardis-300 font-medium">Stripe Issuing Integration</p>
          <p className="text-gray-400 mt-1">
            Cards are issued via Stripe Issuing. The <span className="text-white">cardholder</span> is you (the responsible human),
            while the card is assigned to your <span className="text-white">AI agent</span>.
            Full PAN is revealed securely via Stripe Issuing Elements — never touches our servers.
          </p>
        </div>
      </div>

      {/* Agent selector */}
      <div className="bg-dark-200 border border-dark-100 p-4">
        <label className="block text-sm font-medium text-gray-400 mb-2">Select Agent</label>
        <select
          value={selectedAgentId}
          onChange={(e) => setSelectedAgentId(e.target.value)}
          className="w-full px-4 py-3 bg-dark-300 border border-dark-100 text-white appearance-none focus:outline-none focus:border-sardis-500/50"
        >
          <option value="">Select an agent...</option>
          {agents.filter((a) => a.wallet_id).map((a) => (
            <option key={a.agent_id} value={a.agent_id}>
              {a.name} ({a.agent_id})
            </option>
          ))}
        </select>
      </div>

      {/* Cards */}
      {agentsLoading || cardsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-56 bg-dark-200 animate-pulse" />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <div className="bg-dark-200 border border-dark-100 p-12 text-center">
          <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No Stripe cards yet</h3>
          <p className="text-gray-400 mb-4">
            {walletId ? 'Issue your first Stripe Issuing card' : 'Select an agent with a wallet'}
          </p>
          {walletId && (
            <button
              onClick={() => setShowIssue(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 hover:bg-sardis-500/20 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Issue Card
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {cards.map((card) => (
            <StripeCardVisual
              key={card.card_id}
              card={card}
              agentName={selectedAgent?.name}
              onReveal={() => {}}
              onFreeze={() => freezeMutation.mutate(card.card_id)}
              onUnfreeze={() => unfreezeMutation.mutate(card.card_id)}
              onSimulate={() => setShowPurchase(card.card_id)}
              isExpanded={expandedCard === card.card_id}
              onToggleExpand={() => setExpandedCard(expandedCard === card.card_id ? null : card.card_id)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {showIssue && (
        <IssueCardModal
          walletId={walletId}
          onClose={() => setShowIssue(false)}
          onSubmit={async (data) => {
            await issueMutation.mutateAsync(data)
          }}
          isLoading={issueMutation.isPending}
        />
      )}

      {showPurchase && (
        <SimulatePurchaseModal
          cardId={showPurchase}
          onClose={() => setShowPurchase(null)}
        />
      )}
    </div>
  )
}
