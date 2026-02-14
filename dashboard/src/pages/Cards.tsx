import { useState, useEffect } from 'react'
import { CreditCard, Plus, ShoppingCart, Snowflake, Sun, Trash2, RefreshCw, ChevronDown, Copy, Check } from 'lucide-react'
import clsx from 'clsx'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentApi, cardsApi } from '../api/client'
import type { Agent } from '../types'

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
}

type CardTransaction = {
  transaction_id: string
  merchant_name?: string
  merchant_category?: string
  status?: string
  provider_tx_id?: string
  amount?: number | string
  currency?: string
}

type IssueCardInput = {
  wallet_id: string
  limit_per_tx: string
  limit_daily: string
  limit_monthly: string
}

type SimulatePurchaseResult = {
  policy?: {
    allowed?: boolean
    reason?: string
  }
  provider_tx_id?: string
  transaction?: {
    transaction_id?: string
  }
}

const SEED_AGENTS = [
  { agent_id: 'agent_shopping_001', name: 'shopping_agent', wallet_id: 'wallet_demo_001' },
  { agent_id: 'agent_research_002', name: 'research_analyst', wallet_id: 'wallet_demo_002' },
]

const SEED_CARDS = [
  {
    card_id: 'card_demo_001',
    provider_card_id: 'lith_sandbox_a1b2c3',
    status: 'active',
    card_number_last4: '4242',
    limit_per_tx: 100,
    limit_daily: 500,
    limit_monthly: 2000,
    wallet_id: 'wallet_demo_001',
  },
  {
    card_id: 'card_demo_002',
    provider_card_id: 'lith_sandbox_d4e5f6',
    status: 'frozen',
    card_number_last4: '8888',
    limit_per_tx: 50,
    limit_daily: 200,
    limit_monthly: 1000,
    wallet_id: 'wallet_demo_001',
  },
]

