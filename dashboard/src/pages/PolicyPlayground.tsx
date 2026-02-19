import { useState, useMemo, useCallback } from 'react'
import {
  FlaskConical,
  Sparkles,
  Play,
  Shuffle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronRight,
  ToggleLeft,
  ToggleRight,
  DollarSign,
  ShieldCheck,
  Target,
  Clock,
  Zap,
  Copy,
  Check,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import clsx from 'clsx'
import { demoApi } from '../api/client'

/* ─── Types ─── */

interface ParsedPolicy {
  per_tx_limit: number | null
  total_limit: number | null
  allowed_merchants: string[]
  blocked_categories: string[]
  approval_threshold: number | null
  time_window: string | null
  require_purpose: boolean
}

interface PolicyCheckResult {
  passed: boolean
  label: string
  detail: string
}

interface SimTransaction {
  id: string
  amount: number
  destination: string
  token: string
  purpose: string
  status: 'approved' | 'rejected' | 'approval_required'
  reason: string
  checks: PolicyCheckResult[]
}

interface SpendDataPoint {
  day: string
  cumulative: number
  daily: number
}

/* ─── Constants ─── */

const EXAMPLE_POLICIES = [
  'Max $50 per transaction',
  'Only OpenAI and Anthropic',
  'No gambling, approval above $100',
  'Max $500/day, only SaaS and cloud providers',
  'Block crypto exchanges, require purpose for all',
  'Max $25/tx, $200 total, only API services',
]

const TOKEN_OPTIONS = ['USDC', 'USDT', 'EURC', 'PYUSD']

const MOCK_DESTINATIONS = [
  'OpenAI', 'Anthropic', 'AWS', 'Google Cloud', 'Vercel',
  'Stripe', 'Twilio', 'GitHub', 'Cloudflare', 'DataDog',
  'PokerStars', 'DraftKings', 'Binance', 'Coinbase',
  'Shopify', 'Heroku', 'DigitalOcean', 'Netlify',
]

const MOCK_PURPOSES = [
  'API inference call', 'Cloud compute', 'Data storage',
  'Monitoring service', 'CI/CD pipeline', 'Domain renewal',
  'Model fine-tuning', 'Database hosting', 'CDN bandwidth',
  '', // some with no purpose
]

const SPEND_CATEGORIES = [
  { name: 'AI/ML APIs', value: 340, color: '#22c55e' },
  { name: 'Cloud Infra', value: 220, color: '#3b82f6' },
  { name: 'SaaS Tools', value: 150, color: '#f59e0b' },
  { name: 'Data Services', value: 90, color: '#8b5cf6' },
  { name: 'Other', value: 45, color: '#6b7280' },
]

const CHART_TOOLTIP_STYLE = {
  background: '#1f1e1c',
  border: '1px solid #2f2e2c',
  borderRadius: '0px',
  fontSize: '12px',
}

/* ─── Helpers ─── */

function parseNaturalLanguagePolicy(text: string): ParsedPolicy {
  const lower = text.toLowerCase()
  const policy: ParsedPolicy = {
    per_tx_limit: null,
    total_limit: null,
    allowed_merchants: [],
    blocked_categories: [],
    approval_threshold: null,
    time_window: null,
    require_purpose: false,
  }

  // Parse per-transaction limit
  const perTxMatch = lower.match(/max\s*\$?(\d+(?:\.\d+)?)\s*(?:per\s*(?:tx|transaction)|\/tx)/)
  if (perTxMatch) policy.per_tx_limit = parseFloat(perTxMatch[1])

  // Parse total limit
  const totalMatch = lower.match(/\$?(\d+(?:\.\d+)?)\s*total/)
  if (totalMatch) policy.total_limit = parseFloat(totalMatch[1])

  // Parse daily limit as total
  const dailyMatch = lower.match(/max\s*\$?(\d+(?:\.\d+)?)\s*(?:\/day|per\s*day|daily)/)
  if (dailyMatch) {
    policy.total_limit = parseFloat(dailyMatch[1])
    policy.time_window = '24h'
  }

  // Fallback: generic max without per-tx qualifier
  if (!policy.per_tx_limit && !policy.total_limit) {
    const genericMax = lower.match(/max\s*\$?(\d+(?:\.\d+)?)/)
    if (genericMax) policy.per_tx_limit = parseFloat(genericMax[1])
  }

  // Parse allowed merchants
  const onlyMatch = lower.match(/only\s+(.+?)(?:\.|,\s*(?:max|no|block|require|approval)|$)/)
  if (onlyMatch) {
    policy.allowed_merchants = onlyMatch[1]
      .split(/\s+and\s+|,\s*/)
      .map(s => s.trim())
      .filter(Boolean)
  }

  // Parse blocked categories
  const blockPatterns = [
    /no\s+(.+?)(?:\.|,\s*(?:max|only|require|approval)|$)/,
    /block\s+(.+?)(?:\.|,\s*(?:max|only|require|no)|$)/,
  ]
  for (const pattern of blockPatterns) {
    const match = lower.match(pattern)
    if (match) {
      policy.blocked_categories = match[1]
        .split(/\s+and\s+|,\s*/)
        .map(s => s.trim())
        .filter(Boolean)
      break
    }
  }

  // Parse approval threshold
  const approvalMatch = lower.match(/approval\s+(?:above|over|for\s+amounts?\s+(?:above|over))\s*\$?(\d+(?:\.\d+)?)/)
  if (approvalMatch) policy.approval_threshold = parseFloat(approvalMatch[1])

  // Parse require purpose
  if (lower.includes('require purpose') || lower.includes('require reason')) {
    policy.require_purpose = true
  }

  return policy
}

function checkTransaction(
  tx: { amount: number; destination: string; token: string; purpose: string },
  policy: ParsedPolicy,
  totalSpent: number,
): { status: SimTransaction['status']; reason: string; checks: PolicyCheckResult[] } {
  const checks: PolicyCheckResult[] = []
  let blocked = false
  let needsApproval = false

  // Per-tx limit
  if (policy.per_tx_limit !== null) {
    const passed = tx.amount <= policy.per_tx_limit
    checks.push({
      passed,
      label: 'Per-transaction limit',
      detail: passed
        ? `$${tx.amount.toFixed(2)} <= $${policy.per_tx_limit.toFixed(2)}`
        : `$${tx.amount.toFixed(2)} exceeds $${policy.per_tx_limit.toFixed(2)} limit`,
    })
    if (!passed) blocked = true
  }

  // Total limit
  if (policy.total_limit !== null) {
    const newTotal = totalSpent + tx.amount
    const passed = newTotal <= policy.total_limit
    checks.push({
      passed,
      label: `Total spend limit${policy.time_window ? ` (${policy.time_window})` : ''}`,
      detail: passed
        ? `$${newTotal.toFixed(2)} <= $${policy.total_limit.toFixed(2)}`
        : `$${newTotal.toFixed(2)} would exceed $${policy.total_limit.toFixed(2)} budget`,
    })
    if (!passed) blocked = true
  }

  // Allowed merchants
  if (policy.allowed_merchants.length > 0) {
    const destLower = tx.destination.toLowerCase()
    const passed = policy.allowed_merchants.some(m => destLower.includes(m.toLowerCase()))
    checks.push({
      passed,
      label: 'Allowed destinations',
      detail: passed
        ? `"${tx.destination}" is an allowed destination`
        : `"${tx.destination}" not in allowed list: ${policy.allowed_merchants.join(', ')}`,
    })
    if (!passed) blocked = true
  }

  // Blocked categories
  if (policy.blocked_categories.length > 0) {
    const destLower = tx.destination.toLowerCase()
    const isBlocked = policy.blocked_categories.some(cat => destLower.includes(cat.toLowerCase()))
    checks.push({
      passed: !isBlocked,
      label: 'Blocked categories',
      detail: !isBlocked
        ? `"${tx.destination}" not in blocked categories`
        : `"${tx.destination}" matches blocked category`,
    })
    if (isBlocked) blocked = true
  }

  // Purpose requirement
  if (policy.require_purpose) {
    const passed = tx.purpose.trim().length > 0
    checks.push({
      passed,
      label: 'Purpose required',
      detail: passed ? `Purpose provided: "${tx.purpose}"` : 'No purpose provided',
    })
    if (!passed) blocked = true
  }

  // Approval threshold (only if not already blocked)
  if (!blocked && policy.approval_threshold !== null && tx.amount > policy.approval_threshold) {
    needsApproval = true
    checks.push({
      passed: true,
      label: 'Approval threshold',
      detail: `$${tx.amount.toFixed(2)} > $${policy.approval_threshold.toFixed(2)} requires human approval`,
    })
  }

  if (blocked) {
    const failedCheck = checks.find(c => !c.passed)
    return { status: 'rejected', reason: failedCheck?.detail || 'Policy violation', checks }
  }
  if (needsApproval) {
    return { status: 'approval_required', reason: `Amount exceeds $${policy.approval_threshold} approval threshold`, checks }
  }
  return { status: 'approved', reason: 'All policy checks passed', checks }
}

function generateRandomTransactions(policy: ParsedPolicy, count: number): SimTransaction[] {
  const txs: SimTransaction[] = []
  let runningTotal = 0

  for (let i = 0; i < count; i++) {
    const maxRange = policy.per_tx_limit ? policy.per_tx_limit * 2.5 : 200
    const amount = parseFloat((Math.random() * maxRange + 1).toFixed(2))
    const destination = MOCK_DESTINATIONS[Math.floor(Math.random() * MOCK_DESTINATIONS.length)]
    const token = TOKEN_OPTIONS[Math.floor(Math.random() * TOKEN_OPTIONS.length)]
    const purpose = MOCK_PURPOSES[Math.floor(Math.random() * MOCK_PURPOSES.length)]

    const result = checkTransaction({ amount, destination, token, purpose }, policy, runningTotal)
    if (result.status === 'approved') runningTotal += amount

    txs.push({
      id: `sim_${Math.random().toString(36).substring(2, 8)}`,
      amount,
      destination,
      token,
      purpose,
      ...result,
    })
  }

  return txs
}

function generateSpendData(policy: ParsedPolicy): SpendDataPoint[] {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const limit = policy.total_limit || policy.per_tx_limit ? (policy.per_tx_limit || 50) * 10 : 500
  let cumulative = 0

  return days.map(day => {
    const daily = parseFloat((Math.random() * (limit / 5) + 10).toFixed(2))
    cumulative += daily
    return { day, cumulative: parseFloat(cumulative.toFixed(2)), daily: parseFloat(daily.toFixed(2)) }
  })
}

/* ─── Main Component ─── */

export default function PolicyPlaygroundPage() {
  // Mode toggle
  const [liveMode, setLiveMode] = useState(false)

  // Section 1: Policy Editor
  const [policyText, setPolicyText] = useState('')
  const [parsedPolicy, setParsedPolicy] = useState<ParsedPolicy | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [liveParseResult, setLiveParseResult] = useState<Record<string, unknown> | null>(null)
  const [liveParseError, setLiveParseError] = useState<string | null>(null)

  // Section 2: Transaction Simulator
  const [simAmount, setSimAmount] = useState('25.00')
  const [simDestination, setSimDestination] = useState('OpenAI')
  const [simToken, setSimToken] = useState('USDC')
  const [simPurpose, setSimPurpose] = useState('API inference call')
  const [simResult, setSimResult] = useState<{
    status: SimTransaction['status']
    reason: string
    checks: PolicyCheckResult[]
  } | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [liveCheckResult, setLiveCheckResult] = useState<{ allowed: boolean; reason: string } | null>(null)

  // Section 3: Batch Simulator
  const [batchTxs, setBatchTxs] = useState<SimTransaction[]>([])

  // Section 4: Spend Visualization
  const spendData = useMemo(() => parsedPolicy ? generateSpendData(parsedPolicy) : [], [parsedPolicy])

  const totalBudget = parsedPolicy?.total_limit || (parsedPolicy?.per_tx_limit ? parsedPolicy.per_tx_limit * 10 : 500)
  const usedBudget = spendData.length > 0 ? spendData[spendData.length - 1].cumulative : 0
  const budgetPercent = Math.min(100, (usedBudget / totalBudget) * 100)

  // Handlers
  const handleParsePolicy = useCallback(async () => {
    if (!policyText.trim()) return
    setIsParsing(true)
    setLiveParseResult(null)
    setLiveParseError(null)

    if (liveMode) {
      try {
        const result = await demoApi.applyPolicy({
          agent_id: 'playground_agent',
          natural_language: policyText,
        })
        setLiveParseResult(result)
        // Also parse locally for simulator functionality
        const local = parseNaturalLanguagePolicy(policyText)
        setParsedPolicy(local)
      } catch (err) {
        setLiveParseError(err instanceof Error ? err.message : 'API request failed')
        // Fall back to local parse
        const local = parseNaturalLanguagePolicy(policyText)
        setParsedPolicy(local)
      }
    } else {
      // Simulate a brief delay for UX
      await new Promise(r => setTimeout(r, 400))
      const local = parseNaturalLanguagePolicy(policyText)
      setParsedPolicy(local)
    }

    setIsParsing(false)
    setSimResult(null)
    setBatchTxs([])
  }, [policyText, liveMode])

  const handleCheckTransaction = useCallback(async () => {
    if (!parsedPolicy) return
    setIsChecking(true)
    setLiveCheckResult(null)

    if (liveMode) {
      try {
        const result = await demoApi.checkPolicy({
          agent_id: 'playground_agent',
          amount: simAmount,
          currency: simToken,
          merchant_id: simDestination,
        })
        setLiveCheckResult(result)
      } catch {
        // Fall through to local check
      }
    }

    // Always run local check for the detailed UI
    await new Promise(r => setTimeout(r, 300))
    const result = checkTransaction(
      {
        amount: parseFloat(simAmount) || 0,
        destination: simDestination,
        token: simToken,
        purpose: simPurpose,
      },
      parsedPolicy,
      usedBudget,
    )
    setSimResult(result)
    setIsChecking(false)
  }, [parsedPolicy, simAmount, simDestination, simToken, simPurpose, usedBudget, liveMode])

  const handleGenerateBatch = useCallback(() => {
    if (!parsedPolicy) return
    const txs = generateRandomTransactions(parsedPolicy, 10)
    setBatchTxs(txs)
  }, [parsedPolicy])

  const batchStats = useMemo(() => {
    const approved = batchTxs.filter(t => t.status === 'approved').length
    const rejected = batchTxs.filter(t => t.status === 'rejected').length
    const needsApproval = batchTxs.filter(t => t.status === 'approval_required').length
    return { approved, rejected, needsApproval }
  }, [batchTxs])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Policy Lab</h1>
          <p className="text-gray-400 mt-1">
            Design, test, and visualize spending policies for your AI agents
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setLiveMode(!liveMode)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 text-sm font-medium',
              liveMode
                ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                : 'bg-dark-200 text-gray-400 border border-dark-100 hover:border-dark-100/80'
            )}
          >
            {liveMode ? (
              <ToggleRight className="w-5 h-5" />
            ) : (
              <ToggleLeft className="w-5 h-5" />
            )}
            {liveMode ? 'Live Mode' : 'Simulation'}
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <FlaskConical className="w-4 h-4 text-sardis-400" />
            <span className="text-sm text-gray-400">Playground</span>
          </div>
        </div>
      </div>

      {/* Section 1: Natural Language Policy Editor */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-sardis-400" />
          <h2 className="text-lg font-semibold text-white">Natural Language Policy</h2>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Describe your spending policy in plain English. Click an example to get started.
        </p>

        {/* Example chips */}
        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLE_POLICIES.map((example) => (
            <button
              key={example}
              onClick={() => setPolicyText(example)}
              className={clsx(
                'px-3 py-1.5 text-xs rounded-lg transition-all duration-200 border',
                policyText === example
                  ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                  : 'bg-dark-200 text-gray-400 border-dark-100 hover:text-white hover:border-dark-100/80'
              )}
            >
              {example}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={policyText}
          onChange={(e) => setPolicyText(e.target.value)}
          placeholder="e.g. Max $50 per transaction, only allow OpenAI and Anthropic, require approval above $100..."
          rows={3}
          className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 resize-none"
        />

        <div className="flex items-center gap-4 mt-4">
          <button
            onClick={handleParsePolicy}
            disabled={!policyText.trim() || isParsing}
            className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 font-semibold rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isParsing ? (
              <div className="w-4 h-4 border-2 border-dark-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            Parse Policy
          </button>
          {liveMode && (
            <span className="text-xs text-sardis-400/60">Will call /policies/apply API</span>
          )}
        </div>

        {/* Parsed Policy Display */}
        {parsedPolicy && (
          <div className="mt-6 pt-6 border-t border-dark-100">
            <h3 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wider">Parsed Policy Structure</h3>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <PolicyField
                label="Per-TX Limit"
                value={parsedPolicy.per_tx_limit !== null ? `$${parsedPolicy.per_tx_limit.toFixed(2)}` : 'No limit'}
                active={parsedPolicy.per_tx_limit !== null}
                icon={<DollarSign className="w-4 h-4" />}
              />
              <PolicyField
                label={parsedPolicy.time_window ? `Total (${parsedPolicy.time_window})` : 'Total Limit'}
                value={parsedPolicy.total_limit !== null ? `$${parsedPolicy.total_limit.toFixed(2)}` : 'No limit'}
                active={parsedPolicy.total_limit !== null}
                icon={<Target className="w-4 h-4" />}
              />
              <PolicyField
                label="Approval Above"
                value={parsedPolicy.approval_threshold !== null ? `$${parsedPolicy.approval_threshold.toFixed(2)}` : 'None'}
                active={parsedPolicy.approval_threshold !== null}
                icon={<ShieldCheck className="w-4 h-4" />}
              />
              <PolicyField
                label="Purpose Required"
                value={parsedPolicy.require_purpose ? 'Yes' : 'No'}
                active={parsedPolicy.require_purpose}
                icon={<Clock className="w-4 h-4" />}
              />
            </div>

            {parsedPolicy.allowed_merchants.length > 0 && (
              <div className="mt-4">
                <span className="text-xs text-gray-500 uppercase tracking-wider">Allowed destinations</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {parsedPolicy.allowed_merchants.map(m => (
                    <span key={m} className="px-2.5 py-1 text-xs bg-sardis-500/10 text-sardis-400 rounded-lg border border-sardis-500/20">
                      {m}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {parsedPolicy.blocked_categories.length > 0 && (
              <div className="mt-4">
                <span className="text-xs text-gray-500 uppercase tracking-wider">Blocked categories</span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {parsedPolicy.blocked_categories.map(c => (
                    <span key={c} className="px-2.5 py-1 text-xs bg-red-500/10 text-red-400 rounded-lg border border-red-500/20">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Live API result */}
            {liveParseResult && (
              <div className="mt-4 p-3 bg-dark-300 rounded-lg border border-dark-100">
                <span className="text-xs text-sardis-400 font-medium">API Response</span>
                <pre className="text-xs text-gray-400 mt-2 overflow-x-auto">
                  {JSON.stringify(liveParseResult, null, 2)}
                </pre>
              </div>
            )}
            {liveParseError && (
              <div className="mt-4 p-3 bg-red-500/5 rounded-lg border border-red-500/20">
                <span className="text-xs text-red-400">{liveParseError} (fell back to local parse)</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 2: Transaction Simulator */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Play className="w-5 h-5 text-sardis-400" />
          <h2 className="text-lg font-semibold text-white">Transaction Simulator</h2>
        </div>

        {!parsedPolicy ? (
          <div className="text-center py-8">
            <ShieldCheck className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">Parse a policy first to simulate transactions</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Input side */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Amount (USD)</label>
                  <input
                    type="text"
                    value={simAmount}
                    onChange={(e) => setSimAmount(e.target.value)}
                    className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Token</label>
                  <select
                    value={simToken}
                    onChange={(e) => setSimToken(e.target.value)}
                    className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 rounded-lg text-white appearance-none focus:outline-none focus:border-sardis-500/50"
                  >
                    {TOKEN_OPTIONS.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Destination</label>
                <input
                  type="text"
                  value={simDestination}
                  onChange={(e) => setSimDestination(e.target.value)}
                  className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Purpose</label>
                <input
                  type="text"
                  value={simPurpose}
                  onChange={(e) => setSimPurpose(e.target.value)}
                  placeholder="Optional description..."
                  className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                />
              </div>
              <button
                onClick={handleCheckTransaction}
                disabled={isChecking}
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 font-semibold rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
              >
                {isChecking ? (
                  <div className="w-4 h-4 border-2 border-dark-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                Check Policy
              </button>
            </div>

            {/* Result side */}
            <div>
              {simResult ? (
                <div className="space-y-4">
                  {/* Big status indicator */}
                  <div className={clsx(
                    'rounded-xl p-5 border text-center',
                    simResult.status === 'approved' && 'bg-sardis-500/5 border-sardis-500/30',
                    simResult.status === 'rejected' && 'bg-red-500/5 border-red-500/30',
                    simResult.status === 'approval_required' && 'bg-yellow-500/5 border-yellow-500/30',
                  )}>
                    <div className="flex justify-center mb-3">
                      {simResult.status === 'approved' && <CheckCircle2 className="w-12 h-12 text-sardis-400" />}
                      {simResult.status === 'rejected' && <XCircle className="w-12 h-12 text-red-400" />}
                      {simResult.status === 'approval_required' && <AlertTriangle className="w-12 h-12 text-yellow-400" />}
                    </div>
                    <p className={clsx(
                      'text-lg font-semibold',
                      simResult.status === 'approved' && 'text-sardis-400',
                      simResult.status === 'rejected' && 'text-red-400',
                      simResult.status === 'approval_required' && 'text-yellow-400',
                    )}>
                      {simResult.status === 'approved' && 'Transaction Approved'}
                      {simResult.status === 'rejected' && 'Transaction Rejected'}
                      {simResult.status === 'approval_required' && 'Approval Required'}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">{simResult.reason}</p>
                  </div>

                  {/* Individual checks */}
                  <div className="space-y-2">
                    {simResult.checks.map((check, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-dark-300/50 rounded-lg">
                        {check.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-sardis-400 mt-0.5 shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                        )}
                        <div>
                          <p className="text-sm text-white">{check.label}</p>
                          <p className="text-xs text-gray-500">{check.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Live API result */}
                  {liveCheckResult && (
                    <div className="p-3 bg-dark-300 rounded-lg border border-dark-100">
                      <span className="text-xs text-sardis-400 font-medium">API Response</span>
                      <div className="flex items-center gap-2 mt-2">
                        <div className={clsx(
                          'w-2 h-2 rounded-full',
                          liveCheckResult.allowed ? 'bg-sardis-500' : 'bg-red-500'
                        )} />
                        <span className="text-xs text-gray-400">{liveCheckResult.reason}</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-600">
                  <div className="text-center">
                    <ChevronRight className="w-10 h-10 mx-auto mb-2" />
                    <p className="text-sm">Configure a transaction and check it against your policy</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Batch Simulator */}
      {parsedPolicy && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Shuffle className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Batch Simulator</h2>
            </div>
            <button
              onClick={handleGenerateBatch}
              className="flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors text-sm font-medium"
            >
              <Shuffle className="w-4 h-4" />
              Generate 10 Random Transactions
            </button>
          </div>

          {batchTxs.length === 0 ? (
            <div className="text-center py-8">
              <Shuffle className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">Generate random transactions to test your policy at scale</p>
            </div>
          ) : (
            <>
              {/* Summary stats */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-sardis-500/5 border border-sardis-500/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-sardis-400 mono-numbers">{batchStats.approved}</p>
                  <p className="text-xs text-gray-500 mt-1">Approved</p>
                </div>
                <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-red-400 mono-numbers">{batchStats.rejected}</p>
                  <p className="text-xs text-gray-500 mt-1">Rejected</p>
                </div>
                <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-yellow-400 mono-numbers">{batchStats.needsApproval}</p>
                  <p className="text-xs text-gray-500 mt-1">Need Approval</p>
                </div>
              </div>

              {/* Batch table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 uppercase">
                      <th className="pb-3 font-medium">Status</th>
                      <th className="pb-3 font-medium">Amount</th>
                      <th className="pb-3 font-medium">Destination</th>
                      <th className="pb-3 font-medium">Token</th>
                      <th className="pb-3 font-medium">Purpose</th>
                      <th className="pb-3 font-medium">Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-100">
                    {batchTxs.map((tx) => (
                      <tr key={tx.id} className="hover:bg-dark-200/50 transition-colors">
                        <td className="py-3">
                          <span className={clsx(
                            'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
                            tx.status === 'approved' && 'bg-sardis-500/10 text-sardis-400',
                            tx.status === 'rejected' && 'bg-red-500/10 text-red-400',
                            tx.status === 'approval_required' && 'bg-yellow-500/10 text-yellow-400',
                          )}>
                            <div className={clsx(
                              'w-1.5 h-1.5 rounded-full',
                              tx.status === 'approved' && 'bg-sardis-500',
                              tx.status === 'rejected' && 'bg-red-500',
                              tx.status === 'approval_required' && 'bg-yellow-500',
                            )} />
                            {tx.status === 'approval_required' ? 'approval' : tx.status}
                          </span>
                        </td>
                        <td className="py-3">
                          <span className="text-sm text-white font-mono mono-numbers">${tx.amount.toFixed(2)}</span>
                        </td>
                        <td className="py-3">
                          <span className="text-sm text-gray-300">{tx.destination}</span>
                        </td>
                        <td className="py-3">
                          <span className="text-xs px-2 py-0.5 bg-dark-200 text-gray-400 rounded">{tx.token}</span>
                        </td>
                        <td className="py-3">
                          <span className="text-sm text-gray-500 truncate max-w-[120px] block">
                            {tx.purpose || '--'}
                          </span>
                        </td>
                        <td className="py-3">
                          <span className="text-xs text-gray-500 truncate max-w-[200px] block">{tx.reason}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Section 4: Spend Visualization */}
      {parsedPolicy && spendData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cumulative Spend Chart */}
          <div className="lg:col-span-2 card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Cumulative Spend</h2>
                <p className="text-sm text-gray-400">Simulated weekly spend trajectory</p>
              </div>
              {parsedPolicy.total_limit && (
                <div className="text-right">
                  <p className="text-xs text-gray-500">Budget</p>
                  <p className="text-sm text-white font-mono mono-numbers">${parsedPolicy.total_limit.toFixed(2)}</p>
                </div>
              )}
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={spendData}>
                  <defs>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" />
                  <XAxis dataKey="day" stroke="#444341" fontSize={12} tickLine={false} />
                  <YAxis
                    stroke="#444341"
                    fontSize={12}
                    tickLine={false}
                    tickFormatter={(value) => `$${value}`}
                  />
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} labelStyle={{ color: '#94a3b8' }} />
                  <Area
                    type="monotone"
                    dataKey="cumulative"
                    stroke="#22c55e"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorSpend)"
                    name="Cumulative Spend"
                  />
                  {parsedPolicy.total_limit && (
                    <Area
                      type="monotone"
                      dataKey={() => parsedPolicy.total_limit}
                      stroke="#ef4444"
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      fillOpacity={0}
                      name="Budget Limit"
                    />
                  )}
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Budget bar */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">Budget Utilization</span>
                <span className="text-sm text-white font-mono mono-numbers">
                  ${usedBudget.toFixed(2)} / ${totalBudget.toFixed(2)}
                </span>
              </div>
              <div className="h-3 bg-dark-300 rounded-full overflow-hidden">
                <div
                  className={clsx(
                    'h-full rounded-full transition-all duration-500',
                    budgetPercent < 60 && 'bg-sardis-500',
                    budgetPercent >= 60 && budgetPercent < 85 && 'bg-yellow-500',
                    budgetPercent >= 85 && 'bg-red-500',
                  )}
                  style={{ width: `${budgetPercent}%` }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-gray-600">0%</span>
                <span className={clsx(
                  'text-xs font-medium',
                  budgetPercent < 60 && 'text-sardis-400',
                  budgetPercent >= 60 && budgetPercent < 85 && 'text-yellow-400',
                  budgetPercent >= 85 && 'text-red-400',
                )}>
                  {budgetPercent.toFixed(1)}%
                </span>
                <span className="text-xs text-gray-600">100%</span>
              </div>
            </div>
          </div>

          {/* Spend by Category Pie */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-white mb-2">Spend by Category</h3>
            <p className="text-sm text-gray-400 mb-4">Simulated distribution</p>

            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={SPEND_CATEGORIES}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {SPEND_CATEGORIES.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2 mt-4">
              {SPEND_CATEGORIES.map((cat) => (
                <div key={cat.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cat.color }} />
                    <span className="text-sm text-gray-400">{cat.name}</span>
                  </div>
                  <span className="text-sm text-white font-mono mono-numbers">${cat.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* JSON Export */}
      {parsedPolicy && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Policy JSON</h3>
            <CopyButton text={JSON.stringify(parsedPolicy, null, 2)} />
          </div>
          <pre className="text-xs text-gray-400 bg-dark-300 rounded-lg p-4 overflow-x-auto border border-dark-100">
            {JSON.stringify(parsedPolicy, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}


/* ─── Sub-components ─── */

function PolicyField({
  label,
  value,
  active,
  icon,
}: {
  label: string
  value: string
  active: boolean
  icon: React.ReactNode
}) {
  return (
    <div className={clsx(
      'rounded-lg p-4 border transition-all',
      active
        ? 'bg-sardis-500/5 border-sardis-500/20'
        : 'bg-dark-300/50 border-dark-100'
    )}>
      <div className="flex items-center gap-2 mb-2">
        <span className={clsx(active ? 'text-sardis-400' : 'text-gray-600')}>{icon}</span>
        <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
      <p className={clsx(
        'text-lg font-semibold font-mono',
        active ? 'text-white' : 'text-gray-600'
      )}>
        {value}
      </p>
    </div>
  )
}


function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-white transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-sardis-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}
