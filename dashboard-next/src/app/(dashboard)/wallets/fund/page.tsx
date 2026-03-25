"use client";

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  ArrowLeft,
  Wallet,
  CreditCard,
  Building2,
  Smartphone,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
  ChevronRight,
  Shield,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import clsx from 'clsx'
import { useFundWallet } from '@/hooks/useOnramp'
import { useWallets, useWallet } from '@/hooks/useApi'
import type { OnrampProvider, PaymentMethod } from '@/hooks/useOnramp'

const PROVIDERS: {
  id: OnrampProvider
  name: string
  description: string
  recommended?: boolean
  fees: string
}[] = [
  {
    id: 'coinbase',
    name: 'Coinbase Onramp',
    description: 'Instant funding via Coinbase. No fees for USDC.',
    recommended: true,
    fees: 'Free',
  },
  {
    id: 'moonpay',
    name: 'MoonPay',
    description: 'Global coverage with card and bank transfers.',
    fees: '1-4.5%',
  },
]

const PAYMENT_METHODS: {
  id: PaymentMethod
  name: string
  icon: typeof CreditCard
  available: boolean
}[] = [
  { id: 'card', name: 'Debit / Credit Card', icon: CreditCard, available: true },
  { id: 'bank', name: 'Bank Transfer (ACH)', icon: Building2, available: true },
  { id: 'apple_pay', name: 'Apple Pay', icon: Smartphone, available: true },
  { id: 'google_pay', name: 'Google Pay', icon: Smartphone, available: true },
]

const PRESET_AMOUNTS = ['25', '50', '100', '250', '500', '1000']

type FundStep = 'configure' | 'processing' | 'success' | 'error'