export default function CardsPage() {
  const queryClient = useQueryClient()
  const { data: apiAgents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agentApi.list,
  })

  const agents: AgentOption[] = apiAgents.length > 0 ? apiAgents : SEED_AGENTS

  const [selectedAgentId, setSelectedAgentId] = useState<string>('')
  const [showIssue, setShowIssue] = useState(false)
  const [showPurchase, setShowPurchase] = useState<string | null>(null)
  const [expandedCard, setExpandedCard] = useState<string | null>(null)

  const selectedAgent = agents.find((agent) => agent.agent_id === selectedAgentId)
  const walletId = selectedAgent?.wallet_id || ''

  useEffect(() => {
    if (agents.length > 0 && !selectedAgentId) {
      const first = agents.find((agent) => agent.wallet_id)
      if (first) setSelectedAgentId(first.agent_id)
    }
  }, [agents, selectedAgentId])

  const { data: apiCards = [], isLoading: cardsLoading, refetch: refetchCards } = useQuery<CardRecord[]>({
    queryKey: ['cards', walletId],
    queryFn: async () => (await cardsApi.list(walletId)) as CardRecord[],
    enabled: !!walletId,
  })

  // Use seed cards if API returns empty and using seed agents
  const cards: CardRecord[] = apiCards.length > 0 ? apiCards : (apiAgents.length === 0 ? SEED_CARDS : [])

  const issueMutation = useMutation({
    mutationFn: cardsApi.issue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cards', walletId] })
      setShowIssue(false)
    },
  })

  const freezeMutation = useMutation({
    mutationFn: cardsApi.freeze,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cards', walletId] }),
  })

  const unfreezeMutation = useMutation({
    mutationFn: cardsApi.unfreeze,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cards', walletId] }),
  })

  const cancelMutation = useMutation({
    mutationFn: cardsApi.cancel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cards', walletId] }),
  })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Cards</h1>
          <p className="text-gray-400 mt-1">Issue and manage virtual cards for your agents</p>
        </div>
        <button
          onClick={() => setShowIssue(true)}
          disabled={!walletId}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Plus className="w-5 h-5" />
          Issue Card
        </button>
      </div>

      {/* Agent Selector */}
      <div className="card p-4">
        <label className="block text-sm font-medium text-gray-400 mb-2">Select Agent</label>
        <div className="relative">
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white appearance-none focus:outline-none focus:border-sardis-500/50"
          >
            <option value="">Select an agent...</option>
            {agents.filter((agent) => agent.wallet_id).map((agent) => (
              <option key={agent.agent_id} value={agent.agent_id}>
                {agent.name} ({agent.agent_id})
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 pointer-events-none" />
        </div>
        {selectedAgent && !selectedAgent.wallet_id && (
          <p className="text-yellow-400 text-sm mt-2">This agent has no wallet. Create one first.</p>
        )}
      </div>

      {/* Cards Grid */}
      {agentsLoading || cardsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-56 rounded-2xl bg-dark-200 animate-pulse" />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <div className="card p-12 text-center">
          <CreditCard className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No cards yet</h3>
          <p className="text-gray-400 mb-4">
            {walletId ? 'Issue your first virtual card to get started' : 'Select an agent with a wallet first'}
          </p>
          {walletId && (
            <button
              onClick={() => setShowIssue(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Issue Card
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {cards.map((card) => (
            <div key={card.card_id} className="space-y-4">
              <SardisCard
                card={card}
                agentName={selectedAgent?.name}
                onFreeze={() => freezeMutation.mutate(card.card_id)}
                onUnfreeze={() => unfreezeMutation.mutate(card.card_id)}
                onCancel={() => cancelMutation.mutate(card.card_id)}
                onSimulate={() => setShowPurchase(card.card_id)}
                isExpanded={expandedCard === card.card_id}
                onToggleExpand={() => setExpandedCard(expandedCard === card.card_id ? null : card.card_id)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Refresh */}
      {cards.length > 0 && (
        <div className="flex justify-center">
          <button
            onClick={() => refetchCards()}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      )}

      {/* Issue Card Modal */}
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

      {/* Simulate Purchase Modal */}
      {showPurchase && (
        <SimulatePurchaseModal
          cardId={showPurchase}
          onClose={() => setShowPurchase(null)}
        />
      )}
    </div>
  )
}


/* ─── Visual Card Component ─── */

function SardisCard({
  card,
  agentName,
  onFreeze,
  onUnfreeze,
  onCancel,
  onSimulate,
  isExpanded,
  onToggleExpand,
}: {
  card: CardRecord
  agentName?: string
  onFreeze: () => void
  onUnfreeze: () => void
  onCancel: () => void
  onSimulate: () => void
  isExpanded: boolean
  onToggleExpand: () => void
}) {
  const isFrozen = card.status === 'frozen'
  const isCancelled = card.status === 'cancelled'
  const isActive = card.status === 'active' || card.status === 'pending'
  const last4 = card.card_number_last4 || card.provider_card_id?.slice(-4) || '****'

  return (
    <div className="space-y-3">
      {/* The Card */}
      <div
        onClick={onToggleExpand}
        className={clsx(
          'relative rounded-2xl p-6 cursor-pointer transition-all duration-300 overflow-hidden',
          'border select-none',
          isFrozen && 'border-blue-500/30 bg-gradient-to-br from-dark-300 via-dark-200 to-blue-950/30',
          isCancelled && 'border-red-500/30 bg-gradient-to-br from-dark-300 via-dark-200 to-red-950/20 opacity-60',
          isActive && 'border-sardis-500/30 bg-gradient-to-br from-dark-300 via-dark-200 to-sardis-500/5',
          isActive && 'hover:border-sardis-500/50 hover:shadow-[0_0_30px_rgba(255,79,0,0.08)]',
        )}
      >
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-[0.03]" style={{
          backgroundImage: 'radial-gradient(circle at 70% 30%, rgba(255,79,0,0.8), transparent 50%), radial-gradient(circle at 30% 70%, rgba(255,79,0,0.4), transparent 50%)',
        }} />

        {/* Top row: logo + status */}
        <div className="relative flex items-start justify-between mb-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-sardis-500 rounded-lg flex items-center justify-center">
              <CreditCard className="w-4 h-4 text-dark-400" />
            </div>
            <span className="text-sm font-bold text-sardis-400 tracking-wider">SARDIS</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={clsx(
              'status-dot',
              isActive ? 'success' : isFrozen ? 'bg-blue-400' : 'error'
            )} />
            <span className={clsx(
              'text-xs font-medium uppercase tracking-wider',
              isActive && 'text-sardis-400',
              isFrozen && 'text-blue-400',
              isCancelled && 'text-red-400',
            )}>
              {card.status}
            </span>
          </div>
        </div>

        {/* Card number */}
        <div className="relative mb-6">
          <p className="text-xl font-mono text-white tracking-[0.2em]">
            <span className="text-gray-500">••••</span>
            {' '}
            <span className="text-gray-500">••••</span>
            {' '}
            <span className="text-gray-500">••••</span>
            {' '}
            <span>{last4}</span>
          </p>
        </div>

        {/* Bottom row: agent + limits */}
        <div className="relative flex items-end justify-between">
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">Virtual Card</p>
            <p className="text-sm text-gray-300">{agentName || 'Agent'}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">Daily Limit</p>
            <p className="text-sm text-white font-mono">${Number(card.limit_daily || 0).toFixed(2)}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">Per TX</p>
            <p className="text-sm text-white font-mono">${Number(card.limit_per_tx || 0).toFixed(2)}</p>
          </div>
        </div>

        {/* Frozen overlay */}
        {isFrozen && (
          <div className="absolute top-4 right-4">
            <Snowflake className="w-5 h-5 text-blue-400 animate-pulse" />
          </div>
        )}
      </div>

      {/* Expanded Actions */}
      {isExpanded && (
        <div className="card p-4 space-y-3 animate-in slide-in-from-top-2">
          {/* Card ID */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Card ID</span>
            <CopyableText text={card.card_id} />
          </div>
          {card.provider_card_id && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Provider ID</span>
              <CopyableText text={card.provider_card_id} />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            {isActive && (
              <>
                <button
                  onClick={onSimulate}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors text-sm"
                >
                  <ShoppingCart className="w-4 h-4" />
                  Simulate Purchase
                </button>
                <button
                  onClick={onFreeze}
                  className="flex items-center justify-center gap-2 px-3 py-2 bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition-colors text-sm"
                >
                  <Snowflake className="w-4 h-4" />
                  Freeze
                </button>
              </>
            )}
            {isFrozen && (
              <button
                onClick={onUnfreeze}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-yellow-500/10 text-yellow-400 rounded-lg hover:bg-yellow-500/20 transition-colors text-sm"
              >
                <Sun className="w-4 h-4" />
                Unfreeze
              </button>
            )}
            {!isCancelled && (
              <button
                onClick={onCancel}
                className="flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-colors text-sm"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Transactions */}
          <CardTransactions cardId={card.card_id} />
        </div>
      )}
    </div>
  )
}


/* ─── Card Transactions ─── */

function CardTransactions({ cardId }: { cardId: string }) {
  const { data: transactions = [], isLoading } = useQuery<CardTransaction[]>({
    queryKey: ['card-transactions', cardId],
    queryFn: async () => (await cardsApi.listTransactions(cardId)) as CardTransaction[],
  })

  if (isLoading) {
    return <div className="py-3 text-center text-sm text-gray-500">Loading transactions...</div>
  }

  if (transactions.length === 0) {
    return <div className="py-3 text-center text-sm text-gray-500">No transactions yet</div>
  }

  return (
    <div className="space-y-2 pt-2 border-t border-dark-100">
      <p className="text-xs text-gray-500 uppercase tracking-wider">Recent Transactions</p>
      {transactions.slice(0, 5).map((tx) => (
        <div key={tx.transaction_id} className="flex items-center justify-between py-2 px-3 bg-dark-300/50 rounded-lg">
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{tx.merchant_name || 'Unknown'}</p>
            <div className="flex items-center gap-2">
              <p className="text-xs text-gray-500">{tx.status}</p>
              {tx.provider_tx_id && !tx.provider_tx_id.startsWith('txn_sim_') && (
                <span className="text-xs text-sardis-400 font-mono">
                  Lithic: {tx.provider_tx_id.slice(0, 12)}...
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className={clsx(
              'text-sm font-mono',
              tx.status === 'declined' || tx.status === 'declined_policy' ? 'text-red-400' : 'text-white'
            )}>
              ${Number(tx.amount || 0).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500">{tx.currency || 'USD'}</p>
          </div>
        </div>
      ))}
    </div>
  )
}


/* ─── Copyable Text ─── */

function CopyableText({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button onClick={handleCopy} className="flex items-center gap-1 text-gray-300 hover:text-white transition-colors font-mono text-xs">
      {text.length > 20 ? `${text.slice(0, 10)}...${text.slice(-6)}` : text}
      {copied ? <Check className="w-3 h-3 text-sardis-400" /> : <Copy className="w-3 h-3" />}
    </button>
  )
}


/* ─── Issue Card Modal ─── */

function IssueCardModal({
  walletId,
  onClose,
  onSubmit,
  isLoading,
}: {
  walletId: string
  onClose: () => void
  onSubmit: (data: IssueCardInput) => Promise<void>
  isLoading: boolean
}) {
  const [formData, setFormData] = useState({
    limit_per_tx: '100.00',
    limit_daily: '500.00',
    limit_monthly: '2000.00',
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card max-w-md w-full mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-6">Issue Virtual Card</h2>
        <form
          onSubmit={async (e) => {
            e.preventDefault()
            await onSubmit({
              wallet_id: walletId,
              ...formData,
            })
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Per TX</label>
              <input
                type="text"
                required
                value={formData.limit_per_tx}
                onChange={(e) => setFormData(d => ({ ...d, limit_per_tx: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Daily</label>
              <input
                type="text"
                required
                value={formData.limit_daily}
                onChange={(e) => setFormData(d => ({ ...d, limit_daily: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Monthly</label>
              <input
                type="text"
                required
                value={formData.limit_monthly}
                onChange={(e) => setFormData(d => ({ ...d, limit_monthly: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Issuing...' : 'Issue Card'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


/* ─── Simulate Purchase Modal ─── */

function SimulatePurchaseModal({
  cardId,
  onClose,
}: {
  cardId: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    amount: '25.00',
    merchant_name: 'Demo Coffee Shop',
    mcc_code: '5812',
  })
  const [result, setResult] = useState<SimulatePurchaseResult | null>(null)

  const simulateMutation = useMutation({
    mutationFn: (data: { amount: string; merchant_name: string; mcc_code: string }) =>
      cardsApi.simulatePurchase(cardId, data),
    onSuccess: (data) => {
      setResult(data)
      queryClient.invalidateQueries({ queryKey: ['card-transactions', cardId] })
      queryClient.invalidateQueries({ queryKey: ['cards'] })
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card max-w-lg w-full mx-4 p-6">
        <h2 className="text-xl font-bold text-white mb-6">Simulate Purchase</h2>

        {!result ? (
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              await simulateMutation.mutateAsync(formData)
            }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Amount (USD)</label>
              <input
                type="text"
                required
                value={formData.amount}
                onChange={(e) => setFormData(d => ({ ...d, amount: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Merchant</label>
              <input
                type="text"
                required
                value={formData.merchant_name}
                onChange={(e) => setFormData(d => ({ ...d, merchant_name: e.target.value }))}
                className="w-full px-4 py-2 bg-dark-300 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50"
              />
            </div>

            {simulateMutation.isError && (
              <p className="text-red-400 text-sm">{String(simulateMutation.error?.message || 'Failed')}</p>
            )}

            <div className="flex gap-4 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={simulateMutation.isPending}
                className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
              >
                {simulateMutation.isPending ? 'Simulating...' : 'Run Simulation'}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            {/* Result */}
            <div className={clsx(
              'rounded-xl p-4 border',
              result.policy?.allowed
                ? 'bg-sardis-500/5 border-sardis-500/30'
                : 'bg-red-500/5 border-red-500/30'
            )}>
              <div className="flex items-center gap-2 mb-3">
                <div className={clsx(
                  'w-3 h-3 rounded-full',
                  result.policy?.allowed ? 'bg-sardis-500' : 'bg-red-500'
                )} />
                <span className={clsx(
                  'text-sm font-medium',
                  result.policy?.allowed ? 'text-sardis-400' : 'text-red-400'
                )}>
                  {result.policy?.allowed ? 'Transaction Approved' : 'Transaction Denied'}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Policy</span>
                  <span className="text-gray-300">{result.policy?.reason || 'OK'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Amount</span>
                  <span className="text-white font-mono">${formData.amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Merchant</span>
                  <span className="text-gray-300">{formData.merchant_name}</span>
                </div>
                {result.provider_tx_id && (
                  <div className="flex justify-between items-center pt-2 border-t border-dark-100">
                    <span className="text-sardis-400 font-medium">Lithic TX ID</span>
                    <CopyableText text={result.provider_tx_id} />
                  </div>
                )}
                {result.transaction?.transaction_id && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Internal TX</span>
                    <span className="text-gray-300 font-mono text-xs">{result.transaction.transaction_id}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-4">
              <button
                onClick={() => { setResult(null) }}
                className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors"
              >
                Run Another
              </button>
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
