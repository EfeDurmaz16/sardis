import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  FlaskConical,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Shield,
  ShieldCheck,
  Power,
  ChevronDown,
  ChevronRight,
  User,
} from 'lucide-react'
import clsx from 'clsx'
import { useSimulate, useAgents } from '../hooks/useApi'

/* ─── Types ─── */

interface SimulatePayload {
  amount: string
  currency?: string
  chain?: string
  sender_agent_id: string
  sender_wallet_id?: string
  recipient_wallet_id?: string
  recipient_address?: string
  source?: string
}

interface PolicyStep {
  step: string
  result: string
  reason?: string
}

interface PolicyResult {
  verdict?: string
  steps?: PolicyStep[]
  [key: string]: unknown
}

interface ComplianceResult {
  status?: string
  kyc_status?: string
  aml_status?: string
  risk_score?: number
  [key: string]: unknown
}

interface KillSwitchStatus {
  active?: boolean
  rails?: Record<string, unknown>
  chains?: Record<string, unknown>
  [key: string]: unknown
}

interface SimulateResult {
  would_succeed: boolean
  failure_reasons: string[]
  policy_result: PolicyResult | null
  compliance_result: ComplianceResult | null
  cap_check: object | null
  kill_switch_status: KillSwitchStatus | null
}

/* ─── Constants ─── */

const CURRENCIES = ['USDC', 'USDT', 'EURC'] as const
const CHAINS = ['base', 'polygon', 'arbitrum', 'optimism', 'ethereum'] as const
const SOURCES = ['ap2', 'a2a', 'checkout'] as const

/* ─── Sub-components ─── */

