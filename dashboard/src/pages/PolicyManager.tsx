/**
 * Policy Lifecycle Manager
 *
 * Unified policy authoring surface with tabs:
 *  Author   — NL input + live parse preview
 *  Test     — scenario builder + results table
 *  Deploy   — wallet select + diff view + confirmation
 *  History  — per-wallet policy timeline with rollback
 */

import { useState, useCallback } from 'react'
import {
  FileText,
  FlaskConical,
  Send,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  DollarSign,
  Tag,
  ShieldCheck,
  Eye,
  Sparkles,
  Info,
} from 'lucide-react'
import clsx from 'clsx'
import {
  useAgents,
  useParsePolicy,
  useApplyPolicy,
  usePolicyTestDraft,
  useWallets,
} from '../hooks/useApi'

// ── Types ────────────────────────────────────────────────────────────────────

type TabId = 'author' | 'test' | 'deploy' | 'history'

interface ParsedPolicy {
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
  merchant_restrictions?: string[]
  warnings?: string[]
  [key: string]: unknown
}

interface TestScenario {
  id: string
  label: string
  amount: string
  merchant: string
  category: string
}

interface TestResult {
  scenarioId: string
  label: string
  amount: string
  merchant: string
  verdict: 'allow' | 'deny' | 'approval_required'
  would_succeed: boolean
  failure_reasons: string[]
}

interface PolicyHistoryEntry {
  id: string
  timestamp: string
  policy_text: string
  deployed_by: string
  version: number
}

// ── Static preset scenarios ───────────────────────────────────────────────────

const PRESET_SCENARIOS: TestScenario[] = [
  { id: 'small', label: 'Small purchase ($10)', amount: '10', merchant: 'coffee-shop', category: '5812' },
  { id: 'large', label: 'Large purchase ($5000)', amount: '5000', merchant: 'electronics-store', category: '5734' },
  { id: 'gambling', label: 'Gambling site', amount: '100', merchant: 'betway-casino', category: '7995' },
  { id: 'api', label: 'API service', amount: '50', merchant: 'openai-api', category: '7372' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val: number | null | undefined, prefix = '$') {
  if (val == null) return '—'
  return `${prefix}${val.toLocaleString()}`
}

function getInitialTab(): TabId {
  const hash = window.location.hash.replace('#', '')
  const valid: TabId[] = ['author', 'test', 'deploy', 'history']
  return valid.includes(hash as TabId) ? (hash as TabId) : 'author'
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'default' | 'success' | 'danger' | 'warn' }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded',
        variant === 'success' && 'bg-green-500/10 text-green-400 border border-green-500/20',
        variant === 'danger' && 'bg-red-500/10 text-red-400 border border-red-500/20',
        variant === 'warn' && 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
        variant === 'default' && 'bg-dark-200 text-gray-400 border border-dark-100',
      )}
    >
      {children}
    </span>
  )
}

// ── Parsed Policy Preview ─────────────────────────────────────────────────────