export default function FundWalletPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const walletIdParam = searchParams.get('wallet')

  const { data: wallets = [] } = useWallets()
  const { data: selectedWalletData } = useWallet(walletIdParam || '')
  const fundWallet = useFundWallet()

  const [step, setStep] = useState<FundStep>('configure')
  const [amount, setAmount] = useState('')
  const [provider, setProvider] = useState<OnrampProvider>('coinbase')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('card')
  const [selectedWalletId, setSelectedWalletId] = useState(walletIdParam || '')
  const [resultData, setResultData] = useState<Record<string, unknown> | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  // Set wallet from query param
  useEffect(() => {
    if (walletIdParam) {
      setSelectedWalletId(walletIdParam)
    }
  }, [walletIdParam])

  // Auto-select first wallet if none specified
  useEffect(() => {
    if (!selectedWalletId && (wallets as any[]).length > 0) {
      setSelectedWalletId((wallets as any[])[0].wallet_id)
    }
  }, [wallets, selectedWalletId])

  const parsedAmount = parseFloat(amount)
  const isValidAmount = !isNaN(parsedAmount) && parsedAmount >= 1 && parsedAmount <= 10000

  const handleFund = async () => {
    if (!isValidAmount || !selectedWalletId) return

    setStep('processing')
    setErrorMessage('')

    try {
      const result = await fundWallet.mutateAsync({
        walletId: selectedWalletId,
        amount: parsedAmount.toFixed(2),
        provider,
        payment_method: paymentMethod,
      })

      setResultData(result)

      // If the provider returns an onramp URL, open it
      if ((result as any)?.onramp_url) {
        window.open((result as any).onramp_url, '_blank', 'noopener,noreferrer')
      }

      setStep('success')
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to initiate funding. Please try again.')
      setStep('error')
    }
  }

  const handleRetry = () => {
    setStep('configure')
    setErrorMessage('')
    setResultData(null)
  }

  const walletDisplayName = selectedWalletData
    ? `${(selectedWalletData as any).wallet_id?.slice(0, 8)}...${(selectedWalletData as any).wallet_id?.slice(-6)}`
    : selectedWalletId
      ? `${selectedWalletId.slice(0, 8)}...${selectedWalletId.slice(-6)}`
      : 'Select a wallet'

  const currentBalance = selectedWalletData
    ? `$${parseFloat((selectedWalletData as any).balance || '0').toFixed(2)}`
    : '--'

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/wallets"
          className="p-2 text-gray-400 hover:text-white hover:bg-dark-200 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white font-display">Fund Wallet</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Add USDC to your wallet via fiat onramp
          </p>
        </div>
      </div>

      {/* Configure step */}
      {step === 'configure' && (
        <div className="space-y-6">
          {/* Wallet selector */}
          <div className="card p-5 space-y-3">
            <label className="text-sm font-medium text-gray-400">Destination Wallet</label>
            <div className="flex items-center gap-3 p-3 bg-dark-200 rounded-lg border border-dark-100">
              <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                <Wallet className="w-5 h-5 text-sardis-400" />
              </div>
              <div className="flex-1 min-w-0">
                {(wallets as any[]).length > 1 ? (
                  <select
                    value={selectedWalletId}
                    onChange={(e) => setSelectedWalletId(e.target.value)}
                    className="w-full bg-transparent text-white text-sm font-mono focus:outline-none cursor-pointer"
                  >
                    {(wallets as any[]).map((w: any) => (
                      <option key={w.wallet_id} value={w.wallet_id} className="bg-dark-300">
                        {w.wallet_id}
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-sm text-white font-mono truncate">{walletDisplayName}</p>
                )}
                <p className="text-xs text-gray-500">
                  Balance: <span className="text-gray-300 mono-numbers">{currentBalance}</span> USDC
                </p>
              </div>
            </div>
          </div>

          {/* Amount input */}
          <div className="card p-5 space-y-4">
            <label className="text-sm font-medium text-gray-400">Amount (USD)</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-2xl text-gray-500 font-medium">
                $
              </span>
              <input
                type="text"
                inputMode="decimal"
                value={amount}
                onChange={(e) => {
                  const val = e.target.value.replace(/[^0-9.]/g, '')
                  // Allow only one decimal point
                  const parts = val.split('.')
                  if (parts.length > 2) return
                  if (parts[1] && parts[1].length > 2) return
                  setAmount(val)
                }}
                placeholder="0.00"
                className="w-full pl-10 pr-4 py-4 bg-dark-300 border border-dark-100 rounded-lg text-white text-2xl font-mono focus:outline-none focus:border-sardis-500/50 placeholder-gray-600"
              />
            </div>

            {/* Preset amounts */}
            <div className="flex flex-wrap gap-2">
              {PRESET_AMOUNTS.map((preset) => (
                <button
                  key={preset}
                  onClick={() => setAmount(preset)}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    amount === preset
                      ? 'bg-sardis-500/20 text-sardis-400 border border-sardis-500/40'
                      : 'bg-dark-200 text-gray-400 border border-dark-100 hover:border-gray-600 hover:text-white'
                  )}
                >
                  ${preset}
                </button>
              ))}
            </div>

            {amount && !isValidAmount && (
              <p className="text-xs text-red-400">
                {parsedAmount < 1
                  ? 'Minimum amount is $1.00'
                  : parsedAmount > 10000
                    ? 'Maximum amount is $10,000.00'
                    : 'Please enter a valid amount'}
              </p>
            )}
          </div>

          {/* Provider selection */}
          <div className="card p-5 space-y-4">
            <label className="text-sm font-medium text-gray-400">Provider</label>
            <div className="space-y-2">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  className={clsx(
                    'w-full flex items-center gap-4 p-4 rounded-lg border transition-all text-left',
                    provider === p.id
                      ? 'bg-sardis-500/10 border-sardis-500/40'
                      : 'bg-dark-200 border-dark-100 hover:border-gray-600'
                  )}
                >
                  <div
                    className={clsx(
                      'w-10 h-10 rounded-lg flex items-center justify-center',
                      provider === p.id ? 'bg-sardis-500/20' : 'bg-dark-300'
                    )}
                  >
                    <Zap
                      className={clsx(
                        'w-5 h-5',
                        provider === p.id ? 'text-sardis-400' : 'text-gray-500'
                      )}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white">{p.name}</span>
                      {p.recommended && (
                        <span className="text-[10px] px-1.5 py-0.5 bg-sardis-500/20 text-sardis-400 rounded font-medium uppercase tracking-wider">
                          Recommended
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-gray-400">Fees: {p.fees}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Payment method */}
          <div className="card p-5 space-y-4">
            <label className="text-sm font-medium text-gray-400">Payment Method</label>
            <div className="grid grid-cols-2 gap-2">
              {PAYMENT_METHODS.map((method) => (
                <button
                  key={method.id}
                  onClick={() => method.available && setPaymentMethod(method.id)}
                  disabled={!method.available}
                  className={clsx(
                    'flex items-center gap-3 p-3 rounded-lg border transition-all',
                    !method.available && 'opacity-40 cursor-not-allowed',
                    paymentMethod === method.id
                      ? 'bg-sardis-500/10 border-sardis-500/40'
                      : 'bg-dark-200 border-dark-100 hover:border-gray-600'
                  )}
                >
                  <method.icon
                    className={clsx(
                      'w-4 h-4',
                      paymentMethod === method.id ? 'text-sardis-400' : 'text-gray-500'
                    )}
                  />
                  <span
                    className={clsx(
                      'text-sm',
                      paymentMethod === method.id ? 'text-white' : 'text-gray-400'
                    )}
                  >
                    {method.name}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Summary + submit */}
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Shield className="w-4 h-4" />
              <span>Funds are converted to USDC and deposited on Base</span>
            </div>

            {isValidAmount && (
              <div className="bg-dark-200 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">You pay</span>
                  <span className="text-white font-mono">
                    ${parsedAmount.toFixed(2)} USD
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">You receive</span>
                  <span className="text-sardis-400 font-mono">
                    ~{parsedAmount.toFixed(2)} USDC
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Provider fees</span>
                  <span className="text-gray-300">
                    {provider === 'coinbase' ? 'Free' : '~' + (parsedAmount * 0.03).toFixed(2) + ' USD'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Network</span>
                  <span className="text-gray-300">Base (L2)</span>
                </div>
              </div>
            )}

            <button
              onClick={handleFund}
              disabled={!isValidAmount || !selectedWalletId || fundWallet.isPending}
              className={clsx(
                'w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-all text-base',
                isValidAmount && selectedWalletId
                  ? 'bg-sardis-500 text-dark-400 hover:bg-sardis-400 glow-green-hover'
                  : 'bg-dark-200 text-gray-600 cursor-not-allowed'
              )}
            >
              {fundWallet.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  Fund ${isValidAmount ? parsedAmount.toFixed(2) : '0.00'}
                  <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Processing step */}
      {step === 'processing' && (
        <div className="card p-12 text-center space-y-4">
          <Loader2 className="w-12 h-12 text-sardis-400 animate-spin mx-auto" />
          <h2 className="text-xl font-semibold text-white">Processing...</h2>
          <p className="text-gray-400 text-sm">
            Setting up your {provider === 'coinbase' ? 'Coinbase' : 'MoonPay'} onramp session.
            <br />
            You may be redirected to complete payment.
          </p>
        </div>
      )}

      {/* Success step */}
      {step === 'success' && (
        <div className="card p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-sardis-500/10 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Funding Initiated</h2>
            <p className="text-gray-400 text-sm mt-2">
              Your ${parsedAmount.toFixed(2)} funding request has been submitted.
              {(resultData as any)?.onramp_url
                ? ' Complete the payment in the provider window.'
                : ' Funds will arrive in your wallet shortly.'}
            </p>
          </div>

          {(resultData as any)?.new_balance && (
            <div className="bg-dark-200 rounded-lg p-4 inline-block mx-auto">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">New Balance</p>
              <p className="text-2xl font-bold text-sardis-400 mono-numbers">
                ${parseFloat((resultData as any).new_balance).toFixed(2)} USDC
              </p>
            </div>
          )}

          {(resultData as any)?.onramp_url && (
            <a
              href={(resultData as any).onramp_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-sardis-400 hover:text-sardis-300 transition-colors"
            >
              Open payment window
              <ExternalLink className="w-4 h-4" />
            </a>
          )}

          <div className="flex gap-3 justify-center pt-2">
            <button
              onClick={() => {
                setStep('configure')
                setAmount('')
                setResultData(null)
              }}
              className="px-4 py-2 text-sm border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
            >
              Fund Again
            </button>
            <Link
              href="/wallets"
              className="px-4 py-2 text-sm bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors"
            >
              View Wallets
            </Link>
          </div>
        </div>
      )}

      {/* Error step */}
      {step === 'error' && (
        <div className="card p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-8 h-8 text-red-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">Funding Failed</h2>
            <p className="text-gray-400 text-sm mt-2">{errorMessage}</p>
          </div>
          <div className="flex gap-3 justify-center">
            <button
              onClick={handleRetry}
              className="px-4 py-2 text-sm bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors"
            >
              Try Again
            </button>
            <Link
              href="/wallets"
              className="px-4 py-2 text-sm border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
            >
              Back to Wallets
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
