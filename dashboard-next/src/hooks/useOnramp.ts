import { useMutation, useQueryClient } from '@tanstack/react-query'
import { walletsApi } from '@/api/client'

export type OnrampProvider = 'coinbase' | 'moonpay' | 'conduit'

export type PaymentMethod = 'card' | 'bank' | 'apple_pay' | 'google_pay'

export interface FundWalletRequest {
  walletId: string
  amount: string
  provider: OnrampProvider
  payment_method?: PaymentMethod
  target_chain?: string
}

export interface FundWalletResponse {
  fund_id: string
  wallet_id: string
  amount: string
  provider: OnrampProvider
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'quote_ready' | 'created'
  onramp_url?: string
  widget_session_id?: string
  new_balance?: string
  created_at: string
  // Conduit-specific
  quote_id?: string
  source_amount?: string
  target_amount?: string
  target_chain?: string
  target_token?: string
  deposit_instructions?: Record<string, unknown>
}

export function useFundWallet() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: FundWalletRequest) =>
      walletsApi.fund(data.walletId, {
        amount: data.amount,
        provider: data.provider,
        payment_method: data.payment_method,
        target_chain: data.target_chain,
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['wallets'] })
      queryClient.invalidateQueries({ queryKey: ['wallet', variables.walletId] })
      queryClient.invalidateQueries({ queryKey: ['agent-wallet'] })
    },
  })
}
