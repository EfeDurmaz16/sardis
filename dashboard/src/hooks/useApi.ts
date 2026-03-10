import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi, paymentApi, merchantApi, webhookApi, healthApi, enterpriseSupportApi, killSwitchApi, approvalsApi, evidenceApi, policiesApi, simulationApi, policyTestApi, exceptionsApi, anomalyApi, billingApi, walletsApi } from '../api/client'
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

// Kill Switch
export function useKillSwitchStatus() {
  return useQuery({
    queryKey: ['kill-switch-status'],
    queryFn: killSwitchApi.status,
    refetchInterval: 10000,
  })
}

export function useActivateKillSwitchRail() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ rail, data }: { rail: string; data: { reason: string; notes?: string; auto_reactivate_after_seconds?: number } }) =>
      killSwitchApi.activateRail(rail, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch-status'] })
    },
  })
}

export function useDeactivateKillSwitchRail() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (rail: string) => killSwitchApi.deactivateRail(rail),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch-status'] })
    },
  })
}

export function useActivateKillSwitchChain() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ chain, data }: { chain: string; data: { reason: string; notes?: string; auto_reactivate_after_seconds?: number } }) =>
      killSwitchApi.activateChain(chain, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch-status'] })
    },
  })
}

export function useDeactivateKillSwitchChain() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (chain: string) => killSwitchApi.deactivateChain(chain),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kill-switch-status'] })
    },
  })
}

// Approvals
export function usePendingApprovals() {
  return useQuery({
    queryKey: ['approvals-pending'],
    queryFn: approvalsApi.listPending,
    refetchInterval: 15000,
  })
}

export function useApprovals(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: ['approvals', params?.status, params?.limit],
    queryFn: () => approvalsApi.list(params),
  })
}

export function useApproveApproval() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      approvalsApi.approve(id, { notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] })
    },
  })
}

export function useDenyApproval() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      approvalsApi.deny(id, { reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] })
    },
  })
}

// Evidence
export function useTransactionEvidence(txId: string) {
  return useQuery({
    queryKey: ['evidence', txId],
    queryFn: () => evidenceApi.getTransactionEvidence(txId),
    enabled: !!txId,
  })
}

export function usePolicyDecisions(agentId: string, params?: { limit?: number }) {
  return useQuery({
    queryKey: ['policy-decisions', agentId, params?.limit],
    queryFn: () => evidenceApi.listPolicyDecisions(agentId, params),
    enabled: !!agentId,
  })
}

// Policies
export function usePolicy(agentId: string) {
  return useQuery({
    queryKey: ['policy', agentId],
    queryFn: () => policiesApi.get(agentId),
    enabled: !!agentId,
  })
}

export function useParsePolicy() {
  return useMutation({
    mutationFn: (naturalLanguage: string) =>
      policiesApi.parse({ natural_language: naturalLanguage }),
  })
}

export function usePreviewPolicy() {
  return useMutation({
    mutationFn: ({ agentId, naturalLanguage }: { agentId: string; naturalLanguage: string }) =>
      policiesApi.preview({ agent_id: agentId, natural_language: naturalLanguage }),
  })
}

export function useApplyPolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ agentId, naturalLanguage }: { agentId: string; naturalLanguage: string }) =>
      policiesApi.apply({ agent_id: agentId, natural_language: naturalLanguage, confirm: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policy'] })
    },
  })
}

export function useCheckPolicy() {
  return useMutation({
    mutationFn: (data: { agent_id: string; amount: string; currency?: string; merchant_id?: string; mcc_code?: string }) =>
      policiesApi.check(data),
  })
}

// Live simulation — dry-run through the full control-plane pipeline
export function useSimulate() {
  return useMutation({
    mutationFn: simulationApi.simulate,
  })
}

// Draft policy testing — what-if analysis without executing
export function usePolicyTestDraft() {
  return useMutation({
    mutationFn: policyTestApi.testDraft,
  })
}

// Exceptions
export function useExceptions(params?: { agent_id?: string; status?: string; limit?: number }) {
  return useQuery({
    queryKey: ['exceptions', params?.agent_id, params?.status, params?.limit],
    queryFn: () => exceptionsApi.list(params),
  })
}

export function useException(exceptionId: string) {
  return useQuery({
    queryKey: ['exception', exceptionId],
    queryFn: () => exceptionsApi.get(exceptionId),
    enabled: !!exceptionId,
  })
}

export function useResolveException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      exceptionsApi.resolve(id, { resolution_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exceptions'] })
    },
  })
}

export function useEscalateException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      exceptionsApi.escalate(id, { notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exceptions'] })
    },
  })
}

export function useRetryException() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => exceptionsApi.retry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exceptions'] })
    },
  })
}

// Anomaly
export function useAnomalyEvents(params?: { agent_id?: string; min_score?: number; limit?: number }) {
  return useQuery({
    queryKey: ['anomaly-events', params?.agent_id, params?.min_score, params?.limit],
    queryFn: () => anomalyApi.events(params),
    refetchInterval: 15000,
  })
}

export function useAnomalyConfig() {
  return useQuery({
    queryKey: ['anomaly-config'],
    queryFn: anomalyApi.config,
  })
}

export function useUpdateAnomalyConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: anomalyApi.updateConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['anomaly-config'] })
    },
  })
}

export function useAssessRisk() {
  return useMutation({
    mutationFn: anomalyApi.assess,
  })
}

// Billing
export function useBillingAccount() {
  return useQuery({
    queryKey: ['billing-account'],
    queryFn: billingApi.account,
    retry: false,
  })
}

// Transactions
export function useTransactions(limit = 50) {
  return useQuery({
    queryKey: ['transactions', limit],
    queryFn: () => paymentApi.getHistory(limit),
  })
}

// Wallets
export function useWallets() {
  return useQuery({
    queryKey: ['wallets'],
    queryFn: walletsApi.list,
  })
}

export function useWallet(walletId: string) {
  return useQuery({
    queryKey: ['wallet', walletId],
    queryFn: () => walletsApi.get(walletId),
    enabled: !!walletId,
  })
}

export function usePolicyHistory(walletId: string) {
  return useQuery({
    queryKey: ['policy-history', walletId],
    queryFn: () => walletsApi.history(walletId),
    enabled: !!walletId,
  })
}
