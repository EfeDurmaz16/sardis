"use client";

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Building2,
  Wallet,
  Webhook,
  Code,
  CreditCard,
  ChevronRight,
  ChevronLeft,
  Check,
  Copy,
  ExternalLink,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import clsx from 'clsx'
import { useRegisterMerchant } from '@/hooks/useApi'
import { merchantApi } from '@/api/client'

const STEPS = [
  { title: 'Business Details', icon: Building2 },
  { title: 'Settlement Wallet', icon: Wallet },
  { title: 'Webhook URL', icon: Webhook },
  { title: 'Get Embed Code', icon: Code },
  { title: 'Test Payment', icon: CreditCard },
]

interface FormState {
  business_name: string
  website: string
  logo_url: string
  settlement_address: string
  use_sardis_wallet: boolean
  webhook_url: string
  category: string
}

interface RegistrationResult {
  merchant_id: string
  business_name: string
  settlement_wallet_id: string | null
  settlement_address: string | null
  webhook_url: string | null
  credentials: { client_id: string; client_secret: string }
  embed_snippet: string
  created_at: string
}

export default function MerchantSetupPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState<FormState>({
    business_name: '',
    website: '',
    logo_url: '',
    settlement_address: '',
    use_sardis_wallet: true,
    webhook_url: '',
    category: '',
  })
  const [result, setResult] = useState<RegistrationResult | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [testStatus, setTestStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')

  const registerMutation = useRegisterMerchant()

  const updateField = (field: keyof FormState, value: string | boolean) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleRegister = async () => {
    try {
      const payload: Parameters<typeof registerMutation.mutateAsync>[0] = {
        business_name: form.business_name,
      }
      if (form.website) payload.website = form.website
      if (form.logo_url) payload.logo_url = form.logo_url
      if (!form.use_sardis_wallet && form.settlement_address) {
        payload.settlement_address = form.settlement_address
      }
      if (form.webhook_url) payload.webhook_url = form.webhook_url
      if (form.category) payload.category = form.category

      const res = await registerMutation.mutateAsync(payload)
      setResult(res)
      setStep(3) // Jump to embed code step
    } catch (err) {
      // Error handled by mutation state
    }
  }

  const [testCheckoutUrl, setTestCheckoutUrl] = useState<string | null>(null)

  const handleTestPayment = async () => {
    setTestStatus('sending')
    try {
      const res = await merchantApi.createTestSession()
      setTestCheckoutUrl(res.checkout_url)
      setTestStatus('success')
    } catch {
      setTestStatus('error')
    }
  }

  const canProceed = () => {
    switch (step) {
      case 0:
        return form.business_name.trim().length > 0
      case 1:
        return form.use_sardis_wallet || form.settlement_address.trim().length > 0
      case 2:
        return true // webhook is optional
      case 3:
        return result !== null
      case 4:
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    if (step === 2 && !result) {
      // At the end of info collection, register the merchant
      handleRegister()
      return
    }
    if (step < STEPS.length - 1) {
      setStep(step + 1)
    }
  }

  const handleBack = () => {
    if (step > 0) setStep(step - 1)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Merchant Setup</h1>
        <p className="text-gray-400 mt-1">
          Set up Pay with Sardis for your business in 5 simple steps
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.title} className="flex items-center">
            <button
              onClick={() => i <= step ? setStep(i) : undefined}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors',
                i === step
                  ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                  : i < step
                    ? 'text-sardis-400/60 hover:text-sardis-400'
                    : 'text-gray-500'
              )}
            >
              {i < step ? (
                <Check className="w-4 h-4 text-sardis-400" />
              ) : (
                <s.icon className="w-4 h-4" />
              )}
              <span className="hidden md:inline">{s.title}</span>
              <span className="md:hidden">{i + 1}</span>
            </button>
            {i < STEPS.length - 1 && (
              <ChevronRight className="w-4 h-4 text-gray-600 mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="card p-8 space-y-6">
        {/* Step 1: Business Details */}
        {step === 0 && (
          <>
            <div>
              <h2 className="text-xl font-semibold text-white">Business Details</h2>
              <p className="text-gray-400 text-sm mt-1">
                Tell us about your business
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Business Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={form.business_name}
                  onChange={(e) => updateField('business_name', e.target.value)}
                  placeholder="Acme Corp"
                  className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Website
                </label>
                <input
                  type="url"
                  value={form.website}
                  onChange={(e) => updateField('website', e.target.value)}
                  placeholder="https://acme.com"
                  className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Logo URL
                </label>
                <input
                  type="url"
                  value={form.logo_url}
                  onChange={(e) => updateField('logo_url', e.target.value)}
                  placeholder="https://acme.com/logo.png"
                  className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Category
                </label>
                <Select value={form.category} onValueChange={(v) => updateField('category', v)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a category..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="saas">SaaS</SelectItem>
                    <SelectItem value="ecommerce">E-Commerce</SelectItem>
                    <SelectItem value="marketplace">Marketplace</SelectItem>
                    <SelectItem value="ai_services">AI Services</SelectItem>
                    <SelectItem value="defi">DeFi</SelectItem>
                    <SelectItem value="gaming">Gaming</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </>
        )}

        {/* Step 2: Settlement Wallet */}
        {step === 1 && (
          <>
            <div>
              <h2 className="text-xl font-semibold text-white">Settlement Wallet</h2>
              <p className="text-gray-400 text-sm mt-1">
                Where should payments be settled?
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex gap-4">
                <button
                  onClick={() => updateField('use_sardis_wallet', true)}
                  className={clsx(
                    'flex-1 p-4 border text-left transition-colors',
                    form.use_sardis_wallet
                      ? 'border-sardis-500/50 bg-sardis-500/5'
                      : 'border-dark-100 bg-dark-200 hover:border-dark-50'
                  )}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Wallet className={clsx('w-5 h-5', form.use_sardis_wallet ? 'text-sardis-400' : 'text-gray-400')} />
                    <span className={clsx('font-medium', form.use_sardis_wallet ? 'text-sardis-400' : 'text-gray-300')}>
                      Create Sardis Wallet
                    </span>
                  </div>
                  <p className="text-xs text-gray-400">
                    Auto-provision a USDC settlement wallet. Recommended for fastest setup.
                  </p>
                </button>

                <button
                  onClick={() => updateField('use_sardis_wallet', false)}
                  className={clsx(
                    'flex-1 p-4 border text-left transition-colors',
                    !form.use_sardis_wallet
                      ? 'border-sardis-500/50 bg-sardis-500/5'
                      : 'border-dark-100 bg-dark-200 hover:border-dark-50'
                  )}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <ExternalLink className={clsx('w-5 h-5', !form.use_sardis_wallet ? 'text-sardis-400' : 'text-gray-400')} />
                    <span className={clsx('font-medium', !form.use_sardis_wallet ? 'text-sardis-400' : 'text-gray-300')}>
                      External Wallet
                    </span>
                  </div>
                  <p className="text-xs text-gray-400">
                    Use your own EVM address for direct USDC settlement.
                  </p>
                </button>
              </div>

              {!form.use_sardis_wallet && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Settlement Address <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.settlement_address}
                    onChange={(e) => updateField('settlement_address', e.target.value)}
                    placeholder="0x..."
                    className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 font-mono text-sm"
                  />
                </div>
              )}
            </div>
          </>
        )}

        {/* Step 3: Webhook URL */}
        {step === 2 && (
          <>
            <div>
              <h2 className="text-xl font-semibold text-white">Webhook URL</h2>
              <p className="text-gray-400 text-sm mt-1">
                Receive real-time payment notifications (optional)
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Webhook Endpoint
                </label>
                <input
                  type="url"
                  value={form.webhook_url}
                  onChange={(e) => updateField('webhook_url', e.target.value)}
                  placeholder="https://api.acme.com/webhooks/sardis"
                  className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div className="p-4 bg-dark-200 border border-dark-100">
                <p className="text-sm text-gray-400">
                  Sardis will send <code className="text-sardis-400 bg-dark-300 px-1.5 py-0.5">POST</code> requests
                  to this URL when payment events occur:
                </p>
                <ul className="mt-3 space-y-1.5 text-sm text-gray-400">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-sardis-400 rounded-full" />
                    <code className="text-gray-300">checkout.session.completed</code>
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-sardis-400 rounded-full" />
                    <code className="text-gray-300">checkout.session.expired</code>
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-sardis-400 rounded-full" />
                    <code className="text-gray-300">settlement.completed</code>
                  </li>
                </ul>
              </div>
            </div>
          </>
        )}

        {/* Step 4: Embed Code */}
        {step === 3 && (
          <>
            <div>
              <h2 className="text-xl font-semibold text-white">Your Embed Code</h2>
              <p className="text-gray-400 text-sm mt-1">
                Add this snippet to your website to accept payments with Sardis
              </p>
            </div>

            {registerMutation.isPending && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-sardis-400 animate-spin" />
                <span className="ml-3 text-gray-400">Registering your merchant account...</span>
              </div>
            )}

            {registerMutation.isError && (
              <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 text-red-400">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <div>
                  <p className="font-medium">Registration failed</p>
                  <p className="text-sm mt-1">{(registerMutation.error as Error)?.message || 'Please try again'}</p>
                </div>
              </div>
            )}

            {result && (
              <div className="space-y-6">
                {/* Credentials */}
                <div className="p-4 bg-dark-200 border border-dark-100 space-y-3">
                  <h3 className="text-sm font-medium text-white">Client Credentials</h3>
                  <p className="text-xs text-yellow-400">
                    Save these credentials securely. The client secret will not be shown again.
                  </p>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Client ID</span>
                      <button
                        onClick={() => copyToClipboard(result.credentials.client_id, 'client_id')}
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        {copied === 'client_id' ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <code className="block w-full px-3 py-2 bg-dark-300 text-sardis-400 text-sm font-mono">
                      {result.credentials.client_id}
                    </code>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Client Secret</span>
                      <button
                        onClick={() => copyToClipboard(result.credentials.client_secret, 'client_secret')}
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                      >
                        <Copy className="w-3 h-3" />
                        {copied === 'client_secret' ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <code className="block w-full px-3 py-2 bg-dark-300 text-sardis-400 text-sm font-mono break-all">
                      {result.credentials.client_secret}
                    </code>
                  </div>
                </div>

                {/* Embed snippet */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-white">HTML Embed Snippet</h3>
                    <button
                      onClick={() => copyToClipboard(result.embed_snippet, 'snippet')}
                      className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                      {copied === 'snippet' ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <pre className="w-full px-4 py-3 bg-dark-300 border border-dark-100 text-sardis-400 text-sm font-mono overflow-x-auto whitespace-pre">
                    {result.embed_snippet}
                  </pre>
                </div>

                {/* Merchant ID */}
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400">Merchant ID:</span>
                  <code className="text-gray-300 font-mono">{result.merchant_id}</code>
                </div>
              </div>
            )}
          </>
        )}

        {/* Step 5: Test Payment */}
        {step === 4 && (
          <>
            <div>
              <h2 className="text-xl font-semibold text-white">Test Payment</h2>
              <p className="text-gray-400 text-sm mt-1">
                Verify your integration works end-to-end
              </p>
            </div>

            <div className="space-y-6">
              <div className="p-6 bg-dark-200 border border-dark-100 text-center space-y-4">
                {testStatus === 'idle' && (
                  <>
                    <CreditCard className="w-12 h-12 text-gray-500 mx-auto" />
                    <p className="text-gray-400">
                      Send a $1.00 USDC test payment to verify your checkout flow.
                    </p>
                    <button
                      onClick={handleTestPayment}
                      className="px-6 py-3 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors"
                    >
                      Send Test Payment
                    </button>
                  </>
                )}

                {testStatus === 'sending' && (
                  <>
                    <Loader2 className="w-12 h-12 text-sardis-400 mx-auto animate-spin" />
                    <p className="text-gray-400">Processing test payment...</p>
                  </>
                )}

                {testStatus === 'success' && (
                  <>
                    <div className="w-12 h-12 bg-green-500/10 border border-green-500/30 flex items-center justify-center mx-auto">
                      <Check className="w-6 h-6 text-green-400" />
                    </div>
                    <p className="text-green-400 font-medium">Test session created!</p>
                    <p className="text-sm text-gray-400">
                      Open the checkout page below to test the payment flow end-to-end.
                    </p>
                    {testCheckoutUrl && (
                      <a
                        href={testCheckoutUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors text-sm"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open Checkout Page
                      </a>
                    )}
                  </>
                )}

                {testStatus === 'error' && (
                  <>
                    <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
                    <p className="text-red-400 font-medium">Test payment failed</p>
                    <button
                      onClick={handleTestPayment}
                      className="text-sm text-sardis-400 hover:text-sardis-300 transition-colors"
                    >
                      Retry
                    </button>
                  </>
                )}
              </div>

              {testStatus === 'success' && (
                <div className="flex justify-center">
                  <button
                    onClick={() => router.push('/merchants')}
                    className="px-8 py-3 bg-sardis-500 text-white font-medium hover:bg-sardis-400 transition-colors"
                  >
                    Go to Merchant Dashboard
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Navigation buttons */}
      <div className="flex justify-between">
        <button
          onClick={handleBack}
          disabled={step === 0}
          className={clsx(
            'flex items-center gap-2 px-6 py-3 font-medium transition-colors',
            step === 0
              ? 'text-gray-600 cursor-not-allowed'
              : 'text-gray-300 hover:text-white border border-dark-100 hover:border-sardis-500/30'
          )}
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>

        {step < STEPS.length - 1 && (
          <button
            onClick={handleNext}
            disabled={!canProceed() || registerMutation.isPending}
            className={clsx(
              'flex items-center gap-2 px-6 py-3 font-medium transition-colors',
              canProceed() && !registerMutation.isPending
                ? 'bg-sardis-500 text-white hover:bg-sardis-400'
                : 'bg-dark-200 text-gray-500 cursor-not-allowed'
            )}
          >
            {registerMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Registering...
              </>
            ) : (
              <>
                {step === 2 ? 'Register & Continue' : 'Continue'}
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}
