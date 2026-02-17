import { useMemo, useState } from 'react'
import { CheckCircle2, Copy, Sparkles, XCircle } from 'lucide-react'
import clsx from 'clsx'
import { agentApi, demoApi } from '../api/client'
import { getErrorMessage } from '../utils/errors'

type StepStatus = 'idle' | 'running' | 'done' | 'error'

type AgentWithAddress = {
  name?: string
  agent_id?: string
  external_id?: string
  wallet_id?: string
  addresses?: Record<string, string>
}

type DemoWallet = {
  wallet_id: string
  addresses: Record<string, string>
  card_id?: string
  id?: string
}

type DemoPolicy = {
  policy_id?: string
  limit_per_tx?: string
  limit_total?: string
}

type DemoCard = {
  card_id?: string
  cardId?: string
  id?: string
  status?: string
}

type DemoPurchaseResult = {
  policy?: {
    allowed?: boolean
    reason?: string
  }
  transaction?: {
    transaction_id?: string
    amount?: string
    currency?: string
  }
  card?: {
    status?: string
    provider_card_id?: string
  }
}

type DemoTransaction = {
  transaction_id: string
  status?: string
  merchant_name?: string
  merchant_category?: string
  amount?: string
  currency?: string
}

function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {subtitle ? <p className="text-sm text-gray-400 mt-1">{subtitle}</p> : null}
        </div>
      </div>
      <div className="mt-5">{children}</div>
    </div>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-gray-400 mb-2">{children}</label>
}

function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        'w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white',
        'placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 transition-colors',
        props.className
      )}
    />
  )
}

function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={clsx(
        'w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white',
        'placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 transition-colors resize-none',
        props.className
      )}
    />
  )
}