function PolicyPreview({ parsed }: { parsed: ParsedPolicy }) {
  const limits = parsed.spending_limits ?? {}
  const cats = parsed.category_restrictions ?? {}
  const time = parsed.time_restrictions ?? {}

  return (
    <div className="space-y-4">
      {/* Spending limits */}
      <div className="bg-dark-200 border border-dark-100 p-4 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <DollarSign className="w-4 h-4 text-sardis-400" />
          Spending Limits
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          {[
            { label: 'Per transaction', val: limits.per_tx },
            { label: 'Daily', val: limits.daily },
            { label: 'Weekly', val: limits.weekly },
            { label: 'Monthly', val: limits.monthly },
            { label: 'Total cap', val: limits.total },
          ].map(({ label, val }) => (
            <div key={label} className="flex justify-between">
              <span className="text-gray-400">{label}</span>
              <span className={clsx('font-mono', val == null ? 'text-gray-600' : 'text-white')}>{fmt(val)}</span>
            </div>
          ))}
          {parsed.approval_threshold != null && (
            <div className="flex justify-between col-span-2">
              <span className="text-gray-400">Requires approval above</span>
              <span className="font-mono text-yellow-400">{fmt(parsed.approval_threshold)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Category restrictions */}
      {(cats.blocked?.length || cats.allowed?.length) ? (
        <div className="bg-dark-200 border border-dark-100 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Tag className="w-4 h-4 text-sardis-400" />
            Category Rules
          </div>
          {cats.blocked?.length ? (
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Blocked categories</p>
              <div className="flex flex-wrap gap-1.5">
                {cats.blocked.map((c) => <Badge key={c} variant="danger">{c}</Badge>)}
              </div>
            </div>
          ) : null}
          {cats.allowed?.length ? (
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Allowed only</p>
              <div className="flex flex-wrap gap-1.5">
                {cats.allowed.map((c) => <Badge key={c} variant="success">{c}</Badge>)}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Time restrictions */}
      {(time.window || time.allowed_hours) ? (
        <div className="bg-dark-200 border border-dark-100 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <Clock className="w-4 h-4 text-sardis-400" />
            Time Windows
          </div>
          {time.window && (
            <p className="text-sm text-gray-300">{time.window}</p>
          )}
          {time.allowed_hours && (
            <p className="text-sm text-gray-400 font-mono">{time.allowed_hours}</p>
          )}
        </div>
      ) : null}

      {/* Warnings */}
      {parsed.warnings?.length ? (
        <div className="bg-yellow-500/5 border border-yellow-500/20 p-3 flex gap-2">
          <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
          <ul className="space-y-1">
            {parsed.warnings.map((w, i) => (
              <li key={i} className="text-sm text-yellow-300">{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

// ── Tab: Author ───────────────────────────────────────────────────────────────

function AuthorTab({
  draftText,
  setDraftText,
  parsedPolicy,
  setParsedPolicy,
}: {
  draftText: string
  setDraftText: (v: string) => void
  parsedPolicy: ParsedPolicy | null
  setParsedPolicy: (v: ParsedPolicy | null) => void
}) {
  const parse = useParsePolicy()

  async function handleParse() {
    if (!draftText.trim()) return
    try {
      const result = await parse.mutateAsync(draftText)
      setParsedPolicy(result as ParsedPolicy)
    } catch {
      // error shown below
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2 text-sm text-gray-400 bg-dark-200 border border-dark-100 p-3">
        <Info className="w-4 h-4 text-sardis-400 flex-shrink-0 mt-0.5" />
        Write a spending policy in plain English. Sardis will parse it into structured rules that govern agent payments.
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: NL Input */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-300">
            Natural language policy
          </label>
          <textarea
            value={draftText}
            onChange={(e) => {
              setDraftText(e.target.value)
              if (parsedPolicy) setParsedPolicy(null)
            }}
            placeholder={`E.g. "Allow up to $500 per transaction and $2000 per day. Block gambling and adult content. Require approval for purchases above $300."`}
            rows={14}
            className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-sm text-white placeholder-gray-600 font-mono focus:outline-none focus:border-sardis-500/60 resize-none"
          />
          <button
            onClick={handleParse}
            disabled={!draftText.trim() || parse.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 text-sm font-semibold hover:bg-sardis-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {parse.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {parse.isPending ? 'Parsing…' : 'Parse Policy'}
          </button>
          {parse.isError && (
            <p className="text-sm text-red-400">
              {(parse.error as Error)?.message ?? 'Parse failed. Check your API connection.'}
            </p>
          )}
        </div>

        {/* Right: Structured preview */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-300">
            Structured preview
          </label>
          {parsedPolicy ? (
            <PolicyPreview parsed={parsedPolicy} />
          ) : (
            <div className="h-full min-h-48 bg-dark-200 border border-dashed border-dark-100 flex items-center justify-center">
              <div className="text-center text-gray-600 space-y-2">
                <Eye className="w-8 h-8 mx-auto opacity-40" />
                <p className="text-sm">Parse your policy to see the structured output</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Test ─────────────────────────────────────────────────────────────────

function TestTab({ draftText }: { draftText: string }) {
  const testDraft = usePolicyTestDraft()
  const { data: agents } = useAgents()

  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [customAmount, setCustomAmount] = useState('')
  const [customMerchant, setCustomMerchant] = useState('')
  const [customCategory, setCustomCategory] = useState('')
  const [results, setResults] = useState<TestResult[]>([])
  const [running, setRunning] = useState(false)

  const parsedDef = draftText.trim()
    ? {
        version: '1.0',
        rules: [{ type: 'natural_language', params: { text: draftText } }],
        metadata: { source: 'policy-manager-draft' },
      }
    : undefined

  async function runScenario(scenario: TestScenario) {
    if (!parsedDef) {
      return {
        scenarioId: scenario.id,
        label: scenario.label,
        amount: scenario.amount,
        merchant: scenario.merchant,
        verdict: 'deny',
        would_succeed: false,
        failure_reasons: ['Write a draft policy before testing scenarios.'],
      } as TestResult
    }

    const payload = {
      amount: scenario.amount,
      currency: 'USDC',
      agent_id: selectedAgentId || undefined,
      merchant_id: scenario.merchant,
      mcc_code: scenario.category,
      definition: parsedDef,
    }
    try {
      const res = await testDraft.mutateAsync(payload)
      const apiVerdict = (res.policy_result?.verdict as string | undefined) ?? (res.would_succeed ? 'allowed' : 'denied')
      const verdict =
        apiVerdict === 'requires_approval'
          ? 'approval_required'
          : res.would_succeed
            ? 'allow'
            : 'deny'
      return {
        scenarioId: scenario.id,
        label: scenario.label,
        amount: scenario.amount,
        merchant: scenario.merchant,
        verdict,
        would_succeed: res.would_succeed,
        failure_reasons: res.failure_reasons ?? [],
      } as TestResult
    } catch (err) {
      return {
        scenarioId: scenario.id,
        label: scenario.label,
        amount: scenario.amount,
        merchant: scenario.merchant,
        verdict: 'deny',
        would_succeed: false,
        failure_reasons: [(err as Error)?.message ?? 'Request failed'],
      } as TestResult
    }
  }

  async function runAll() {
    setRunning(true)
    setResults([])
    const newResults: TestResult[] = []
    for (const s of PRESET_SCENARIOS) {
      const r = await runScenario(s)
      newResults.push(r)
      setResults([...newResults])
    }
    setRunning(false)
  }

  async function runCustom() {
    if (!customAmount) return
    setRunning(true)
    const custom: TestScenario = {
      id: 'custom',
      label: `Custom ($${customAmount})`,
      amount: customAmount,
      merchant: customMerchant || 'unknown-merchant',
      category: customCategory || '0000',
    }
    const r = await runScenario(custom)
    setResults((prev) => {
      const filtered = prev.filter((x) => x.scenarioId !== 'custom')
      return [...filtered, r]
    })
    setRunning(false)
  }

  return (
    <div className="space-y-6">
      {!draftText.trim() && (
        <div className="flex items-center gap-2 text-sm text-yellow-400 bg-yellow-500/5 border border-yellow-500/20 p-3">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          No draft policy written yet. Go to the Author tab first. Draft policy tests do not use the live policy.
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Controls */}
        <div className="space-y-5">
          {/* Agent selector (optional) */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Agent context <span className="text-gray-600 font-normal">(optional)</span>
            </label>
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white focus:outline-none focus:border-sardis-500/60"
            >
              <option value="">— No specific agent —</option>
              {(agents ?? []).map((a) => {
                const id = (a as { agent_id?: string; id?: string }).agent_id ?? (a as { id?: string }).id ?? ''
                return (
                  <option key={id} value={id}>
                    {(a as { name: string }).name} ({id.slice(0, 8)}…)
                  </option>
                )
              })}
            </select>
          </div>

          {/* Preset scenarios */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">Preset scenarios</label>
            <div className="space-y-2">
              {PRESET_SCENARIOS.map((s) => (
                <div key={s.id} className="flex items-center justify-between bg-dark-200 border border-dark-100 px-4 py-3">
                  <div>
                    <p className="text-sm text-white">{s.label}</p>
                    <p className="text-xs text-gray-500 font-mono mt-0.5">merchant: {s.merchant} · mcc: {s.category}</p>
                  </div>
                </div>
              ))}
            </div>
            <button
              onClick={runAll}
              disabled={running || !draftText.trim()}
              className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 text-sm font-semibold hover:bg-sardis-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors w-full justify-center mt-2"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
              {running ? 'Running…' : 'Run All Scenarios'}
            </button>
          </div>

          {/* Custom scenario */}
          <div className="space-y-2 border-t border-dark-100 pt-4">
            <label className="block text-sm font-medium text-gray-300">Custom scenario</label>
            <input
              type="number"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              placeholder="Amount (e.g. 250)"
              className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/60"
            />
            <input
              type="text"
              value={customMerchant}
              onChange={(e) => setCustomMerchant(e.target.value)}
              placeholder="Merchant ID (optional)"
              className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/60"
            />
            <input
              type="text"
              value={customCategory}
              onChange={(e) => setCustomCategory(e.target.value)}
              placeholder="MCC code (optional, e.g. 5734)"
              className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/60"
            />
            <button
              onClick={runCustom}
              disabled={!customAmount || running || !draftText.trim()}
              className="flex items-center gap-2 px-5 py-2.5 border border-sardis-500/40 text-sardis-400 text-sm font-medium hover:bg-sardis-500/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors w-full justify-center"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
              Test Custom Scenario
            </button>
          </div>
        </div>

        {/* Right: Results */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-300">Results</label>
          {results.length === 0 ? (
            <div className="bg-dark-200 border border-dashed border-dark-100 flex items-center justify-center min-h-64">
              <div className="text-center text-gray-600 space-y-2">
                <FlaskConical className="w-8 h-8 mx-auto opacity-40" />
                <p className="text-sm">Run scenarios to see results</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {results.map((r) => (
                <div
                  key={r.scenarioId}
                  className={clsx(
                    'border p-4 space-y-1.5',
                    r.would_succeed
                      ? 'bg-green-500/5 border-green-500/20'
                      : 'bg-red-500/5 border-red-500/20',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{r.label}</span>
                    {r.verdict === 'allow' ? (
                      <Badge variant="success">
                        <CheckCircle2 className="w-3 h-3" />
                        ALLOW
                      </Badge>
                    ) : r.verdict === 'approval_required' ? (
                      <Badge variant="warn">
                        <AlertTriangle className="w-3 h-3" />
                        APPROVAL
                      </Badge>
                    ) : (
                      <Badge variant="danger">
                        <XCircle className="w-3 h-3" />
                        DENY
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 font-mono">
                    ${r.amount} · {r.merchant}
                  </p>
                  {r.failure_reasons.length > 0 && (
                    <ul className="space-y-0.5">
                      {r.failure_reasons.map((reason, i) => (
                        <li key={i} className="text-xs text-red-400">— {reason}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Deploy ───────────────────────────────────────────────────────────────

function DeployTab({ draftText, parsedPolicy }: { draftText: string; parsedPolicy: ParsedPolicy | null }) {
  const { data: wallets, isLoading: walletsLoading } = useWallets()
  const { data: agents } = useAgents()
  const applyPolicy = useApplyPolicy()

  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [deploySuccess, setDeploySuccess] = useState(false)
  const [deployError, setDeployError] = useState<string | null>(null)

  const walletList = (wallets ?? []) as Array<{ wallet_id?: string; id?: string; agent_id?: string; balance?: string }>
  const agentList = (agents ?? []) as Array<{ agent_id?: string; id?: string; name: string }>

  async function handleDeploy() {
    if (!selectedAgentId || !draftText.trim()) return
    setDeployError(null)
    try {
      await applyPolicy.mutateAsync({ agentId: selectedAgentId, naturalLanguage: draftText })
      setDeploySuccess(true)
      setConfirmOpen(false)
    } catch (err) {
      setDeployError((err as Error)?.message ?? 'Deploy failed')
      setConfirmOpen(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {!draftText.trim() && (
        <div className="flex items-center gap-2 text-sm text-yellow-400 bg-yellow-500/5 border border-yellow-500/20 p-3">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          No draft policy. Write one in the Author tab before deploying.
        </div>
      )}

      {deploySuccess && (
        <div className="flex items-center gap-2 text-sm text-green-400 bg-green-500/5 border border-green-500/20 p-3">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          Policy deployed successfully to agent {selectedAgentId.slice(0, 8)}…
        </div>
      )}

      {deployError && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/5 border border-red-500/20 p-3">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {deployError}
        </div>
      )}

      {/* Agent selector */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Target agent</label>
        <select
          value={selectedAgentId}
          onChange={(e) => { setSelectedAgentId(e.target.value); setDeploySuccess(false) }}
          className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white focus:outline-none focus:border-sardis-500/60"
        >
          <option value="">— Select an agent —</option>
          {agentList.map((a) => {
            const id = a.agent_id ?? a.id ?? ''
            return (
              <option key={id} value={id}>
                {a.name} ({id.slice(0, 8)}…)
              </option>
            )
          })}
        </select>
        {walletsLoading && <p className="text-xs text-gray-500">Loading wallets…</p>}
        {walletList.length > 0 && selectedAgentId && (
          <p className="text-xs text-gray-500">
            {walletList.filter((w) => w.agent_id === selectedAgentId).length} wallet(s) attached to this agent
          </p>
        )}
      </div>

      {/* Diff view */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-300">Policy diff</label>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-dark-200 border border-dark-100 p-4">
            <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Current (active)</p>
            <p className="text-xs text-gray-500 italic">Fetch current policy by selecting an agent above</p>
          </div>
          <div className="bg-dark-200 border border-sardis-500/30 p-4">
            <p className="text-xs text-sardis-400 mb-2 uppercase tracking-wider">New (draft)</p>
            {draftText.trim() ? (
              <p className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">{draftText}</p>
            ) : (
              <p className="text-xs text-gray-600 italic">No draft written yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Structured preview of draft */}
      {parsedPolicy && (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">Draft policy structure</label>
          <PolicyPreview parsed={parsedPolicy} />
        </div>
      )}

      {/* Deploy button */}
      <button
        onClick={() => setConfirmOpen(true)}
        disabled={!selectedAgentId || !draftText.trim() || applyPolicy.isPending}
        className="flex items-center gap-2 px-6 py-3 bg-sardis-500 text-dark-400 text-sm font-semibold hover:bg-sardis-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Send className="w-4 h-4" />
        Deploy Policy
      </button>

      {/* Confirmation modal */}
      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-dark-300 border border-dark-100 w-full max-w-md p-6 space-y-5">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-6 h-6 text-sardis-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-semibold text-white">Confirm deployment</h3>
                <p className="text-sm text-gray-400 mt-1">
                  You are about to apply a new spending policy to agent{' '}
                  <span className="font-mono text-white">{selectedAgentId.slice(0, 8)}…</span>.
                  This will immediately govern all future payments from this agent.
                </p>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmOpen(false)}
                className="px-4 py-2 text-sm text-gray-400 border border-dark-100 hover:text-white hover:border-dark-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeploy}
                disabled={applyPolicy.isPending}
                className="flex items-center gap-2 px-5 py-2 bg-sardis-500 text-dark-400 text-sm font-semibold hover:bg-sardis-400 disabled:opacity-50 transition-colors"
              >
                {applyPolicy.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {applyPolicy.isPending ? 'Deploying…' : 'Confirm Deploy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab: History ──────────────────────────────────────────────────────────────

// Static sample history (real data would come from /wallets/:id/policy-history)
const SAMPLE_HISTORY: PolicyHistoryEntry[] = [
  {
    id: 'ph-3',
    timestamp: '2026-03-10T08:32:00Z',
    policy_text: 'Allow up to $500 per transaction and $2000 per day. Block gambling and adult content.',
    deployed_by: 'dashboard',
    version: 3,
  },
  {
    id: 'ph-2',
    timestamp: '2026-03-05T14:11:00Z',
    policy_text: 'Allow up to $200 per transaction. Block gambling.',
    deployed_by: 'api-key',
    version: 2,
  },
  {
    id: 'ph-1',
    timestamp: '2026-02-28T09:00:00Z',
    policy_text: 'Allow up to $100 per transaction.',
    deployed_by: 'dashboard',
    version: 1,
  },
]

function HistoryTab({
  setDraftText,
  setParsedPolicy,
  setActiveTab,
}: {
  setDraftText: (v: string) => void
  setParsedPolicy: (v: ParsedPolicy | null) => void
  setActiveTab: (t: TabId) => void
}) {
  const { data: agents } = useAgents()
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [rolledBackId, setRolledBackId] = useState<string | null>(null)

  const agentList = (agents ?? []) as Array<{ agent_id?: string; id?: string; name: string }>

  function handleRollback(entry: PolicyHistoryEntry) {
    setDraftText(entry.policy_text)
    setParsedPolicy(null)
    setRolledBackId(entry.id)
    // Navigate user to author tab so they can review/parse before re-deploying
    setTimeout(() => {
      setActiveTab('author')
      window.location.hash = 'author'
    }, 800)
  }

  const history = SAMPLE_HISTORY

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-400 bg-dark-200 border border-dark-100 p-3">
        <Info className="w-4 h-4 text-sardis-400 flex-shrink-0" />
        Version history shows past policies per agent. Rolling back loads the policy text into the Author tab for review before re-deploying.
      </div>

      {/* Agent selector */}
      <div className="space-y-2 max-w-sm">
        <label className="block text-sm font-medium text-gray-300">Agent</label>
        <select
          value={selectedAgentId}
          onChange={(e) => setSelectedAgentId(e.target.value)}
          className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white focus:outline-none focus:border-sardis-500/60"
        >
          <option value="">— Select agent to view history —</option>
          {agentList.map((a) => {
            const id = a.agent_id ?? a.id ?? ''
            return (
              <option key={id} value={id}>
                {a.name} ({id.slice(0, 8)}…)
              </option>
            )
          })}
        </select>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {history.map((entry, idx) => (
          <div
            key={entry.id}
            className={clsx(
              'bg-dark-200 border p-5 space-y-3',
              idx === 0 ? 'border-sardis-500/30' : 'border-dark-100',
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">Version {entry.version}</span>
                  {idx === 0 && <Badge variant="success">Active</Badge>}
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(entry.timestamp).toLocaleString()}
                  </span>
                  <span>Deployed by: {entry.deployed_by}</span>
                </div>
              </div>
              {idx !== 0 && (
                <button
                  onClick={() => handleRollback(entry)}
                  disabled={rolledBackId === entry.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-dark-100 text-gray-400 hover:text-white hover:border-sardis-500/40 disabled:opacity-50 transition-colors flex-shrink-0"
                >
                  {rolledBackId === entry.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <RotateCcw className="w-3 h-3" />
                  )}
                  {rolledBackId === entry.id ? 'Loading…' : 'Rollback'}
                </button>
              )}
            </div>
            <div className="bg-dark-300 border border-dark-100 px-4 py-3">
              <p className="text-xs text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">{entry.policy_text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── TABS config ───────────────────────────────────────────────────────────────

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'author', label: 'Author', icon: <FileText className="w-4 h-4" /> },
  { id: 'test', label: 'Test', icon: <FlaskConical className="w-4 h-4" /> },
  { id: 'deploy', label: 'Deploy', icon: <Send className="w-4 h-4" /> },
  { id: 'history', label: 'History', icon: <Clock className="w-4 h-4" /> },
]

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PolicyManagerPage() {
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab)
  const [draftText, setDraftText] = useState('')
  const [parsedPolicy, setParsedPolicy] = useState<ParsedPolicy | null>(null)

  const switchTab = useCallback((id: TabId) => {
    setActiveTab(id)
    window.location.hash = id
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Policy Manager</h1>
        <p className="text-gray-400 mt-1">
          Author, test, and deploy spending policies through a unified lifecycle.
        </p>
      </div>

      {/* Draft status bar */}
      <div className="flex items-center gap-3 text-sm">
        <div
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 border text-xs font-medium',
            draftText.trim()
              ? 'bg-sardis-500/10 border-sardis-500/30 text-sardis-400'
              : 'bg-dark-200 border-dark-100 text-gray-500',
          )}
        >
          <FileText className="w-3.5 h-3.5" />
          {draftText.trim() ? `Draft: ${draftText.trim().slice(0, 60)}${draftText.length > 60 ? '…' : ''}` : 'No draft'}
        </div>
        {parsedPolicy && (
          <Badge variant="success">
            <CheckCircle2 className="w-3 h-3" />
            Parsed
          </Badge>
        )}
      </div>

      {/* Tab bar */}
      <div className="border-b border-dark-100">
        <nav className="-mb-px flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => switchTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-sardis-500 text-sardis-400'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-dark-100',
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'author' && (
          <AuthorTab
            draftText={draftText}
            setDraftText={setDraftText}
            parsedPolicy={parsedPolicy}
            setParsedPolicy={setParsedPolicy}
          />
        )}
        {activeTab === 'test' && <TestTab draftText={draftText} />}
        {activeTab === 'deploy' && (
          <DeployTab draftText={draftText} parsedPolicy={parsedPolicy} />
        )}
        {activeTab === 'history' && (
          <HistoryTab
            setDraftText={setDraftText}
            setParsedPolicy={setParsedPolicy}
            setActiveTab={switchTab}
          />
        )}
      </div>
    </div>
  )
}
