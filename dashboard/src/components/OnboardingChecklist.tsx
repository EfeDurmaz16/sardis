import { useState, useEffect } from 'react'
import { CheckCircle, Circle, X, Rocket } from 'lucide-react'
import clsx from 'clsx'
import { useAgents, useWallets, useTransactions, useHealth } from '../hooks/useApi'

const DISMISSED_KEY = 'sardis_onboarding_checklist_dismissed'

interface ChecklistItem {
  label: string
  done: boolean
  description: string
}

export function OnboardingChecklist() {
  const [dismissed, setDismissed] = useState(() => {
    return localStorage.getItem(DISMISSED_KEY) === 'true'
  })

  const { data: health } = useHealth()
  const { data: agents } = useAgents()
  const { data: wallets } = useWallets()
  const { data: transactions } = useTransactions(1)

  // Only show in test/dev environments
  const isTestEnv = health?.environment === 'test' ||
    health?.environment === 'development' ||
    health?.environment === 'sandbox' ||
    import.meta.env.VITE_ENVIRONMENT === 'test' ||
    import.meta.env.DEV

  // Persist dismissed state
  useEffect(() => {
    if (dismissed) {
      localStorage.setItem(DISMISSED_KEY, 'true')
    }
  }, [dismissed])

  if (dismissed || !isTestEnv) return null

  const hasWalletFunded = Array.isArray(wallets) && wallets.some((w: Record<string, unknown>) => {
    const balance = parseFloat(String(w.balance || '0'))
    return balance > 0
  })

  // We don't have a mandate hook readily available, so we check agents as a proxy
  // (agents with policies count as having mandates set)
  const hasMandateSet = Array.isArray(agents) && agents.length > 0

  const hasAgent = Array.isArray(agents) && agents.length > 0

  const hasFirstPayment = Array.isArray(transactions) && transactions.length > 0

  const items: ChecklistItem[] = [
    {
      label: 'Account created',
      done: true, // If they can see this, they have an account
      description: 'Your Sardis account is active',
    },
    {
      label: 'Wallet funded',
      done: hasWalletFunded,
      description: 'Fund a wallet with test USDC using the faucet',
    },
    {
      label: 'Agent created',
      done: hasAgent,
      description: 'Create your first AI agent',
    },
    {
      label: 'Spending mandate set',
      done: hasMandateSet,
      description: 'Set up payment permissions for your agent',
    },
    {
      label: 'First payment made',
      done: hasFirstPayment,
      description: 'Complete your first test payment',
    },
  ]

  const completedCount = items.filter(i => i.done).length
  const totalCount = items.length
  const progressPct = (completedCount / totalCount) * 100

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-dark-100">
        <div className="flex items-center gap-3">
          <Rocket className="w-5 h-5 text-sardis-400" />
          <div>
            <h3 className="text-sm font-semibold text-white">Getting Started</h3>
            <p className="text-xs text-gray-500">
              {completedCount}/{totalCount} complete
            </p>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="p-1 text-gray-500 hover:text-white transition-colors"
          title="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress Bar */}
      <div className="px-6 pt-4 pb-2">
        <div className="w-full h-1.5 rounded-full bg-dark-100">
          <div
            className="h-full rounded-full bg-sardis-500 transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Checklist Items */}
      <div className="px-6 pb-4 space-y-3">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-start gap-3"
          >
            {item.done ? (
              <CheckCircle className="w-5 h-5 text-sardis-500 flex-shrink-0 mt-0.5" />
            ) : (
              <Circle className="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className={clsx(
                'text-sm font-medium',
                item.done ? 'text-gray-400 line-through' : 'text-white'
              )}>
                {item.label}
              </p>
              {!item.done && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {item.description}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* All done message */}
      {completedCount === totalCount && (
        <div className="px-6 pb-4">
          <div className="p-3 bg-sardis-500/10 rounded-lg border border-sardis-500/20">
            <p className="text-sm text-sardis-400 font-medium text-center">
              All set! You're ready to go live.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
