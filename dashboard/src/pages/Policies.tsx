import { useState } from 'react'
import {
  Shield,
  Sparkles,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  DollarSign,
  Tag,
  Clock,
  ShieldCheck,
  Eye,
  Send,
  User,
  BarChart2,
  Search,
} from 'lucide-react'
import clsx from 'clsx'
import {
  useAgents,
  usePolicy,
  useParsePolicy,
  usePreviewPolicy,
  useApplyPolicy,
  useCheckPolicy,
} from '../hooks/useApi'

/* ─── Types ─── */

interface Agent {
  agent_id?: string
  id?: string
  name: string
  is_active?: boolean
}

interface ParsedPolicyResult {
  spending_limits?: {
    per_tx?: number | null
    daily?: number | null
    weekly?: number | null
    monthly?: number | null
    total?: number | null
  }
  category_restrictions?: {
    blocked?: string[]
    allowed?: string[]
  }
  time_restrictions?: {
    window?: string
    allowed_hours?: string
  }
  approval_threshold?: number | null
  warnings?: string[]
  [key: string]: unknown
}

interface PreviewResult {
  confirmation_message?: string
  warnings?: string[]
  parsed?: ParsedPolicyResult
  [key: string]: unknown
}

interface CheckResult {
  allowed: boolean
  reason: string
}

interface CurrentPolicy {
  trust_level?: string
  limit_per_tx?: number | string | null
  limit_total?: number | string | null
  daily_limit?: number | string | null
  weekly_limit?: number | string | null
  monthly_limit?: number | string | null
  blocked_merchant_categories?: string[]
  merchant_rules_count?: number
  approval_threshold?: number | string | null
}

/* ─── Constants ─── */

const EXAMPLE_CHIPS = [
  'Max $50 per transaction',
  'Only allow OpenAI and Anthropic',
  'No gambling, approval above $100',
  'Max $500/day, only SaaS and cloud',
]

/* ─── Helpers ─── */

function agentId(agent: Agent): string {
  return agent.agent_id ?? agent.id ?? ''
}

function formatCurrency(val: number | string | null | undefined): string {
  if (val == null) return '—'
  const num = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(num)) return '—'
  return `$${num.toFixed(2)}`
}

/* ─── Sub-components ─── */

