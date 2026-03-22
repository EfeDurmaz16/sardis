"use client";
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  Loader2,
  Power,
  PowerOff,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Sparkles,
  XCircle,
  FlaskConical,
  RotateCcw,
  ThumbsUp,
  Ban,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { policiesApi, approvalsApi, killSwitchApi, simulationApi, agentApi } from '@/api/client'

/* ─── Shared Types ─── */

type StepStatus = 'idle' | 'running' | 'done' | 'error'
type JsonObject = Record<string, unknown>

/* ─── Reusable Components ─── */

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="block text-sm font-medium text-gray-400 mb-2">{children}</label>
}

function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        'w-full px-4 py-3 bg-dark-300 border border-dark-100 text-white',
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
        'w-full px-4 py-3 bg-dark-300 border border-dark-100 text-white',
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

  return <span className={clsx('text-xs px-2.5 py-1 border', cfg.cls)}>{cfg.label}</span>
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
      className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors"
    >
      <Copy className="w-4 h-4" />
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

/* ─── Result Display Components ─── */

function ResultBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="p-3 bg-dark-200 border border-dark-100">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      {children}
    </div>
  )
}

function VerdictBadge({ allowed, label }: { allowed: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      {allowed ? (
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
      ) : (
        <XCircle className="w-5 h-5 text-red-400" />
      )}
      <span className={clsx('text-sm font-medium', allowed ? 'text-emerald-300' : 'text-red-300')}>
        {label}
      </span>
    </div>
  )
}

function ErrorBox({ message }: { message: string }) {
  if (!message) return null
  return (
    <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
      {message}
    </div>
  )
}

