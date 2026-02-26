import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi, paymentApi, merchantApi, webhookApi, healthApi, enterpriseSupportApi } from '../api/client'
import type { WebhookSubscription } from '../types'

// Agents
export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: agentApi.list,
  })
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: ['agent', agentId],
    queryFn: () => agentApi.get(agentId),
    enabled: !!agentId,
  })
}

export function useAgentWallet(agentId: string) {
  return useQuery({
    queryKey: ['agent-wallet', agentId],
    queryFn: () => agentApi.getWallet(agentId),
    enabled: !!agentId,
  })
}

export function useAgentTransactions(agentId: string) {
  return useQuery({
    queryKey: ['agent-transactions', agentId],
    queryFn: () => agentApi.getTransactions(agentId),
    enabled: !!agentId,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: agentApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })
}

export function useInstructAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ agentId, instruction }: { agentId: string; instruction: string }) =>
      agentApi.instruct(agentId, instruction),
    onSuccess: (_, variables) => {
      // Invalidate wallet and transactions to show updates after instruction
      queryClient.invalidateQueries({ queryKey: ['agent-wallet', variables.agentId] })
      queryClient.invalidateQueries({ queryKey: ['agent-transactions', variables.agentId] })
    },
  })
}

// Merchants
export function useMerchants() {
  return useQuery({
    queryKey: ['merchants'],
    queryFn: merchantApi.list,
  })
}

export function useCreateMerchant() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: merchantApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['merchants'] })
    },
  })
}

// Webhooks
export function useWebhooks() {
  return useQuery({
    queryKey: ['webhooks'],
    queryFn: webhookApi.list,
  })
}

export function useCreateWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: webhookApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WebhookSubscription> }) => webhookApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: webhookApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

// Payments
export function usePaymentEstimate(amount: string, currency = 'USDC') {
  return useQuery({
    queryKey: ['payment-estimate', amount, currency],
    queryFn: () => paymentApi.estimate(amount, currency),
    enabled: !!amount && parseFloat(amount) > 0,
  })
}

export function useCreatePayment() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: paymentApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      queryClient.invalidateQueries({ queryKey: ['agent-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['agent-transactions'] })
    },
  })
}

// Health
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: healthApi.check,
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

// Enterprise support
export function useSupportProfile() {
  return useQuery({
    queryKey: ['support-profile'],
    queryFn: enterpriseSupportApi.profile,
  })
}

export function useSupportTickets(filters?: {
  status_filter?: 'open' | 'acknowledged' | 'resolved' | 'closed'
  priority?: 'low' | 'medium' | 'high' | 'urgent'
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['support-tickets', filters?.status_filter, filters?.priority, filters?.limit, filters?.offset],
    queryFn: () => enterpriseSupportApi.listTickets(filters),
  })
}

export function useCreateSupportTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: enterpriseSupportApi.createTicket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['support-profile'] })
    },
  })
}

export function useAcknowledgeSupportTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (ticketId: string) => enterpriseSupportApi.acknowledgeTicket(ticketId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
    },
  })
}

export function useResolveSupportTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ticketId, resolutionNote }: { ticketId: string; resolutionNote?: string }) =>
      enterpriseSupportApi.resolveTicket(ticketId, resolutionNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['support-tickets'] })
    },
  })
}