function StepRow({ step, index }: { step: PolicyStep; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const passed = step.result === 'pass' || step.result === 'allowed' || step.result === 'ok'
  const failed = step.result === 'fail' || step.result === 'denied' || step.result === 'blocked'
  const skipped = step.result === 'skip' || step.result === 'skipped'
  const hasReason = !!step.reason

  return (
    <div className="border border-dark-100 bg-dark-200">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-dark-300/50 transition-colors"
        onClick={() => hasReason && setExpanded(e => !e)}
        disabled={!hasReason}
      >
        <span className="text-xs text-gray-600 font-mono w-5 flex-shrink-0">{index + 1}</span>
        <span
          className={clsx(
            'w-2 h-2 flex-shrink-0',
            passed && 'bg-green-400',
            failed && 'bg-red-400',
            skipped && 'bg-gray-500',
            !passed && !failed && !skipped && 'bg-yellow-400',
          )}
        />
        <span className="text-sm text-gray-200 flex-1 font-medium">{step.step}</span>
        <span
          className={clsx(
            'text-xs px-2 py-0.5 font-mono',
            passed && 'text-green-400 bg-green-500/10',
            failed && 'text-red-400 bg-red-500/10',
            skipped && 'text-gray-500 bg-gray-500/10',
            !passed && !failed && !skipped && 'text-yellow-400 bg-yellow-500/10',
          )}
        >
          {step.result}
        </span>
        {hasReason && (
          expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
            : <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
        )}
      </button>
      {expanded && hasReason && (
        <div className="px-4 pb-3 pt-1 border-t border-dark-100">
          <p className="text-xs text-gray-400">{step.reason}</p>
        </div>
      )}
    </div>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
      {children}
    </label>
  )
}

function FieldInput({
  type = 'text',
  value,
  onChange,
  placeholder,
}: {
  type?: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 transition-colors"
    />
  )
}

function FieldSelect({
  value,
  onChange,
  options,
}: {
  value: string
  onChange: (v: string) => void
  options: readonly string[]
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm appearance-none focus:outline-none focus:border-sardis-500/60 transition-colors"
    >
      {options.map(o => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  )
}

/* ─── Results Panel ─── */

function ResultsPanel({ result }: { result: SimulateResult }) {
  const { would_succeed, failure_reasons, policy_result, compliance_result, kill_switch_status } = result
  const steps = policy_result?.steps ?? []

  // Determine if any kill switches are active
  const ksActive =
    kill_switch_status?.active === true ||
    Object.values(kill_switch_status?.rails ?? {}).some(Boolean) ||
    Object.values(kill_switch_status?.chains ?? {}).some(Boolean)

  return (
    <div className="space-y-5">
      {/* Overall Verdict */}
      <div
        className={clsx(
          'border p-6 flex flex-col items-center text-center',
          would_succeed
            ? 'bg-green-500/5 border-green-500/30'
            : 'bg-red-500/5 border-red-500/30',
        )}
      >
        {would_succeed ? (
          <CheckCircle2 className="w-14 h-14 text-green-400 mb-3" />
        ) : (
          <XCircle className="w-14 h-14 text-red-400 mb-3" />
        )}
        <p
          className={clsx(
            'text-2xl font-bold tracking-wide uppercase',
            would_succeed ? 'text-green-400' : 'text-red-400',
          )}
        >
          {would_succeed ? 'Would Succeed' : 'Would Fail'}
        </p>
        <p className="text-sm text-gray-500 mt-1">
          {would_succeed
            ? 'This payment would pass all policy and compliance checks.'
            : `${failure_reasons.length} check${failure_reasons.length !== 1 ? 's' : ''} failed.`}
        </p>
      </div>

      {/* Failure Reasons */}
      {failure_reasons.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">Failure Reasons</h3>
          </div>
          <ul className="space-y-2">
            {failure_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <XCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-red-300">{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Policy Checks Breakdown */}
      {steps.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
              <Shield className="w-4 h-4 text-sardis-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Policy Checks</h3>
              {policy_result?.verdict && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Verdict:{' '}
                  <span
                    className={clsx(
                      'font-medium',
                      policy_result.verdict === 'allowed' && 'text-green-400',
                      policy_result.verdict === 'denied' && 'text-red-400',
                      policy_result.verdict !== 'allowed' && policy_result.verdict !== 'denied' && 'text-yellow-400',
                    )}
                  >
                    {policy_result.verdict}
                  </span>
                </p>
              )}
            </div>
          </div>
          <div className="space-y-px">
            {steps.map((step, i) => (
              <StepRow key={i} step={step} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Compliance Result */}
      {compliance_result && (
        <div className="card p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
              <ShieldCheck className="w-4 h-4 text-sardis-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Compliance Result</h3>
              <p className="text-xs text-gray-500 mt-0.5">KYC / AML screening outcome</p>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {compliance_result.status && (
              <div className="px-3 py-3 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-1">Status</p>
                <p
                  className={clsx(
                    'text-sm font-semibold',
                    compliance_result.status === 'clear' && 'text-green-400',
                    compliance_result.status === 'flagged' && 'text-red-400',
                    compliance_result.status !== 'clear' && compliance_result.status !== 'flagged' && 'text-yellow-400',
                  )}
                >
                  {compliance_result.status}
                </p>
              </div>
            )}
            {compliance_result.kyc_status && (
              <div className="px-3 py-3 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-1">KYC</p>
                <p className="text-sm font-semibold text-white">{compliance_result.kyc_status}</p>
              </div>
            )}
            {compliance_result.aml_status && (
              <div className="px-3 py-3 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-1">AML</p>
                <p className="text-sm font-semibold text-white">{compliance_result.aml_status}</p>
              </div>
            )}
            {typeof compliance_result.risk_score === 'number' && (
              <div className="px-3 py-3 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-1">Risk Score</p>
                <p
                  className={clsx(
                    'text-sm font-semibold font-mono',
                    compliance_result.risk_score < 30 && 'text-green-400',
                    compliance_result.risk_score >= 30 && compliance_result.risk_score < 70 && 'text-yellow-400',
                    compliance_result.risk_score >= 70 && 'text-red-400',
                  )}
                >
                  {compliance_result.risk_score}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Kill Switch Status */}
      {kill_switch_status && (
        <div className="card p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div
                className={clsx(
                  'p-2 border',
                  ksActive ? 'bg-red-500/10 border-red-500/20' : 'bg-sardis-500/10 border-sardis-500/20',
                )}
              >
                <Power className={clsx('w-4 h-4', ksActive ? 'text-red-400' : 'text-sardis-400')} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Kill Switch Status</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Emergency suspension controls
                </p>
              </div>
            </div>
            <span
              className={clsx(
                'px-2.5 py-1 text-xs font-semibold uppercase tracking-wider border',
                ksActive
                  ? 'bg-red-500/15 text-red-400 border-red-500/30'
                  : 'bg-green-500/15 text-green-400 border-green-500/30',
              )}
            >
              {ksActive ? 'Active' : 'Clear'}
            </span>
          </div>

          {ksActive && (
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(kill_switch_status.rails ?? {})
                .filter(([, v]) => Boolean(v))
                .map(([rail]) => (
                  <span key={rail} className="px-2 py-0.5 bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
                    rail:{rail}
                  </span>
                ))}
              {Object.entries(kill_switch_status.chains ?? {})
                .filter(([, v]) => Boolean(v))
                .map(([chain]) => (
                  <span key={chain} className="px-2 py-0.5 bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono">
                    chain:{chain}
                  </span>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Empty State ─── */

function EmptyState() {
  return (
    <div className="card p-16 flex flex-col items-center justify-center gap-5 h-full min-h-[320px]">
      <div className="p-5 bg-dark-200 border border-dark-100">
        <FlaskConical className="w-12 h-12 text-gray-600" />
      </div>
      <div className="text-center max-w-xs">
        <h3 className="text-base font-semibold text-white mb-2">No simulation run yet</h3>
        <p className="text-sm text-gray-500 leading-relaxed">
          Fill in the form and click "Run Live Dry Run" to test the transaction against
          the currently deployed policy without touching the chain.
        </p>
      </div>
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <span className="w-1.5 h-1.5 bg-sardis-500" />
        No on-chain execution — read-only policy evaluation
      </div>
    </div>
  )
}

/* ─── Main Page ─── */

export default function SimulationPage() {
  const agentsQuery = useAgents()
  const simulate = useSimulate()

  const agents = ((agentsQuery.data ?? []) as { agent_id?: string; id?: string; name?: string }[])

  // Form state
  const [agentId, setAgentId] = useState('')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState<string>('USDC')
  const [chain, setChain] = useState<string>('base')
  const [source, setSource] = useState<string>('ap2')

  const canSubmit = !!agentId && !!amount && !simulate.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    const payload: SimulatePayload = {
      sender_agent_id: agentId,
      amount,
      currency,
      chain,
      source,
    }

    simulate.mutate(payload)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
            <FlaskConical className="w-8 h-8 text-sardis-400" />
            Live Policy Dry Run
          </h1>
          <p className="text-gray-400 mt-1 max-w-lg">
            Dry-run payments against the currently deployed policy without executing on chain.
            Use Policy Manager for draft-policy scenario testing before deployment.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to="/policy-manager"
              className="inline-flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 text-xs text-gray-300 hover:text-white hover:border-sardis-500/40 transition-colors"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-sardis-400" />
              Go to Policy Manager for draft tests
            </Link>
            <Link
              to="/control-center"
              className="inline-flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 text-xs text-gray-300 hover:text-white hover:border-sardis-500/40 transition-colors"
            >
              <Shield className="w-3.5 h-3.5 text-sardis-400" />
              Review evidence and approvals
            </Link>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 text-xs text-gray-500">
          <Shield className="w-4 h-4 text-sardis-400" />
          Read-only — no on-chain execution
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* ── Input Form (left, ~40%) ── */}
        <div className="w-full lg:w-[40%] flex-shrink-0">
          <form onSubmit={handleSubmit} className="card p-6 space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <FlaskConical className="w-4 h-4 text-sardis-400" />
              <h2 className="text-base font-semibold text-white">Simulation Parameters</h2>
            </div>

            {/* Agent selector */}
            <div>
              <FieldLabel>Agent <span className="text-red-400">*</span></FieldLabel>
              {agentsQuery.isLoading ? (
                <div className="flex items-center gap-2 px-3 py-2.5 bg-dark-200 border border-dark-100 text-gray-500 text-sm">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Loading agents...
                </div>
              ) : agents.length === 0 ? (
                <div className="flex items-center gap-2 px-3 py-2.5 bg-dark-200 border border-dark-100 text-gray-500 text-sm">
                  <User className="w-3.5 h-3.5" />
                  No agents found
                </div>
              ) : (
                <select
                  value={agentId}
                  onChange={e => setAgentId(e.target.value)}
                  required
                  className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm appearance-none focus:outline-none focus:border-sardis-500/60 transition-colors"
                >
                  <option value="" disabled>Select an agent...</option>
                  {agents.map(a => {
                    const id = a.agent_id ?? a.id ?? ''
                    return (
                      <option key={id} value={id}>
                        {a.name ? `${a.name} (${id})` : id}
                      </option>
                    )
                  })}
                </select>
              )}
            </div>

            {/* Amount */}
            <div>
              <FieldLabel>Amount <span className="text-red-400">*</span></FieldLabel>
              <FieldInput
                type="number"
                value={amount}
                onChange={setAmount}
                placeholder="e.g. 50.00"
              />
            </div>

            {/* Currency */}
            <div>
              <FieldLabel>Currency</FieldLabel>
              <FieldSelect value={currency} onChange={setCurrency} options={CURRENCIES} />
            </div>

            {/* Chain */}
            <div>
              <FieldLabel>Chain</FieldLabel>
              <FieldSelect value={chain} onChange={setChain} options={CHAINS} />
            </div>

            {/* Source */}
            <div>
              <FieldLabel>Source</FieldLabel>
              <FieldSelect value={source} onChange={setSource} options={SOURCES} />
            </div>

            {/* Error display */}
            {simulate.isError && (
              <div className="flex items-start gap-2.5 px-3 py-3 bg-red-500/5 border border-red-500/25">
                <XCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-red-300">
                  {(simulate.error as Error)?.message ?? 'Simulation failed. Check API connectivity.'}
                </p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={!canSubmit}
              className={clsx(
                'w-full flex items-center justify-center gap-2 px-5 py-3 font-semibold text-sm transition-colors',
                canSubmit
                  ? 'bg-sardis-500 text-white hover:bg-sardis-600'
                  : 'bg-dark-200 text-gray-600 border border-dark-100 cursor-not-allowed',
              )}
            >
              {simulate.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running simulation...
                </>
              ) : (
                <>
                  <FlaskConical className="w-4 h-4" />
                  Run Live Dry Run
                </>
              )}
            </button>
          </form>
        </div>

        {/* ── Results Panel (right, ~60%) ── */}
        <div className="w-full lg:flex-1 min-w-0">
          {simulate.isPending && (
            <div className="card p-16 flex flex-col items-center justify-center gap-4 min-h-[320px]">
              <Loader2 className="w-10 h-10 text-sardis-400 animate-spin" />
              <p className="text-gray-400 text-sm">Running policy evaluation...</p>
            </div>
          )}

          {!simulate.isPending && simulate.data && (
            <ResultsPanel result={simulate.data as unknown as SimulateResult} />
          )}

          {!simulate.isPending && !simulate.data && (
            <EmptyState />
          )}
        </div>
      </div>
    </div>
  )
}
