import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle,
  Drop,
  SpinnerGap,
  XCircle,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { faucetApi } from '../api/client'
import { useHealth } from '../hooks/useApi'

export function FaucetButton() {
  const queryClient = useQueryClient()
  const { data: health } = useHealth()
  const [feedback, setFeedback] = useState<'success' | 'error' | null>(null)

  const isTestEnv = health?.environment === 'test' ||
    health?.environment === 'development' ||
    health?.environment === 'sandbox' ||
    import.meta.env.VITE_ENVIRONMENT === 'test' ||
    import.meta.env.DEV

  const drip = useMutation({
    mutationFn: faucetApi.drip,
    onSuccess: () => {
      setFeedback('success')
      // Invalidate balance-related queries so the UI refreshes
      queryClient.invalidateQueries({ queryKey: ['wallets'] })
      queryClient.invalidateQueries({ queryKey: ['agent-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['billing-account'] })
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: () => {
      setFeedback('error')
      setTimeout(() => setFeedback(null), 3000)
    },
  })

  // Only show in test/dev environments
  if (!isTestEnv) return null

  return (
    <button
      onClick={() => drip.mutate()}
      disabled={drip.isPending}
      className={clsx(
        'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 border',
        feedback === 'success'
          ? 'bg-green-500/10 text-green-400 border-green-500/30'
          : feedback === 'error'
          ? 'bg-red-500/10 text-red-400 border-red-500/30'
          : 'bg-blue-500/10 text-blue-400 border-blue-500/30 hover:bg-blue-500/20',
        drip.isPending && 'opacity-50 cursor-not-allowed'
      )}
    >
      {drip.isPending ? (
        <>
          <SpinnerGap className="w-4 h-4 animate-spin" />
          Requesting...
        </>
      ) : feedback === 'success' ? (
        <>
          <CheckCircle className="w-4 h-4" />
          100 Test USDC sent
        </>
      ) : feedback === 'error' ? (
        <>
          <XCircle className="w-4 h-4" />
          Faucet failed
        </>
      ) : (
        <>
          <Drop className="w-4 h-4" />
          Get 100 Test USDC
        </>
      )}
    </button>
  )
}