function StatusPill({ status }: { status: StepStatus }) {
  const cfg = {
    idle: { label: 'Idle', cls: 'bg-dark-200 text-gray-400 border-dark-100' },
    running: { label: 'Running', cls: 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30' },
    done: { label: 'Done', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
    error: { label: 'Error', cls: 'bg-red-500/10 text-red-400 border-red-500/30' },
  }[status]

  return <span className={clsx('text-xs px-2.5 py-1 rounded-full border', cfg.cls)}>{cfg.label}</span>
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1000)
        } catch {
          // ignore
        }
      }}
      className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-dark-200 border border-dark-100 rounded-lg text-gray-300 hover:text-white hover:bg-dark-100 transition-colors"
    >
      <Copy className="w-4 h-4" />
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function DemoPage() {
  const [orgId, setOrgId] = useState('org_demo')
  const [bootstrapStatus, setBootstrapStatus] = useState<StepStatus>('idle')
  const [bootstrapError, setBootstrapError] = useState<string>('')
  const [apiKey, setApiKey] = useState<string>('')

  const [agentId, setAgentId] = useState('agent_demo_001')
  const [agentExternalId, setAgentExternalId] = useState<string>('')
  const [walletStatus, setWalletStatus] = useState<StepStatus>('idle')
  const [walletError, setWalletError] = useState<string>('')
  const [wallet, setWallet] = useState<DemoWallet | null>(null)

  const [policyText, setPolicyText] = useState('Max $100 per transaction, block gambling')
  const [policyStatus, setPolicyStatus] = useState<StepStatus>('idle')
  const [policyError, setPolicyError] = useState<string>('')
  const [policy, setPolicy] = useState<DemoPolicy | null>(null)

  const [cardStatus, setCardStatus] = useState<StepStatus>('idle')
  const [cardError, setCardError] = useState<string>('')
  const [card, setCard] = useState<DemoCard | null>(null)

  const [purchaseAmount, setPurchaseAmount] = useState('25.00')
  const [purchaseMcc, setPurchaseMcc] = useState('7995')
  const [purchaseStatus, setPurchaseStatus] = useState<StepStatus>('idle')
  const [purchaseError, setPurchaseError] = useState<string>('')
  const [purchaseResult, setPurchaseResult] = useState<DemoPurchaseResult | null>(null)

  const merchantPresets = [
    { mcc: '7995', name: 'Demo Casino', label: 'Gambling', category: 'gambling' },
    { mcc: '5734', name: 'Demo Software', label: 'Software', category: 'technology' },
    { mcc: '5812', name: 'Demo Restaurant', label: 'Restaurant', category: 'dining' },
    { mcc: '5411', name: 'Demo Grocery', label: 'Grocery', category: 'groceries' },
    { mcc: '4511', name: 'Demo Airlines', label: 'Airline', category: 'travel' },
    { mcc: '5921', name: 'Demo Liquor', label: 'Alcohol', category: 'alcohol' },
  ]
  const selectedMerchant = merchantPresets.find((m) => m.mcc === purchaseMcc) || merchantPresets[0]

  const [txStatus, setTxStatus] = useState<StepStatus>('idle')
  const [txError, setTxError] = useState<string>('')
  const [transactions, setTransactions] = useState<DemoTransaction[]>([])

  const walletId = wallet?.wallet_id || wallet?.card_id || wallet?.id
  const cardId = card?.card_id || card?.cardId || card?.id

  const walletAddress = useMemo(() => {
    if (!wallet?.addresses) return null
    return wallet.addresses.base_sepolia || wallet.addresses.base || Object.values(wallet.addresses)[0]
  }, [wallet])

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white font-display">Demo Wizard</h1>
              <p className="text-gray-400 mt-1">
                End-to-end walkthrough: Turnkey wallet → policy → card → simulated purchase → enforcement.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card
          title="Step 0 — (Optional) Bootstrap API key"
          subtitle="Generates a server-to-server API key using admin JWT. Optional for demo, useful for programmatic access."
        >
          <div className="flex items-center justify-between gap-3">
            <StatusPill status={bootstrapStatus} />
            {apiKey ? <CopyButton value={apiKey} /> : null}
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <FieldLabel>Organization ID</FieldLabel>
              <TextInput value={orgId} onChange={(e) => setOrgId(e.target.value)} placeholder="org_demo" />
            </div>

            <button
              type="button"
              disabled={bootstrapStatus === 'running'}
              onClick={async () => {
                setBootstrapError('')
                setBootstrapStatus('running')
                try {
                  const res = await demoApi.bootstrapApiKey({
                    name: 'Demo Admin Key',
                    scopes: ['admin', '*'],
                    organization_id: orgId,
                  })
                  setApiKey(res.key)
                  setBootstrapStatus('done')
                } catch (error: unknown) {
                  setBootstrapError(getErrorMessage(error, 'Bootstrap failed'))
                  setBootstrapStatus('error')
                }
              }}
              className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Bootstrap API key
            </button>

            {bootstrapError ? (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {bootstrapError}
              </div>
            ) : null}

            {apiKey ? (
              <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                <div className="text-xs text-gray-400 mb-1">API key (shown once)</div>
                <div className="text-sm font-mono text-white break-all">{apiKey}</div>
              </div>
            ) : null}
          </div>
        </Card>

        <Card title="Step 1 — Create Turnkey wallet" subtitle="Creates a real non-custodial wallet and address via Turnkey MPC.">
          <div className="flex items-center justify-between gap-3">
            <StatusPill status={walletStatus} />
            {walletId ? <CopyButton value={walletId} /> : null}
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <FieldLabel>Agent ID</FieldLabel>
              <TextInput value={agentId} onChange={(e) => setAgentId(e.target.value)} placeholder="agent_demo_001" />
            </div>

            <button
              type="button"
              disabled={walletStatus === 'running'}
              onClick={async () => {
                setWalletError('')
                setWalletStatus('running')
                try {
                  // Create agent with wallet (create_wallet: true creates a basic wallet automatically)
                  let agent: AgentWithAddress | undefined
                  try {
                    agent = await agentApi.create({
                      name: agentId,
                      description: 'Demo agent created by wizard',
                      spending_limits: { per_transaction: '100.00', total: '1000.00' },
                      create_wallet: true,
                    })
                  } catch {
                    // Agent may already exist — fetch it
                    const agents = await agentApi.list()
                    agent = agents.find((existingAgent) => existingAgent.name === agentId || existingAgent.agent_id === agentId)
                  }
                  // Store the real external_id so policy apply uses the correct agent
                  const realId = agent?.agent_id || agent?.external_id || agentId
                  setAgentExternalId(realId)
                  if (agent?.wallet_id) {
                    setWallet({ wallet_id: agent.wallet_id, addresses: agent.addresses || {} })
                  } else {
                    setWallet({ wallet_id: realId, addresses: {} })
                  }
                  setWalletStatus('done')
                } catch (error: unknown) {
                  setWalletError(getErrorMessage(error, 'Agent/wallet creation failed'))
                  setWalletStatus('error')
                }
              }}
              className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create wallet
            </button>

            {walletError ? (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {walletError}
              </div>
            ) : null}

            {wallet ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <div className="text-xs text-gray-400">wallet_id</div>
                  <div className="text-sm font-mono text-white break-all">{wallet.wallet_id}</div>
                </div>
                <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <div className="text-xs text-gray-400">address</div>
                  <div className="text-sm font-mono text-white break-all">{walletAddress || '-'}</div>
                </div>
              </div>
            ) : null}
          </div>
        </Card>

        <Card title="Step 2 — Apply policy" subtitle='e.g. "Max $100 per transaction, block gambling".'>
          <div className="flex items-center justify-between gap-3">
            <StatusPill status={policyStatus} />
            {policy?.policy_id ? <CopyButton value={policy.policy_id} /> : null}
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <FieldLabel>Natural language policy</FieldLabel>
              <TextArea value={policyText} onChange={(e) => setPolicyText(e.target.value)} rows={3} />
            </div>

            <button
              type="button"
              disabled={policyStatus === 'running'}
              onClick={async () => {
                setPolicyError('')
                setPolicyStatus('running')
                try {
                  const res = await demoApi.applyPolicy({ agent_id: agentExternalId || agentId, natural_language: policyText })
                  setPolicy(res as DemoPolicy)
                  setPolicyStatus('done')
                } catch (error: unknown) {
                  setPolicyError(getErrorMessage(error, 'Policy apply failed'))
                  setPolicyStatus('error')
                }
              }}
              className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply policy
            </button>

            {policyError ? (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {policyError}
              </div>
            ) : null}

            {policy ? (
              <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                <div className="text-xs text-gray-400 mb-1">Applied</div>
                <div className="text-sm text-white">
                  policy_id: <span className="font-mono">{policy.policy_id}</span>
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  per_tx: <span className="font-mono">{policy.limit_per_tx}</span> · total:{' '}
                  <span className="font-mono">{policy.limit_total}</span>
                </div>
              </div>
            ) : null}
          </div>
        </Card>

        <Card title="Step 3 — Issue virtual card" subtitle="Lithic card issuance (demo).">
          <div className="flex items-center justify-between gap-3">
            <StatusPill status={cardStatus} />
            {cardId ? <CopyButton value={cardId} /> : null}
          </div>

          <div className="mt-4 space-y-4">
            <button
              type="button"
              disabled={cardStatus === 'running' || !wallet?.wallet_id}
              onClick={async () => {
                setCardError('')
                setCardStatus('running')
                try {
                  const res = await demoApi.issueCard({ wallet_id: wallet.wallet_id, limit_per_tx: '100.00' })
                  setCard(res as DemoCard)
                  setCardStatus('done')
                } catch (error: unknown) {
                  setCardError(getErrorMessage(error, 'Card issue failed'))
                  setCardStatus('error')
                }
              }}
              className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Issue card
            </button>

            {!wallet?.wallet_id ? (
              <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg text-gray-400 text-sm">
                Create wallet first.
              </div>
            ) : null}

            {cardError ? (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {cardError}
              </div>
            ) : null}

            {card ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <div className="text-xs text-gray-400">card_id</div>
                  <div className="text-sm font-mono text-white break-all">{card.card_id}</div>
                </div>
                <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
                  <div className="text-xs text-gray-400">status</div>
                  <div className="text-sm text-white">{card.status || 'pending'}</div>
                </div>
              </div>
            ) : null}
          </div>
        </Card>
      </div>

      <Card title="Step 4 — Simulate purchase + enforcement" subtitle="Gambling merchant → blocked by policy → auto-freeze. Software merchant → approved.">
        <div className="flex items-center justify-between gap-3">
          <StatusPill status={purchaseStatus} />
          {purchaseResult?.transaction?.transaction_id ? <CopyButton value={purchaseResult.transaction.transaction_id} /> : null}
        </div>

        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div>
              <FieldLabel>Amount</FieldLabel>
              <TextInput value={purchaseAmount} onChange={(e) => setPurchaseAmount(e.target.value)} placeholder="25.00" />
            </div>
            <div className="lg:col-span-2">
              <FieldLabel>Merchant Category</FieldLabel>
              <div className="grid grid-cols-3 gap-2">
                {merchantPresets.map((m) => (
                  <button
                    key={m.mcc}
                    type="button"
                    onClick={() => setPurchaseMcc(m.mcc)}
                    className={clsx(
                      'px-3 py-2 border text-sm rounded-lg transition-colors',
                      purchaseMcc === m.mcc
                        ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                        : 'bg-dark-300 text-gray-300 border-dark-100 hover:bg-dark-200'
                    )}
                  >
                    {m.label}
                    <span className="block text-xs text-gray-500 mt-0.5">MCC {m.mcc}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div>
            <button
              type="button"
              disabled={purchaseStatus === 'running' || !card?.card_id}
              onClick={async () => {
                setPurchaseError('')
                setPurchaseStatus('running')
                try {
                  const res = await demoApi.simulatePurchase(card.card_id, {
                    amount: purchaseAmount,
                    merchant_name: selectedMerchant.name,
                    mcc_code: purchaseMcc,
                  })
                  setPurchaseResult(res as DemoPurchaseResult)
                  setPurchaseStatus('done')
                  // Auto-refresh transaction history
                  try {
                    const list = await demoApi.listCardTransactions(card.card_id, 50)
                    setTransactions(list as DemoTransaction[])
                    setTxStatus('done')
                  } catch {
                    // silent — user can still click Refresh manually
                  }
                } catch (error: unknown) {
                  setPurchaseError(getErrorMessage(error, 'Simulation failed'))
                  setPurchaseStatus('error')
                }
              }}
              className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Simulate purchase
            </button>
          </div>
        </div>


        {!card?.card_id ? (
          <div className="mt-4 p-3 bg-dark-200 border border-dark-100 rounded-lg text-gray-400 text-sm">
            Issue card first.
          </div>
        ) : null}

        {purchaseError ? (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {purchaseError}
          </div>
        ) : null}

        {purchaseResult ? (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
              <div className="text-xs text-gray-400 mb-1">Policy</div>
              <div className="flex items-center gap-2">
                {purchaseResult.policy?.allowed ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-emerald-300">Allowed</span>
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-300">Denied</span>
                  </>
                )}
              </div>
              <div className="text-xs text-gray-400 mt-2">reason</div>
              <div className="text-sm text-white font-mono break-all">{purchaseResult.policy?.reason || '-'}</div>
            </div>
            <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
              <div className="text-xs text-gray-400 mb-1">Transaction</div>
              <div className="text-sm text-white font-mono break-all">{purchaseResult.transaction?.transaction_id}</div>
              <div className="text-sm text-gray-300 mt-1">
                {purchaseResult.transaction?.amount} {purchaseResult.transaction?.currency}
              </div>
            </div>
            <div className="p-3 bg-dark-200 border border-dark-100 rounded-lg">
              <div className="text-xs text-gray-400 mb-1">Card</div>
              <div className="text-sm text-white">status: {purchaseResult.card?.status || '-'}</div>
              <div className="text-xs text-gray-400 mt-2">provider_card_id</div>
              <div className="text-sm text-white font-mono break-all">{purchaseResult.card?.provider_card_id || '-'}</div>
            </div>
          </div>
        ) : null}
      </Card>

      <Card title="Step 5 — Transaction history" subtitle="Simulated purchases appear here (latest first).">
        <div className="flex items-center justify-between gap-3">
          <StatusPill status={txStatus} />
          <button
            type="button"
            disabled={txStatus === 'running' || !card?.card_id}
            onClick={async () => {
              setTxError('')
              setTxStatus('running')
              try {
                const list = await demoApi.listCardTransactions(card.card_id, 50)
                setTransactions(list as DemoTransaction[])
                setTxStatus('done')
              } catch (error: unknown) {
                setTxError(getErrorMessage(error, 'Failed to load transactions'))
                setTxStatus('error')
              }
            }}
            className="px-4 py-2 bg-dark-200 border border-dark-100 rounded-lg text-gray-300 hover:text-white hover:bg-dark-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Refresh
          </button>
        </div>

        {txError ? (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
            {txError}
          </div>
        ) : null}

        <div className="mt-4 overflow-hidden rounded-lg border border-dark-100">
          <table className="w-full text-sm">
            <thead className="bg-dark-200">
              <tr className="text-left text-gray-400">
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Merchant</th>
                <th className="px-4 py-3 font-medium">MCC</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Txn</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {transactions.length === 0 ? (
                <tr>
                  <td className="px-4 py-4 text-gray-400" colSpan={5}>
                    No transactions yet. Run “Simulate purchase”.
                  </td>
                </tr>
              ) : (
                transactions.map((t) => (
                  <tr key={t.transaction_id} className="bg-dark-300/20">
                    <td className="px-4 py-3">
                      <span
                        className={clsx(
                          'text-xs px-2 py-1 rounded-full border',
                          t.status?.includes('declined')
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        )}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-white">{t.merchant_name || 'Unknown'}</td>
                    <td className="px-4 py-3 text-gray-300 font-mono">{t.merchant_category || '-'}</td>
                    <td className="px-4 py-3 text-gray-300">
                      {t.amount} {t.currency}
                    </td>
                    <td className="px-4 py-3 text-gray-300 font-mono break-all">{t.transaction_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
