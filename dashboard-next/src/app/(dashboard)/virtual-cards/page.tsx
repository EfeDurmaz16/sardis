"use client";
import { useState } from 'react'
import { CreditCard, Plus, Eye, EyeOff, Copy, Check, Loader2, DollarSign, Send, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { virtualCardsApi } from '@/api/client'

type IssuedCard = {
  card_id: string
  card_number: string
  cvv: string
  expiry: string
  amount: string
  currency: string
  status: string
  card_type: string
  billing_address: Record<string, string>
  created_at: string
}

type BalanceInfo = {
  available: string
  pending: string
  currency: string
}

export default function VirtualCardsPage() {
  const queryClient = useQueryClient()
  const [showIssue, setShowIssue] = useState(false)
  const [issueAmount, setIssueAmount] = useState('25')
  const [cardType, setCardType] = useState<'single_use' | 'multi_use'>('single_use')
  const [revealedCards, setRevealedCards] = useState<Set<string>>(new Set())
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [issuedCards, setIssuedCards] = useState<IssuedCard[]>([])

  // Payment form state
  const [showPayment, setShowPayment] = useState<string | null>(null)
  const [paymentMerchant, setPaymentMerchant] = useState('')
  const [paymentAmount, setPaymentAmount] = useState('')

  // Balance
  const { data: balance, isLoading: balanceLoading } = useQuery({
    queryKey: ['virtual-cards-balance'],
    queryFn: virtualCardsApi.getBalance,
    retry: false,
  })

  // Issue card mutation
  const issueMutation = useMutation({
    mutationFn: (data: { amount: string; card_type: string }) =>
      virtualCardsApi.issue(data),
    onSuccess: (card) => {
      setIssuedCards((prev) => [card, ...prev])
      setShowIssue(false)
      setIssueAmount('25')
      queryClient.invalidateQueries({ queryKey: ['virtual-cards-balance'] })
    },
  })

  // Use card for payment mutation
  const paymentMutation = useMutation({
    mutationFn: (data: { cardId: string; merchant_name: string; amount: string }) =>
      virtualCardsApi.useForPayment(data.cardId, {
        merchant_name: data.merchant_name,
        amount: data.amount,
      }),
    onSuccess: () => {
      setShowPayment(null)
      setPaymentMerchant('')
      setPaymentAmount('')
    },
  })

  const toggleReveal = (cardId: string) => {
    setRevealedCards((prev) => {
      const next = new Set(prev)
      if (next.has(cardId)) {
        next.delete(cardId)
      } else {
        next.add(cardId)
      }
      return next
    })
  }

  const copyToClipboard = async (text: string, fieldKey: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedField(fieldKey)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const maskNumber = (num: string) => {
    if (num.length < 4) return num
    return '**** **** **** ' + num.slice(-4)
  }

  const statusColor = (s: string) => {
    switch (s) {
      case 'ready': case 'active': case 'funded': return 'text-green-400'
      case 'processing': return 'text-yellow-400'
      case 'used': case 'expired': return 'text-neutral-500'
      default: return 'text-neutral-400'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Virtual Cards</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Stablecoin-funded Visa prepaid cards via Laso Finance x402
          </p>
        </div>
        <button
          onClick={() => setShowIssue(true)}
          className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-neutral-200 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Issue Card
        </button>
      </div>

      {/* Balance Card */}
      <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
        <div className="flex items-center gap-3 mb-4">
          <DollarSign className="h-5 w-5 text-neutral-400" />
          <h2 className="text-lg font-medium text-white">Laso Account Balance</h2>
        </div>
        {balanceLoading ? (
          <div className="flex items-center gap-2 text-neutral-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading balance...
          </div>
        ) : balance ? (
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-neutral-500">Available</p>
              <p className="text-2xl font-semibold text-white">${balance.available}</p>
            </div>
            <div>
              <p className="text-sm text-neutral-500">Pending</p>
              <p className="text-2xl font-semibold text-neutral-400">${balance.pending}</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">
            Connect a Tempo wallet to view balance
          </p>
        )}
      </div>

      {/* Issue Card Dialog */}
      {showIssue && (
        <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Issue Virtual Card</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Amount (USD)</label>
              <input
                type="number"
                min="5"
                max="1000"
                step="1"
                value={issueAmount}
                onChange={(e) => setIssueAmount(e.target.value)}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-white text-sm focus:border-neutral-500 focus:outline-none"
                placeholder="$5 - $1,000"
              />
              <p className="mt-1 text-xs text-neutral-500">
                $5 minimum, $1,000 maximum. Card amount must match checkout total exactly.
              </p>
            </div>
            <div>
              <label className="block text-sm text-neutral-400 mb-1">Card Type</label>
              <div className="flex gap-3">
                <button
                  onClick={() => setCardType('single_use')}
                  className={clsx(
                    'rounded-lg border px-4 py-2 text-sm transition-colors',
                    cardType === 'single_use'
                      ? 'border-white bg-white text-black'
                      : 'border-neutral-700 bg-neutral-800 text-neutral-400 hover:border-neutral-600'
                  )}
                >
                  Single Use
                </button>
                <button
                  onClick={() => setCardType('multi_use')}
                  className={clsx(
                    'rounded-lg border px-4 py-2 text-sm transition-colors',
                    cardType === 'multi_use'
                      ? 'border-white bg-white text-black'
                      : 'border-neutral-700 bg-neutral-800 text-neutral-400 hover:border-neutral-600'
                  )}
                >
                  Multi Use
                </button>
              </div>
            </div>
            <div className="rounded-lg border border-neutral-700 bg-neutral-800/50 p-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-neutral-500 mt-0.5 shrink-0" />
                <div className="text-xs text-neutral-500">
                  <p>Authentication cost: $0.001 USDC (x402 micro-payment on Tempo).</p>
                  <p className="mt-1">Restrictions: US-only, non-reloadable, no 3D Secure.</p>
                  <p className="mt-1">Daily limits: 6 cards, $6,000 total.</p>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => issueMutation.mutate({ amount: issueAmount, card_type: cardType })}
                disabled={issueMutation.isPending || !issueAmount}
                className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black hover:bg-neutral-200 transition-colors disabled:opacity-50"
              >
                {issueMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CreditCard className="h-4 w-4" />
                )}
                Issue ${issueAmount} Card
              </button>
              <button
                onClick={() => setShowIssue(false)}
                className="rounded-lg border border-neutral-700 px-4 py-2 text-sm text-neutral-400 hover:border-neutral-600 transition-colors"
              >
                Cancel
              </button>
            </div>
            {issueMutation.isError && (
              <p className="text-sm text-red-400">
                {(issueMutation.error as Error)?.message || 'Card issuance failed'}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Issued Cards List */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-white">Issued Cards</h2>
        {issuedCards.length === 0 ? (
          <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-12 text-center">
            <CreditCard className="mx-auto h-12 w-12 text-neutral-700" />
            <p className="mt-4 text-sm text-neutral-500">
              No virtual cards issued yet. Click &quot;Issue Card&quot; to create one.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {issuedCards.map((card) => {
              const revealed = revealedCards.has(card.card_id)
              return (
                <div
                  key={card.card_id}
                  className="rounded-xl border border-neutral-800 bg-neutral-900 p-6"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <CreditCard className="h-5 w-5 text-neutral-400" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-white">
                            ${card.amount} {card.currency}
                          </span>
                          <span className={clsx('text-xs', statusColor(card.status))}>
                            {card.status}
                          </span>
                          <span className="text-xs text-neutral-600">
                            {card.card_type === 'single_use' ? 'Single use' : 'Multi use'}
                          </span>
                        </div>
                        <p className="text-xs text-neutral-500 mt-0.5">
                          {card.card_id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setShowPayment(showPayment === card.card_id ? null : card.card_id)}
                        className="flex items-center gap-1 rounded-lg border border-neutral-700 px-3 py-1.5 text-xs text-neutral-400 hover:border-neutral-600 transition-colors"
                      >
                        <Send className="h-3 w-3" />
                        Pay
                      </button>
                      <button
                        onClick={() => toggleReveal(card.card_id)}
                        className="flex items-center gap-1 rounded-lg border border-neutral-700 px-3 py-1.5 text-xs text-neutral-400 hover:border-neutral-600 transition-colors"
                      >
                        {revealed ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                        {revealed ? 'Hide' : 'Reveal'}
                      </button>
                    </div>
                  </div>

                  {/* Card Details */}
                  <div className="mt-4 grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-neutral-500">Card Number</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-sm font-mono text-white">
                          {revealed ? card.card_number : maskNumber(card.card_number)}
                        </span>
                        {revealed && (
                          <button
                            onClick={() => copyToClipboard(card.card_number, `num-${card.card_id}`)}
                            className="text-neutral-500 hover:text-neutral-300"
                          >
                            {copiedField === `num-${card.card_id}` ? (
                              <Check className="h-3 w-3" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-neutral-500">CVV</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-sm font-mono text-white">
                          {revealed ? card.cvv : '***'}
                        </span>
                        {revealed && (
                          <button
                            onClick={() => copyToClipboard(card.cvv, `cvv-${card.card_id}`)}
                            className="text-neutral-500 hover:text-neutral-300"
                          >
                            {copiedField === `cvv-${card.card_id}` ? (
                              <Check className="h-3 w-3" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-neutral-500">Expiry</p>
                      <span className="text-sm font-mono text-white mt-1 block">
                        {card.expiry || '--/--'}
                      </span>
                    </div>
                  </div>

                  {/* Payment form */}
                  {showPayment === card.card_id && (
                    <div className="mt-4 rounded-lg border border-neutral-700 bg-neutral-800/50 p-4">
                      <h4 className="text-sm font-medium text-white mb-3">Use Card for Payment</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs text-neutral-500 mb-1">Merchant</label>
                          <input
                            type="text"
                            value={paymentMerchant}
                            onChange={(e) => setPaymentMerchant(e.target.value)}
                            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-1.5 text-white text-sm focus:border-neutral-500 focus:outline-none"
                            placeholder="Merchant name"
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-neutral-500 mb-1">Amount</label>
                          <input
                            type="number"
                            value={paymentAmount}
                            onChange={(e) => setPaymentAmount(e.target.value)}
                            className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-1.5 text-white text-sm focus:border-neutral-500 focus:outline-none"
                            placeholder="0.00"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => paymentMutation.mutate({
                            cardId: card.card_id,
                            merchant_name: paymentMerchant,
                            amount: paymentAmount,
                          })}
                          disabled={paymentMutation.isPending || !paymentMerchant || !paymentAmount}
                          className="flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-black hover:bg-neutral-200 transition-colors disabled:opacity-50"
                        >
                          {paymentMutation.isPending ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Send className="h-3 w-3" />
                          )}
                          Authorize
                        </button>
                        <button
                          onClick={() => setShowPayment(null)}
                          className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm text-neutral-400 hover:border-neutral-600 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                      {paymentMutation.isError && (
                        <p className="mt-2 text-xs text-red-400">
                          {(paymentMutation.error as Error)?.message || 'Payment failed'}
                        </p>
                      )}
                      {paymentMutation.isSuccess && (
                        <p className="mt-2 text-xs text-green-400">
                          Payment authorized successfully
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