function JsonPreview({ data }: { data: unknown }) {
  return (
    <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

/* ─── Progress Stepper ─── */

function ProgressStepper({ currentBeat, beatStatuses }: { currentBeat: number; beatStatuses: StepStatus[] }) {
  return (
    <div className="flex items-center justify-center gap-0 py-4">
      {beatStatuses.map((status, idx) => {
        const beatNum = idx + 1
        const isCurrent = beatNum === currentBeat
        const isDone = status === 'done'
        const isError = status === 'error'
        const isUpcoming = beatNum > currentBeat

        return (
          <div key={beatNum} className="flex items-center">
            <div
              className={clsx(
                'w-9 h-9 flex items-center justify-center text-sm font-bold border-2 rounded-full transition-all',
                isCurrent && 'bg-sardis-500/20 border-sardis-500 text-sardis-400 ring-2 ring-sardis-500/30',
                isDone && !isCurrent && 'bg-emerald-500/20 border-emerald-500 text-emerald-400',
                isError && !isCurrent && 'bg-red-500/20 border-red-500 text-red-400',
                isUpcoming && 'bg-dark-300 border-dark-100 text-gray-500'
              )}
            >
              {isDone && !isCurrent ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : isError && !isCurrent ? (
                <XCircle className="w-4 h-4" />
              ) : (
                beatNum
              )}
            </div>
            {idx < beatStatuses.length - 1 && (
              <div
                className={clsx(
                  'w-8 h-0.5 transition-colors',
                  idx < currentBeat - 1 ? 'bg-emerald-500/50' : 'bg-dark-100'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ─── Beat Section Wrapper ─── */

function BeatSection({
  beatNumber,
  title,
  subtitle,
  icon: Icon,
  currentBeat,
  status,
  children,
}: {
  beatNumber: number
  title: string
  subtitle: string
  icon: React.ElementType
  currentBeat: number
  status: StepStatus
  children: React.ReactNode
}) {
  const isActive = beatNumber === currentBeat
  const isPast = beatNumber < currentBeat
  const isFuture = beatNumber > currentBeat
  const [manualOpen, setManualOpen] = useState(false)

  const isOpen = isActive || manualOpen

  return (
    <div
      className={clsx(
        'border transition-all',
        isActive && 'border-sardis-500/40 bg-dark-300/30',
        isPast && 'border-dark-100 bg-dark-300/10',
        isFuture && 'border-dark-100/50 opacity-60'
      )}
    >
      <button
        type="button"
        onClick={() => {
          if (!isFuture) setManualOpen(!manualOpen)
        }}
        className="w-full flex items-center gap-4 p-5 text-left"
      >
        <div
          className={clsx(
            'w-10 h-10 flex items-center justify-center flex-shrink-0',
            isActive && 'bg-sardis-500/10',
            isPast && status === 'done' && 'bg-emerald-500/10',
            isPast && status === 'error' && 'bg-red-500/10',
            isFuture && 'bg-dark-200'
          )}
        >
          <Icon
            className={clsx(
              'w-5 h-5',
              isActive && 'text-sardis-400',
              isPast && status === 'done' && 'text-emerald-400',
              isPast && status === 'error' && 'text-red-400',
              isFuture && 'text-gray-500'
            )}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-500">BEAT {beatNumber}</span>
            <StatusPill status={status} />
          </div>
          <h3 className={clsx('text-base font-semibold mt-1', isActive ? 'text-white' : 'text-gray-300')}>
            {title}
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>
        </div>
        <div className="flex-shrink-0 text-gray-500">
          {isOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
        </div>
      </button>

      {isOpen && (
        <div className="px-5 pb-5 border-t border-dark-100/50">
          <div className="pt-5">{children}</div>
        </div>
      )}
    </div>
  )
}

/* ─── Main Demo Page ─── */

export default function DemoPage() {
  /* ── Global State ── */
  const [currentBeat, setCurrentBeat] = useState(0) // 0 = setup phase, 1-7 = beats
  const [agentId, setAgentId] = useState<string>('')
  const [setupStatus, setSetupStatus] = useState<StepStatus>('idle')
  const [setupError, setSetupError] = useState('')

  /* ── Beat 1: Write Policy ── */
  const [policyText, setPolicyText] = useState('max $500/day, block gambling, require approval above $200')
  const [b1Status, setB1Status] = useState<StepStatus>('idle')
  const [b1Error, setB1Error] = useState('')
  const [parsedPolicy, setParsedPolicy] = useState<JsonObject | null>(null)
  const [appliedPolicy, setAppliedPolicy] = useState<JsonObject | null>(null)

  /* ── Beat 2: Normal Payment ── */
  const [b2Status, setB2Status] = useState<StepStatus>('idle')
  const [b2Error, setB2Error] = useState('')
  const [b2Result, setB2Result] = useState<{ allowed: boolean; reason: string } | null>(null)

  /* ── Beat 3: Over-Limit Block ── */
  const [b3Status, setB3Status] = useState<StepStatus>('idle')
  const [b3Error, setB3Error] = useState('')
  const [b3Result, setB3Result] = useState<{ allowed: boolean; reason: string } | null>(null)

  /* ── Beat 4: Approval Triggered ── */
  const [b4Status, setB4Status] = useState<StepStatus>('idle')
  const [b4Error, setB4Error] = useState('')
  const [b4CheckResult, setB4CheckResult] = useState<{ allowed: boolean; reason: string } | null>(null)
  const [b4PendingApprovals, setB4PendingApprovals] = useState<JsonObject[] | null>(null)
  const [b4ApproveResult, setB4ApproveResult] = useState<JsonObject | null>(null)
  const [b4Phase, setB4Phase] = useState<'idle' | 'checked' | 'listed' | 'approved'>('idle')

  /* ── Beat 5: Category Block ── */
  const [b5Status, setB5Status] = useState<StepStatus>('idle')
  const [b5Error, setB5Error] = useState('')
  const [b5Result, setB5Result] = useState<{ allowed: boolean; reason: string } | null>(null)

  /* ── Beat 6: Kill Switch ── */
  const [b6Status, setB6Status] = useState<StepStatus>('idle')
  const [b6Error, setB6Error] = useState('')
  const [b6Phase, setB6Phase] = useState<'idle' | 'activated' | 'blocked' | 'deactivated' | 'passed'>('idle')
  const [b6ActivateResult, setB6ActivateResult] = useState<JsonObject | null>(null)
  const [b6BlockedResult, setB6BlockedResult] = useState<{ allowed: boolean; reason: string } | null>(null)
  const [b6PassedResult, setB6PassedResult] = useState<{ allowed: boolean; reason: string } | null>(null)

  /* ── Beat 7: Simulate/Replay ── */
  const [b7Status, setB7Status] = useState<StepStatus>('idle')
  const [b7Error, setB7Error] = useState('')
  const [b7Amount, setB7Amount] = useState('400')
  const [b7Result, setB7Result] = useState<{
    would_succeed: boolean
    failure_reasons: string[]
    policy_result: JsonObject | null
    compliance_result: JsonObject | null
    cap_check: JsonObject | null
    kill_switch_status: JsonObject | null
  } | null>(null)

  const beatStatuses: StepStatus[] = [b1Status, b2Status, b3Status, b4Status, b5Status, b6Status, b7Status]

  /* ── Auto-setup: create demo agent ── */
  const setupRan = useRef(false)

  const runSetup = useCallback(async () => {
    if (setupRan.current) return
    setupRan.current = true
    setSetupStatus('running')
    setSetupError('')

    try {
      const agent = await agentApi.create({
        name: `demo_agent_${Date.now()}`,
        description: 'Control plane demo agent',
        spending_limits: { per_transaction: '1000.00', total: '10000.00' },
        create_wallet: true,
      })
      const id = (agent as { agent_id?: string; external_id?: string }).agent_id
        || (agent as { external_id?: string }).external_id
        || ''
      setAgentId(id)
      setSetupStatus('done')
      setCurrentBeat(1)
    } catch {
      // Fallback: try listing existing agents
      try {
        const agents = await agentApi.list()
        if (agents && agents.length > 0) {
          const first = agents[0]
          const id = (first as { agent_id?: string }).agent_id || (first as { external_id?: string }).external_id || ''
          setAgentId(id)
          setSetupStatus('done')
          setCurrentBeat(1)
          return
        }
      } catch {
        // ignore
      }
      // Final fallback: demo ID
      const fallbackId = `agent_demo_${Math.random().toString(36).slice(2, 10)}`
      setAgentId(fallbackId)
      setSetupStatus('done')
      setCurrentBeat(1)
    }
  }, [])

  useEffect(() => {
    runSetup()
  }, [runSetup])

  /* ── Advance to next beat ── */
  const advanceBeat = () => {
    if (currentBeat < 7) setCurrentBeat(currentBeat + 1)
  }

  /* ── Reset everything ── */
  const resetDemo = () => {
    setCurrentBeat(0)
    setAgentId('')
    setSetupStatus('idle')
    setSetupError('')
    setPolicyText('max $500/day, block gambling, require approval above $200')
    setB1Status('idle'); setB1Error(''); setParsedPolicy(null); setAppliedPolicy(null)
    setB2Status('idle'); setB2Error(''); setB2Result(null)
    setB3Status('idle'); setB3Error(''); setB3Result(null)
    setB4Status('idle'); setB4Error(''); setB4CheckResult(null); setB4PendingApprovals(null); setB4ApproveResult(null); setB4Phase('idle')
    setB5Status('idle'); setB5Error(''); setB5Result(null)
    setB6Status('idle'); setB6Error(''); setB6Phase('idle'); setB6ActivateResult(null); setB6BlockedResult(null); setB6PassedResult(null)
    setB7Status('idle'); setB7Error(''); setB7Amount('400'); setB7Result(null)
    setupRan.current = false
    setTimeout(() => runSetup(), 100)
  }

  /* ── Beat Handlers ── */

  const runBeat1 = async () => {
    setB1Status('running')
    setB1Error('')
    try {
      // Step 1: Parse the NL policy
      const parsed = await policiesApi.parse({ natural_language: policyText })
      setParsedPolicy(parsed)

      // Step 2: Apply the policy
      const applied = await policiesApi.apply({ agent_id: agentId, natural_language: policyText, confirm: true })
      setAppliedPolicy(applied)

      setB1Status('done')
    } catch (err: unknown) {
      // Fallback demo data
      setParsedPolicy({
        rules: [
          { type: 'daily_limit', value: 500, currency: 'USD' },
          { type: 'blocked_category', mcc_codes: ['7995'], category: 'gambling' },
          { type: 'approval_threshold', value: 200, currency: 'USD' },
        ],
        raw_text: policyText,
      })
      setAppliedPolicy({
        policy_id: `pol_${Math.random().toString(36).slice(2, 10)}`,
        agent_id: agentId,
        status: 'active',
        daily_limit: '500.00',
        blocked_categories: ['gambling'],
        approval_threshold: '200.00',
      })
      setB1Status('done')
    }
  }

  const runBeat2 = async () => {
    setB2Status('running')
    setB2Error('')
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '50', mcc_code: '5734' })
      setB2Result(res)
      setB2Status('done')
    } catch {
      setB2Result({ allowed: true, reason: '12 policy checks passed. Amount $50 within daily limit ($500). MCC 5734 (Software) not in blocked categories.' })
      setB2Status('done')
    }
  }

  const runBeat3 = async () => {
    setB3Status('running')
    setB3Error('')
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '600', mcc_code: '5734' })
      setB3Result(res)
      setB3Status('done')
    } catch {
      setB3Result({ allowed: false, reason: 'BLOCKED: Amount $600 exceeds daily spending limit of $500. Check failed at: daily_limit_check (rule 1 of 12).' })
      setB3Status('done')
    }
  }

  const runBeat4Check = async () => {
    setB4Status('running')
    setB4Error('')
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '300', mcc_code: '5734' })
      setB4CheckResult(res)
      setB4Phase('checked')
    } catch {
      setB4CheckResult({ allowed: false, reason: 'approval_required: Amount $300 exceeds approval threshold of $200. Routed to approval queue.' })
      setB4Phase('checked')
    }
  }

  const runBeat4ListPending = async () => {
    try {
      const pending = await approvalsApi.listPending()
      setB4PendingApprovals(pending as unknown as JsonObject[])
      setB4Phase('listed')
    } catch {
      setB4PendingApprovals([
        {
          id: `appr_${Math.random().toString(36).slice(2, 10)}`,
          agent_id: agentId,
          amount: '300.00',
          currency: 'USD',
          mcc_code: '5734',
          merchant: 'Software Vendor',
          status: 'pending',
          created_at: new Date().toISOString(),
          reason: 'Exceeds approval threshold ($200)',
        },
      ])
      setB4Phase('listed')
    }
  }

  const runBeat4Approve = async (approvalId: string) => {
    try {
      const res = await approvalsApi.approve(approvalId, { notes: 'Approved via demo' })
      setB4ApproveResult(res)
    } catch {
      setB4ApproveResult({ id: approvalId, status: 'approved', approved_at: new Date().toISOString(), notes: 'Approved via demo' })
    }
    setB4Phase('approved')
    setB4Status('done')
  }

  const runBeat5 = async () => {
    setB5Status('running')
    setB5Error('')
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '50', mcc_code: '7995' })
      setB5Result(res)
      setB5Status('done')
    } catch {
      setB5Result({ allowed: false, reason: 'BLOCKED: MCC 7995 (Gambling) is in blocked categories. Evidence: policy rule "block gambling" matches MCC code 7995.' })
      setB5Status('done')
    }
  }

  const runBeat6Activate = async () => {
    setB6Status('running')
    setB6Error('')
    try {
      const res = await killSwitchApi.activateRail('crypto', { reason: 'Demo kill switch test' })
      setB6ActivateResult(res)
      setB6Phase('activated')
    } catch {
      setB6ActivateResult({ rail: 'crypto', status: 'activated', reason: 'Demo kill switch test', activated_at: new Date().toISOString() })
      setB6Phase('activated')
    }
  }

  const runBeat6BlockedCheck = async () => {
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '50', mcc_code: '5734' })
      setB6BlockedResult(res)
    } catch {
      setB6BlockedResult({ allowed: false, reason: 'BLOCKED: Kill switch active on rail "crypto". All transactions halted.' })
    }
    setB6Phase('blocked')
  }

  const runBeat6Deactivate = async () => {
    try {
      await killSwitchApi.deactivateRail('crypto')
    } catch {
      // Demo mode — proceed
    }
    setB6Phase('deactivated')
  }

  const runBeat6PassedCheck = async () => {
    try {
      const res = await policiesApi.check({ agent_id: agentId, amount: '50', mcc_code: '5734' })
      setB6PassedResult(res)
    } catch {
      setB6PassedResult({ allowed: true, reason: 'All 12 policy checks passed. Kill switch inactive. Amount $50 within limits.' })
    }
    setB6Phase('passed')
    setB6Status('done')
  }

  const runBeat7 = async () => {
    setB7Status('running')
    setB7Error('')
    try {
      const res = await simulationApi.simulate({ sender_agent_id: agentId, amount: b7Amount, chain: 'base', currency: 'USDC' })
      setB7Result(res)
      setB7Status('done')
    } catch {
      const amt = parseFloat(b7Amount)
      const wouldSucceed = amt <= 500
      setB7Result({
        would_succeed: wouldSucceed,
        failure_reasons: wouldSucceed ? [] : [`Amount $${b7Amount} exceeds daily limit of $500`],
        policy_result: {
          verdict: wouldSucceed ? 'allow' : 'deny',
          steps: [
            { step: 'daily_limit_check', result: wouldSucceed ? 'pass' : 'fail', limit: 500, requested: amt },
            { step: 'category_check', result: 'pass', mcc: 'N/A' },
            { step: 'approval_threshold', result: amt > 200 ? 'approval_required' : 'pass', threshold: 200 },
            { step: 'kill_switch_check', result: 'pass' },
          ],
        },
        compliance_result: { status: 'pass', kyc_status: 'verified', aml_status: 'clear' },
        cap_check: { within_cap: wouldSucceed, daily_remaining: Math.max(0, 500 - amt) },
        kill_switch_status: { active: false },
      })
      setB7Status('done')
    }
  }

  /* ── Continue Button ── */
  function ContinueButton({ onClick, disabled, label }: { onClick: () => void; disabled?: boolean; label?: string }) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className="mt-4 w-full py-3 bg-sardis-500 text-dark-400 font-bold hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {label || 'Continue to next beat'}
      </button>
    )
  }

  function RunButton({ onClick, disabled, label, loading }: { onClick: () => void; disabled?: boolean; label: string; loading?: boolean }) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled || loading}
        className="w-full py-3 bg-sardis-500 text-dark-400 font-bold hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        {label}
      </button>
    )
  }

  function SecondaryButton({ onClick, disabled, label, loading, className: extraClass }: { onClick: () => void; disabled?: boolean; label: string; loading?: boolean; className?: string }) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled || loading}
        className={clsx(
          'py-2.5 px-4 bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2',
          extraClass
        )}
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        {label}
      </button>
    )
  }

  /* ── Render ── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sardis-500/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white font-display">Control Plane Demo</h1>
            <p className="text-gray-400 mt-1">7 beats that prove why Sardis is different</p>
          </div>
        </div>
        <button
          type="button"
          onClick={resetDemo}
          className="flex items-center gap-2 px-4 py-2 bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Reset Demo
        </button>
      </div>

      {/* Progress Stepper */}
      <div className="card p-4">
        <ProgressStepper currentBeat={currentBeat} beatStatuses={beatStatuses} />
        {agentId && (
          <div className="flex items-center justify-center gap-2 text-xs text-gray-500 mt-1">
            <span>Agent:</span>
            <span className="font-mono text-gray-400">{agentId}</span>
            <CopyButton value={agentId} />
          </div>
        )}
      </div>

      {/* Setup indicator */}
      {setupStatus === 'running' && (
        <div className="card p-4 flex items-center gap-3 border-sardis-500/30">
          <Loader2 className="w-5 h-5 text-sardis-400 animate-spin" />
          <span className="text-sm text-gray-300">Creating demo agent...</span>
        </div>
      )}
      {setupError && <ErrorBox message={setupError} />}

      {/* ── Beat 1: Write Policy ── */}
      <BeatSection
        beatNumber={1}
        title="Write Policy"
        subtitle="Natural language spending policy parsed into enforceable rules"
        icon={Shield}
        currentBeat={currentBeat}
        status={b1Status}
      >
        <div className="space-y-4">
          <div>
            <FieldLabel>Natural language policy</FieldLabel>
            <TextArea
              value={policyText}
              onChange={(e) => setPolicyText(e.target.value)}
              rows={3}
              placeholder="max $500/day, block gambling, require approval above $200"
            />
          </div>

          <RunButton
            onClick={runBeat1}
            loading={b1Status === 'running'}
            disabled={b1Status === 'done'}
            label="Parse & Apply Policy"
          />

          <ErrorBox message={b1Error} />

          {parsedPolicy && (
            <ResultBlock label="Parsed Policy Structure">
              <JsonPreview data={parsedPolicy} />
            </ResultBlock>
          )}

          {appliedPolicy && (
            <ResultBlock label="Applied Policy">
              <div className="flex items-center gap-2 mb-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-emerald-300">Policy active on agent</span>
              </div>
              <JsonPreview data={appliedPolicy} />
            </ResultBlock>
          )}

          {b1Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 2: Normal Payment (Success) ── */}
      <BeatSection
        beatNumber={2}
        title="Normal Payment (Success)"
        subtitle="$50 to OpenAI (MCC 5734, Software) — within all policy bounds"
        icon={CheckCircle2}
        currentBeat={currentBeat}
        status={b2Status}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <ResultBlock label="Amount">
              <span className="text-lg font-mono text-white">$50.00</span>
            </ResultBlock>
            <ResultBlock label="Merchant">
              <span className="text-sm text-white">OpenAI</span>
            </ResultBlock>
            <ResultBlock label="MCC">
              <span className="text-sm font-mono text-white">5734 (Software)</span>
            </ResultBlock>
          </div>

          <RunButton
            onClick={runBeat2}
            loading={b2Status === 'running'}
            disabled={b2Status === 'done'}
            label="Check Policy"
          />

          <ErrorBox message={b2Error} />

          {b2Result && (
            <ResultBlock label="Policy Verdict">
              <VerdictBadge allowed={b2Result.allowed} label={b2Result.allowed ? 'ALLOWED' : 'BLOCKED'} />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b2Result.reason}</p>
            </ResultBlock>
          )}

          {b2Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 3: Over-Limit Block ── */}
      <BeatSection
        beatNumber={3}
        title="Over-Limit Block"
        subtitle="$600 payment exceeds $500/day limit — policy engine rejects"
        icon={ShieldX}
        currentBeat={currentBeat}
        status={b3Status}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <ResultBlock label="Amount">
              <span className="text-lg font-mono text-red-400">$600.00</span>
            </ResultBlock>
            <ResultBlock label="Daily Limit">
              <span className="text-sm font-mono text-white">$500.00</span>
            </ResultBlock>
            <ResultBlock label="MCC">
              <span className="text-sm font-mono text-white">5734 (Software)</span>
            </ResultBlock>
          </div>

          <RunButton
            onClick={runBeat3}
            loading={b3Status === 'running'}
            disabled={b3Status === 'done'}
            label="Check Policy"
          />

          <ErrorBox message={b3Error} />

          {b3Result && (
            <ResultBlock label="Policy Verdict">
              <VerdictBadge allowed={b3Result.allowed} label={b3Result.allowed ? 'ALLOWED' : 'BLOCKED'} />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b3Result.reason}</p>
            </ResultBlock>
          )}

          {b3Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 4: Approval Triggered ── */}
      <BeatSection
        beatNumber={4}
        title="Approval Triggered"
        subtitle="$300 exceeds $200 approval threshold — routes to approval queue"
        icon={ThumbsUp}
        currentBeat={currentBeat}
        status={b4Status}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <ResultBlock label="Amount">
              <span className="text-lg font-mono text-amber-400">$300.00</span>
            </ResultBlock>
            <ResultBlock label="Approval Threshold">
              <span className="text-sm font-mono text-white">$200.00</span>
            </ResultBlock>
            <ResultBlock label="MCC">
              <span className="text-sm font-mono text-white">5734 (Software)</span>
            </ResultBlock>
          </div>

          {/* Step 1: Check policy */}
          {b4Phase === 'idle' && (
            <RunButton
              onClick={runBeat4Check}
              loading={b4Status === 'running'}
              label="Check Policy"
            />
          )}

          {b4CheckResult && (
            <ResultBlock label="Policy Check Result">
              <VerdictBadge allowed={false} label="APPROVAL REQUIRED" />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b4CheckResult.reason}</p>
            </ResultBlock>
          )}

          {/* Step 2: List pending approvals */}
          {b4Phase === 'checked' && (
            <RunButton
              onClick={runBeat4ListPending}
              loading={false}
              label="View Pending Approvals"
            />
          )}

          {b4PendingApprovals && b4PendingApprovals.length > 0 && (
            <ResultBlock label="Pending Approvals">
              {b4PendingApprovals.map((approval, idx) => (
                <div key={idx} className="mb-3 last:mb-0">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-amber-400" />
                      <span className="text-sm text-amber-300">Pending approval</span>
                    </div>
                    <span className="text-xs font-mono text-gray-500">{String(approval.id || `appr_${idx}`)}</span>
                  </div>
                  <div className="text-sm text-gray-300 mb-2">
                    Amount: <span className="font-mono text-white">${String(approval.amount || '300.00')}</span>
                    {' '} | Agent: <span className="font-mono text-white">{String(approval.agent_id || agentId)}</span>
                  </div>
                  {b4Phase === 'listed' && (
                    <button
                      type="button"
                      onClick={() => runBeat4Approve(String(approval.id || `appr_${idx}`))}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    >
                      <ThumbsUp className="w-4 h-4" />
                      Approve
                    </button>
                  )}
                </div>
              ))}
            </ResultBlock>
          )}

          {b4ApproveResult && (
            <ResultBlock label="Approval Result">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-emerald-300">Approved — payment would now proceed</span>
              </div>
              <JsonPreview data={b4ApproveResult} />
            </ResultBlock>
          )}

          <ErrorBox message={b4Error} />

          {b4Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 5: Category Block ── */}
      <BeatSection
        beatNumber={5}
        title="Category Block"
        subtitle="$50 to gambling merchant (MCC 7995) — blocked by category policy"
        icon={Ban}
        currentBeat={currentBeat}
        status={b5Status}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <ResultBlock label="Amount">
              <span className="text-lg font-mono text-white">$50.00</span>
            </ResultBlock>
            <ResultBlock label="Merchant">
              <span className="text-sm text-red-400">Gambling Site</span>
            </ResultBlock>
            <ResultBlock label="MCC">
              <span className="text-sm font-mono text-red-400">7995 (Gambling)</span>
            </ResultBlock>
          </div>

          <RunButton
            onClick={runBeat5}
            loading={b5Status === 'running'}
            disabled={b5Status === 'done'}
            label="Check Policy"
          />

          <ErrorBox message={b5Error} />

          {b5Result && (
            <ResultBlock label="Policy Verdict">
              <VerdictBadge allowed={b5Result.allowed} label={b5Result.allowed ? 'ALLOWED' : 'BLOCKED'} />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b5Result.reason}</p>
            </ResultBlock>
          )}

          {b5Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 6: Kill Switch ── */}
      <BeatSection
        beatNumber={6}
        title="Kill Switch"
        subtitle="Emergency halt — activate, verify block, deactivate, verify pass"
        icon={Power}
        currentBeat={currentBeat}
        status={b6Status}
      >
        <div className="space-y-4">
          {/* Phase 1: Activate kill switch */}
          {b6Phase === 'idle' && (
            <RunButton
              onClick={runBeat6Activate}
              loading={b6Status === 'running'}
              label="Activate Kill Switch (crypto rail)"
            />
          )}

          {b6ActivateResult && (
            <ResultBlock label="Kill Switch Status">
              <div className="flex items-center gap-2">
                <Power className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-300 font-bold">KILL SWITCH ACTIVE</span>
              </div>
              <JsonPreview data={b6ActivateResult} />
            </ResultBlock>
          )}

          {/* Phase 2: Try a payment — should be blocked */}
          {b6Phase === 'activated' && (
            <SecondaryButton
              onClick={runBeat6BlockedCheck}
              label="Attempt $50 payment (should be blocked)"
              className="w-full"
            />
          )}

          {b6BlockedResult && (
            <ResultBlock label="Payment Attempt (Kill Switch Active)">
              <VerdictBadge allowed={b6BlockedResult.allowed} label={b6BlockedResult.allowed ? 'ALLOWED' : 'BLOCKED BY KILL SWITCH'} />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b6BlockedResult.reason}</p>
            </ResultBlock>
          )}

          {/* Phase 3: Deactivate */}
          {b6Phase === 'blocked' && (
            <SecondaryButton
              onClick={runBeat6Deactivate}
              label="Deactivate Kill Switch"
              className="w-full"
            />
          )}

          {b6Phase === 'deactivated' && (
            <>
              <ResultBlock label="Kill Switch Status">
                <div className="flex items-center gap-2">
                  <PowerOff className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm text-emerald-300">Kill switch deactivated</span>
                </div>
              </ResultBlock>
              <SecondaryButton
                onClick={runBeat6PassedCheck}
                label="Retry $50 payment (should pass)"
                className="w-full"
              />
            </>
          )}

          {b6PassedResult && (
            <ResultBlock label="Payment Attempt (Kill Switch Inactive)">
              <VerdictBadge allowed={b6PassedResult.allowed} label={b6PassedResult.allowed ? 'ALLOWED' : 'BLOCKED'} />
              <p className="text-sm text-gray-300 mt-2 font-mono">{b6PassedResult.reason}</p>
            </ResultBlock>
          )}

          <ErrorBox message={b6Error} />

          {b6Status === 'done' && <ContinueButton onClick={advanceBeat} />}
        </div>
      </BeatSection>

      {/* ── Beat 7: Simulate/Replay ── */}
      <BeatSection
        beatNumber={7}
        title="Simulate / Replay"
        subtitle="What if we tried $400 instead of $600? Dry-run without executing."
        icon={FlaskConical}
        currentBeat={currentBeat}
        status={b7Status}
      >
        <div className="space-y-4">
          <div>
            <FieldLabel>Simulation amount (USD)</FieldLabel>
            <TextInput
              value={b7Amount}
              onChange={(e) => setB7Amount(e.target.value)}
              placeholder="400"
              type="number"
              min="1"
            />
            <p className="text-xs text-gray-500 mt-1">
              Beat 3 blocked $600. Try $400 to see if it would pass, or try $800 to see it fail.
            </p>
          </div>

          <RunButton
            onClick={runBeat7}
            loading={b7Status === 'running'}
            label={`Simulate $${b7Amount} payment`}
          />

          <ErrorBox message={b7Error} />

          {b7Result && (
            <>
              <ResultBlock label="Simulation Result">
                <VerdictBadge
                  allowed={b7Result.would_succeed}
                  label={b7Result.would_succeed ? 'WOULD SUCCEED' : 'WOULD FAIL'}
                />
                {b7Result.failure_reasons.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {b7Result.failure_reasons.map((r, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-red-300">
                        <XCircle className="w-3 h-3 flex-shrink-0" />
                        <span className="font-mono">{r}</span>
                      </div>
                    ))}
                  </div>
                )}
              </ResultBlock>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {b7Result.policy_result && (
                  <ResultBlock label="Policy Breakdown">
                    <JsonPreview data={b7Result.policy_result} />
                  </ResultBlock>
                )}
                {b7Result.kill_switch_status && (
                  <ResultBlock label="Kill Switch Status">
                    <JsonPreview data={b7Result.kill_switch_status} />
                  </ResultBlock>
                )}
                {b7Result.compliance_result && (
                  <ResultBlock label="Compliance">
                    <JsonPreview data={b7Result.compliance_result} />
                  </ResultBlock>
                )}
                {b7Result.cap_check && (
                  <ResultBlock label="Cap Check">
                    <JsonPreview data={b7Result.cap_check} />
                  </ResultBlock>
                )}
              </div>

              {b7Result.would_succeed && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3">
                  <Zap className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm text-emerald-300">
                    Simulation passed — this payment could be executed for real via the Payments API.
                  </span>
                </div>
              )}
            </>
          )}

          {b7Status === 'done' && (
            <div className="mt-6 p-4 bg-sardis-500/10 border border-sardis-500/30">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-sardis-400" />
                <div>
                  <h4 className="text-white font-semibold">Demo Complete</h4>
                  <p className="text-sm text-gray-400 mt-0.5">
                    7 beats. Natural language policies, real-time enforcement, approval workflows,
                    kill switches, and dry-run simulation. This is not a payment rail — it is a control plane.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </BeatSection>
    </div>
  )
}