function WarningBox({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null
  return (
    <div className="mt-4 p-4 bg-yellow-500/10 border border-yellow-500/30">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
        <div className="space-y-1">
          {warnings.map((w, i) => (
            <p key={i} className="text-sm text-yellow-300">
              {w}
            </p>
          ))}
        </div>
      </div>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs text-gray-500 uppercase tracking-wider font-medium mb-2">
      {children}
    </p>
  )
}

function PolicySummary({ policy }: { policy: CurrentPolicy }) {
  const categories = policy.blocked_merchant_categories ?? []

  return (
    <div className="p-4 bg-dark-300 border border-dark-100 space-y-3">
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Trust Level</p>
          <p className="text-white font-medium capitalize">
            {policy.trust_level ?? '—'}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Approval Above</p>
          <p className="text-white font-medium mono-numbers">
            {formatCurrency(policy.approval_threshold)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Per-TX Limit</p>
          <p className="text-white font-medium mono-numbers">
            {formatCurrency(policy.limit_per_tx)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Daily Limit</p>
          <p className="text-white font-medium mono-numbers">
            {formatCurrency(policy.daily_limit)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Weekly Limit</p>
          <p className="text-white font-medium mono-numbers">
            {formatCurrency(policy.weekly_limit)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-0.5">Monthly Limit</p>
          <p className="text-white font-medium mono-numbers">
            {formatCurrency(policy.monthly_limit)}
          </p>
        </div>
      </div>

      {categories.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-2">Blocked Categories</p>
          <div className="flex flex-wrap gap-1.5">
            {categories.map((cat) => (
              <span
                key={cat}
                className="px-2 py-0.5 text-xs bg-red-500/10 text-red-400 border border-red-500/20"
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}

      {policy.merchant_rules_count != null && (
        <p className="text-xs text-gray-500">
          {policy.merchant_rules_count} merchant rule
          {policy.merchant_rules_count !== 1 ? 's' : ''} configured
        </p>
      )}
    </div>
  )
}

function ParsedResult({ result }: { result: ParsedPolicyResult }) {
  const limits = result.spending_limits ?? {}
  const restrictions = result.category_restrictions ?? {}
  const time = result.time_restrictions ?? {}

  return (
    <div className="mt-4 space-y-4">
      <SectionLabel>Parsed Structure</SectionLabel>

      {/* Spending limits */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: 'Per TX', value: limits.per_tx },
          { label: 'Daily', value: limits.daily },
          { label: 'Weekly', value: limits.weekly },
          { label: 'Monthly', value: limits.monthly },
          { label: 'Total', value: limits.total },
        ]
          .filter(({ value }) => value != null)
          .map(({ label, value }) => (
            <div
              key={label}
              className="p-3 bg-sardis-500/5 border border-sardis-500/20"
            >
              <div className="flex items-center gap-1.5 mb-1">
                <DollarSign className="w-3 h-3 text-sardis-400" />
                <p className="text-xs text-gray-500 uppercase tracking-wider">
                  {label}
                </p>
              </div>
              <p className="text-lg font-semibold text-white mono-numbers">
                {formatCurrency(value)}
              </p>
            </div>
          ))}
      </div>

      {/* Blocked categories */}
      {restrictions.blocked && restrictions.blocked.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Tag className="w-3.5 h-3.5 text-red-400" />
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              Blocked Categories
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {restrictions.blocked.map((cat) => (
              <span
                key={cat}
                className="px-2.5 py-1 text-xs bg-red-500/10 text-red-400 border border-red-500/20"
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Allowed categories */}
      {restrictions.allowed && restrictions.allowed.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Tag className="w-3.5 h-3.5 text-sardis-400" />
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              Allowed Only
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {restrictions.allowed.map((cat) => (
              <span
                key={cat}
                className="px-2.5 py-1 text-xs bg-sardis-500/10 text-sardis-400 border border-sardis-500/20"
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Time restrictions */}
      {(time.window || time.allowed_hours) && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Clock className="w-4 h-4 text-sardis-400" />
          {time.window && <span>Window: {time.window}</span>}
          {time.allowed_hours && <span>Hours: {time.allowed_hours}</span>}
        </div>
      )}

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <WarningBox warnings={result.warnings} />
      )}
    </div>
  )
}

/* ─── Main Component ─── */

export default function PoliciesPage() {
  const { data: agentsRaw = [], isLoading: agentsLoading } = useAgents()

  const agents: Agent[] = Array.isArray(agentsRaw) ? agentsRaw : []

  // Policy editor state
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [policyText, setPolicyText] = useState('')
  const [parsedResult, setParsedResult] = useState<ParsedPolicyResult | null>(null)
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null)
  const [applySuccess, setApplySuccess] = useState(false)
  const [confirmApply, setConfirmApply] = useState(false)

  // Policy tester state
  const [testAmount, setTestAmount] = useState('')
  const [testMerchantId, setTestMerchantId] = useState('')
  const [testMccCode, setTestMccCode] = useState('')
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null)

  // Hooks
  const { data: currentPolicy, isLoading: policyLoading } =
    usePolicy(selectedAgentId)
  const parseMutation = useParsePolicy()
  const previewMutation = usePreviewPolicy()
  const applyMutation = useApplyPolicy()
  const checkMutation = useCheckPolicy()

  // Agents that have any policy info (for the bottom summary)
  const agentsWithPolicies = agents.filter((a) => agentId(a))

  /* ─── Handlers ─── */

  function handleChipClick(chip: string) {
    setPolicyText(chip)
    setParsedResult(null)
    setPreviewResult(null)
    setApplySuccess(false)
    setConfirmApply(false)
  }

  async function handleParse() {
    if (!policyText.trim()) return
    setParsedResult(null)
    setPreviewResult(null)
    setApplySuccess(false)
    setConfirmApply(false)
    const result = await parseMutation.mutateAsync(policyText)
    setParsedResult(result as ParsedPolicyResult)
  }

  async function handlePreview() {
    if (!selectedAgentId || !policyText.trim()) return
    setPreviewResult(null)
    setApplySuccess(false)
    setConfirmApply(false)
    const result = await previewMutation.mutateAsync({
      agentId: selectedAgentId,
      naturalLanguage: policyText,
    })
    setPreviewResult(result as PreviewResult)
  }

  async function handleApply() {
    if (!selectedAgentId || !policyText.trim()) return
    await applyMutation.mutateAsync({
      agentId: selectedAgentId,
      naturalLanguage: policyText,
    })
    setApplySuccess(true)
    setConfirmApply(false)
    setPolicyText('')
    setParsedResult(null)
    setPreviewResult(null)
  }

  async function handleCheck() {
    if (!selectedAgentId || !testAmount) return
    setCheckResult(null)
    const result = await checkMutation.mutateAsync({
      agent_id: selectedAgentId,
      amount: testAmount,
      merchant_id: testMerchantId || undefined,
      mcc_code: testMccCode || undefined,
    })
    setCheckResult(result as CheckResult)
  }

  /* ─── Render ─── */

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">
          Policy Management
        </h1>
        <p className="text-gray-400 mt-1">
          Define and apply natural language spending policies for AI agents
        </p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Left: Policy Editor (2/3 width) ── */}
        <div className="lg:col-span-2 space-y-5">
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-5">
              <Sparkles className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Policy Editor</h2>
            </div>

            {/* Agent selector */}
            <div className="mb-5">
              <SectionLabel>Agent</SectionLabel>
              <div className="relative">
                <select
                  value={selectedAgentId}
                  onChange={(e) => {
                    setSelectedAgentId(e.target.value)
                    setParsedResult(null)
                    setPreviewResult(null)
                    setApplySuccess(false)
                    setConfirmApply(false)
                    setCheckResult(null)
                  }}
                  className="w-full appearance-none px-4 py-2.5 bg-dark-300 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50 pr-10"
                >
                  <option value="" disabled>
                    {agentsLoading ? 'Loading agents…' : 'Select an agent'}
                  </option>
                  {agents.map((agent) => (
                    <option key={agentId(agent)} value={agentId(agent)}>
                      {agent.name}
                      {!agent.is_active ? ' (inactive)' : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
              </div>
            </div>

            {/* Current policy summary */}
            {selectedAgentId && (
              <div className="mb-5">
                <SectionLabel>Current Policy</SectionLabel>
                {policyLoading ? (
                  <div className="flex items-center gap-2 py-4 text-gray-500 text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading current policy…
                  </div>
                ) : currentPolicy ? (
                  <PolicySummary policy={currentPolicy as CurrentPolicy} />
                ) : (
                  <p className="text-sm text-gray-500 py-2">
                    No policy configured for this agent.
                  </p>
                )}
              </div>
            )}

            {/* Natural language textarea */}
            <div className="mb-4">
              <SectionLabel>Natural Language Policy</SectionLabel>

              {/* Example chips */}
              <div className="flex flex-wrap gap-2 mb-3">
                {EXAMPLE_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => handleChipClick(chip)}
                    className={clsx(
                      'px-3 py-1.5 text-xs border transition-all',
                      policyText === chip
                        ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                        : 'bg-dark-200 text-gray-400 border-dark-100 hover:text-white hover:border-dark-100/60'
                    )}
                  >
                    {chip}
                  </button>
                ))}
              </div>

              <textarea
                value={policyText}
                onChange={(e) => {
                  setPolicyText(e.target.value)
                  setParsedResult(null)
                  setPreviewResult(null)
                  setApplySuccess(false)
                  setConfirmApply(false)
                }}
                placeholder="e.g. Max $50 per transaction, only allow OpenAI and Anthropic, no gambling, require approval above $100…"
                rows={4}
                className="w-full px-4 py-3 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 resize-none"
              />
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={handleParse}
                disabled={!policyText.trim() || parseMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:border-sardis-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium"
              >
                {parseMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Parse
              </button>

              <button
                onClick={handlePreview}
                disabled={
                  !selectedAgentId ||
                  !policyText.trim() ||
                  previewMutation.isPending
                }
                className="flex items-center gap-2 px-4 py-2 bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:border-sardis-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium"
              >
                {previewMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
                Preview
              </button>

              {!confirmApply ? (
                <button
                  onClick={() => setConfirmApply(true)}
                  disabled={
                    !selectedAgentId ||
                    !policyText.trim() ||
                    applyMutation.isPending
                  }
                  className="flex items-center gap-2 px-5 py-2 bg-sardis-500 text-dark-400 font-semibold hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
                >
                  <Send className="w-4 h-4" />
                  Apply Policy
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-yellow-400">Confirm apply?</span>
                  <button
                    onClick={handleApply}
                    disabled={applyMutation.isPending}
                    className="flex items-center gap-1.5 px-4 py-2 bg-sardis-500 text-dark-400 font-semibold hover:bg-sardis-400 transition-colors disabled:opacity-40 text-sm"
                  >
                    {applyMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4" />
                    )}
                    Yes, Apply
                  </button>
                  <button
                    onClick={() => setConfirmApply(false)}
                    className="px-3 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            {/* Success message */}
            {applySuccess && (
              <div className="mt-4 flex items-center gap-2 p-3 bg-sardis-500/10 border border-sardis-500/30 text-sardis-400 text-sm">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                Policy applied successfully.
              </div>
            )}

            {/* Apply error */}
            {applyMutation.isError && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                {applyMutation.error instanceof Error
                  ? applyMutation.error.message
                  : 'Failed to apply policy.'}
              </div>
            )}

            {/* Parse result */}
            {parsedResult && !parseMutation.isError && (
              <ParsedResult result={parsedResult} />
            )}

            {parseMutation.isError && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                {parseMutation.error instanceof Error
                  ? parseMutation.error.message
                  : 'Failed to parse policy.'}
              </div>
            )}

            {/* Preview result */}
            {previewResult && !previewMutation.isError && (
              <div className="mt-4 space-y-3">
                <SectionLabel>Preview</SectionLabel>
                {previewResult.confirmation_message && (
                  <p className="text-sm text-gray-300 p-3 bg-dark-300 border border-dark-100">
                    {previewResult.confirmation_message}
                  </p>
                )}
                {previewResult.warnings && previewResult.warnings.length > 0 && (
                  <WarningBox warnings={previewResult.warnings} />
                )}
                {previewResult.parsed && (
                  <ParsedResult result={previewResult.parsed} />
                )}
              </div>
            )}

            {previewMutation.isError && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                {previewMutation.error instanceof Error
                  ? previewMutation.error.message
                  : 'Failed to preview policy.'}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Policy Tester (1/3 width) ── */}
        <div className="space-y-5">
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-5">
              <ShieldCheck className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Policy Tester</h2>
            </div>

            {!selectedAgentId && (
              <p className="text-sm text-gray-500 mb-4">
                Select an agent in the editor to test its policy.
              </p>
            )}

            <div className="space-y-4">
              <div>
                <SectionLabel>Amount (USD)</SectionLabel>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={testAmount}
                  onChange={(e) => {
                    setTestAmount(e.target.value)
                    setCheckResult(null)
                  }}
                  placeholder="e.g. 75.00"
                  className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div>
                <SectionLabel>Merchant ID (optional)</SectionLabel>
                <input
                  type="text"
                  value={testMerchantId}
                  onChange={(e) => {
                    setTestMerchantId(e.target.value)
                    setCheckResult(null)
                  }}
                  placeholder="e.g. merchant_openai"
                  className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <div>
                <SectionLabel>MCC Code (optional)</SectionLabel>
                <input
                  type="text"
                  value={testMccCode}
                  onChange={(e) => {
                    setTestMccCode(e.target.value)
                    setCheckResult(null)
                  }}
                  placeholder="e.g. 5734"
                  className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                />
              </div>

              <button
                onClick={handleCheck}
                disabled={
                  !selectedAgentId ||
                  !testAmount ||
                  checkMutation.isPending
                }
                className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 font-semibold hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
              >
                {checkMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4" />
                )}
                Check Policy
              </button>
            </div>

            {/* Check result */}
            {checkResult && (
              <div
                className={clsx(
                  'mt-5 p-5 border text-center',
                  checkResult.allowed
                    ? 'bg-sardis-500/5 border-sardis-500/30'
                    : 'bg-red-500/5 border-red-500/30'
                )}
              >
                <div className="flex justify-center mb-3">
                  {checkResult.allowed ? (
                    <CheckCircle2 className="w-10 h-10 text-sardis-400" />
                  ) : (
                    <XCircle className="w-10 h-10 text-red-400" />
                  )}
                </div>
                <p
                  className={clsx(
                    'text-lg font-bold tracking-wide',
                    checkResult.allowed ? 'text-sardis-400' : 'text-red-400'
                  )}
                >
                  {checkResult.allowed ? 'ALLOWED' : 'DENIED'}
                </p>
                <p className="text-sm text-gray-400 mt-2">{checkResult.reason}</p>
              </div>
            )}

            {checkMutation.isError && (
              <div className="mt-4 flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <XCircle className="w-4 h-4 mt-0.5 shrink-0" />
                {checkMutation.error instanceof Error
                  ? checkMutation.error.message
                  : 'Failed to check policy.'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Applied Policies Summary */}
      <div className="card p-6">
        <div className="flex items-center gap-2 mb-5">
          <BarChart2 className="w-5 h-5 text-sardis-400" />
          <h2 className="text-lg font-semibold text-white">Applied Policies</h2>
        </div>

        {agentsLoading ? (
          <div className="flex items-center gap-2 py-6 text-gray-500 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading agents…
          </div>
        ) : agentsWithPolicies.length === 0 ? (
          <div className="text-center py-10">
            <Shield className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">No agents found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase border-b border-dark-100">
                  <th className="pb-3 pr-4 font-medium">Agent</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Trust Level</th>
                  <th className="pb-3 pr-4 font-medium">Per-TX Limit</th>
                  <th className="pb-3 pr-4 font-medium">Daily Limit</th>
                  <th className="pb-3 font-medium">Approval Threshold</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-100">
                {agentsWithPolicies.map((agent) => (
                  <AgentPolicyRow
                    key={agentId(agent)}
                    agent={agent}
                    isSelected={agentId(agent) === selectedAgentId}
                    onSelect={() => setSelectedAgentId(agentId(agent))}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Agent policy row with inline policy fetch ─── */

function AgentPolicyRow({
  agent,
  isSelected,
  onSelect,
}: {
  agent: Agent
  isSelected: boolean
  onSelect: () => void
}) {
  const id = agent.agent_id ?? agent.id ?? ''
  const { data: policy, isLoading } = usePolicy(id)
  const p = policy as CurrentPolicy | null | undefined

  return (
    <tr
      onClick={onSelect}
      className={clsx(
        'transition-colors cursor-pointer',
        isSelected
          ? 'bg-sardis-500/5'
          : 'hover:bg-dark-200/50'
      )}
    >
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2">
          <User className="w-4 h-4 text-gray-500 shrink-0" />
          <span className="text-sm text-white font-medium">{agent.name}</span>
        </div>
        <p className="text-xs text-gray-600 mt-0.5 pl-6">{id}</p>
      </td>
      <td className="py-3 pr-4">
        <span
          className={clsx(
            'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium',
            agent.is_active !== false
              ? 'bg-sardis-500/10 text-sardis-400'
              : 'bg-dark-200 text-gray-500'
          )}
        >
          <span
            className={clsx(
              'w-1.5 h-1.5 rounded-full',
              agent.is_active !== false ? 'bg-sardis-500' : 'bg-gray-600'
            )}
          />
          {agent.is_active !== false ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td className="py-3 pr-4">
        {isLoading ? (
          <Loader2 className="w-3.5 h-3.5 text-gray-600 animate-spin" />
        ) : (
          <span className="text-sm text-gray-300 capitalize">
            {p?.trust_level ?? '—'}
          </span>
        )}
      </td>
      <td className="py-3 pr-4">
        <span className="text-sm text-gray-300 mono-numbers">
          {isLoading ? '…' : formatCurrency(p?.limit_per_tx)}
        </span>
      </td>
      <td className="py-3 pr-4">
        <span className="text-sm text-gray-300 mono-numbers">
          {isLoading ? '…' : formatCurrency(p?.daily_limit)}
        </span>
      </td>
      <td className="py-3">
        <span className="text-sm text-gray-300 mono-numbers">
          {isLoading ? '…' : formatCurrency(p?.approval_threshold)}
        </span>
      </td>
    </tr>
  )
}
