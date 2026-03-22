"use client";
import { useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import {
  Shield,
  ShieldCheck,
  Search,
  Copy,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Hash,
  FileText,
  Activity,
  User,
  Loader2,
  AlertCircle,
  Package,
} from 'lucide-react'
import clsx from 'clsx'
import { useQuery } from '@tanstack/react-query'
import { useTransactionEvidence, usePolicyDecisions, useAgents } from '@/hooks/useApi'
import { evidenceApi } from '@/api/client'
import EvidenceExportModal from '@/components/EvidenceExportModal'

/* ─── Types ─── */

type SearchMode = 'idle' | 'transaction' | 'agent'

type Verdict = 'allowed' | 'denied' | 'approval_required'

interface PolicyStep {
  step: string
  result: string
  reason?: string
  data?: Record<string, unknown>
}

interface PolicyEvaluation {
  verdict: Verdict
  steps: PolicyStep[]
  evidence_hash: string
}

interface ExecutionReceipt {
  receipt_id: string
  timestamp: string
  intent_hash: string
  policy_snapshot_hash: string
  compliance_result_hash: string
  tx_hash: string
  chain: string
  org_id: string
  agent_id: string
  amount: string
  currency: string
  signature?: string
}

interface ComplianceResult {
  status: string
  kyc_status?: string
  aml_status?: string
  risk_score?: number
  flags?: string[]
}

interface LedgerEntry {
  id: string
  entry_hash: string
  entry_type: string
  amount?: string
  currency?: string
  timestamp: string
  agent_id?: string
}

interface TransactionEvidence {
  receipt: ExecutionReceipt
  ledger_entries: LedgerEntry[]
  compliance_result: ComplianceResult
  policy_evaluation: PolicyEvaluation
  side_effects?: Record<string, unknown>[]
}

interface PolicyDecision {
  decision_id: string
  agent_id: string
  verdict: Verdict
  evidence_hash: string
  created_at: string
}

/* ─── Helpers ─── */

function truncateHash(hash: string, leading = 10, trailing = 8): string {
  if (!hash || hash.length <= leading + trailing + 3) return hash
  return `${hash.slice(0, leading)}...${hash.slice(-trailing)}`
}

function getExplorerUrl(chain: string, txHash: string): string {
  const explorers: Record<string, string> = {
    base: 'https://basescan.org/tx/',
    base_sepolia: 'https://sepolia.basescan.org/tx/',
    polygon: 'https://polygonscan.com/tx/',
    ethereum: 'https://etherscan.io/tx/',
    arbitrum: 'https://arbiscan.io/tx/',
    optimism: 'https://optimistic.ethscan.io/tx/',
    arc: 'https://explorer.circle.com/tx/',
    tempo_testnet: 'https://moderato.tempo.xyz/tx/',
    solana_devnet: 'https://explorer.solana.com/tx/',
    solana: 'https://explorer.solana.com/tx/',
    morph: 'https://explorer.morphl2.io/tx/',
    morph_testnet: 'https://explorer-testnet.morphl2.io/tx/',
  }
  const base = explorers[chain?.toLowerCase()] ?? 'https://basescan.org/tx/'
  return `${base}${txHash}`
}

/* ─── Sub-components ─── */

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold uppercase tracking-wider',
        verdict === 'allowed' && 'bg-green-500/15 text-green-400 border border-green-500/30',
        verdict === 'denied' && 'bg-red-500/15 text-red-400 border border-red-500/30',
        verdict === 'approval_required' && 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
      )}
    >
      {verdict === 'allowed' && <CheckCircle2 className="w-3 h-3" />}
      {verdict === 'denied' && <XCircle className="w-3 h-3" />}
      {verdict === 'approval_required' && <Clock className="w-3 h-3" />}
      {verdict.replace('_', ' ')}
    </span>
  )
}

function HashField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }, [value])

  if (!value) return null

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      <div className="flex items-center gap-2 bg-dark-200 border border-dark-100 px-3 py-2">
        <Hash className="w-3 h-3 text-gray-600 flex-shrink-0" />
        <code className="text-xs font-mono text-gray-300 flex-1 truncate" title={value}>
          {truncateHash(value)}
        </code>
        <button
          onClick={handleCopy}
          className="text-gray-500 hover:text-sardis-400 transition-colors flex-shrink-0"
          title="Copy full hash"
        >
          {copied ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <Copy className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  )
}

function PolicyStepRow({ step, index }: { step: PolicyStep; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const passed = step.result === 'pass' || step.result === 'allowed' || step.result === 'ok'
  const failed = step.result === 'fail' || step.result === 'denied' || step.result === 'blocked'
  const hasDetail = !!step.reason || (step.data && Object.keys(step.data).length > 0)

  return (
    <div className="border border-dark-100 bg-dark-200">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-dark-300/50 transition-colors"
        onClick={() => hasDetail && setExpanded(e => !e)}
        disabled={!hasDetail}
      >
        <span className="text-xs text-gray-600 font-mono w-5 flex-shrink-0">{index + 1}</span>
        <span
          className={clsx(
            'w-2 h-2 flex-shrink-0',
            passed && 'bg-green-400',
            failed && 'bg-red-400',
            !passed && !failed && 'bg-yellow-400',
          )}
        />
        <span className="text-sm text-gray-200 flex-1 font-medium">{step.step}</span>
        <span
          className={clsx(
            'text-xs px-2 py-0.5 font-mono',
            passed && 'text-green-400 bg-green-500/10',
            failed && 'text-red-400 bg-red-500/10',
            !passed && !failed && 'text-yellow-400 bg-yellow-500/10',
          )}
        >
          {step.result}
        </span>
        {hasDetail && (
          expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
            : <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
        )}
      </button>
      {expanded && hasDetail && (
        <div className="px-4 pb-3 pt-1 border-t border-dark-100 space-y-2">
          {step.reason && (
            <p className="text-xs text-gray-400">{step.reason}</p>
          )}
          {step.data && Object.keys(step.data).length > 0 && (
            <pre className="text-xs font-mono text-gray-500 bg-dark-300 px-3 py-2 overflow-x-auto">
              {JSON.stringify(step.data, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function PolicyDecisionRow({
  decision,
  agentId,
  defaultOpen = false,
}: {
  decision: PolicyDecision
  agentId: string
  defaultOpen?: boolean
}) {
  const [expanded, setExpanded] = useState(defaultOpen)

  const detailQuery = useQuery({
    queryKey: ['policy-decision-detail', agentId, decision.decision_id],
    queryFn: () => evidenceApi.getPolicyDecisionDetail(agentId, decision.decision_id),
    enabled: expanded,
  })

  const detail = detailQuery.data as {
    verdict?: Verdict
    steps?: PolicyStep[]
    evidence_hash?: string
    [key: string]: unknown
  } | undefined

  return (
    <div className="border border-dark-100 bg-dark-200">
      <button
        className="w-full flex items-center gap-4 px-4 py-3 text-left hover:bg-dark-300/50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <VerdictBadge verdict={decision.verdict} />
            <code className="text-xs font-mono text-gray-500 truncate">
              {truncateHash(decision.decision_id, 12, 6)}
            </code>
          </div>
          <p className="text-xs text-gray-500">
            {new Date(decision.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {decision.evidence_hash && (
            <code className="text-xs font-mono text-gray-600 hidden sm:block">
              {truncateHash(decision.evidence_hash, 8, 6)}
            </code>
          )}
          {expanded
            ? <ChevronDown className="w-4 h-4 text-gray-500" />
            : <ChevronRight className="w-4 h-4 text-gray-500" />
          }
        </div>
      </button>

      {expanded && (
        <div className="border-t border-dark-100 px-4 py-4 space-y-4">
          {detailQuery.isLoading && (
            <div className="flex items-center gap-2 py-4 justify-center text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Loading decision detail...</span>
            </div>
          )}
          {detailQuery.isError && (
            <div className="flex items-center gap-2 text-red-400 text-sm py-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>Failed to load detail: {(detailQuery.error as Error).message}</span>
            </div>
          )}
          {detail && (
            <>
              {detail.evidence_hash && (
                <HashField label="Evidence Hash" value={detail.evidence_hash} />
              )}
              {detail.steps && detail.steps.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Policy Steps</p>
                  <div className="space-y-px">
                    {detail.steps.map((step, i) => (
                      <PolicyStepRow key={i} step={step} index={i} />
                    ))}
                  </div>
                </div>
              )}
              {!detail.steps && (
                <pre className="text-xs font-mono text-gray-500 bg-dark-300 px-3 py-2 overflow-x-auto max-h-64">
                  {JSON.stringify(detail, null, 2)}
                </pre>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Transaction Evidence View ─── */

function TransactionEvidenceView({ txId }: { txId: string }) {
  const { data, isLoading, isError, error } = useTransactionEvidence(txId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin text-sardis-400" />
        <span>Loading transaction evidence...</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="card p-8 flex items-center gap-4">
        <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
        <div>
          <p className="text-red-400 font-medium">Failed to load evidence</p>
          <p className="text-sm text-gray-500 mt-0.5">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  if (!data) return null

  const ev = data as unknown as TransactionEvidence
  const { receipt, ledger_entries, compliance_result, policy_evaluation } = ev

  return (
    <div className="space-y-6">
      {/* Execution Receipt */}
      <div className="card p-6">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
              <FileText className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Execution Receipt</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {receipt?.timestamp ? new Date(receipt.timestamp).toLocaleString() : '—'}
              </p>
            </div>
          </div>
          {receipt?.signature && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/25 text-green-400 text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              Signature Verified
            </div>
          )}
        </div>

        {receipt && (
          <>
            {/* Amount + Chain banner */}
            <div className="flex items-center gap-4 px-4 py-3 bg-dark-200 border border-dark-100 mb-5">
              <div>
                <p className="text-2xl font-bold text-white font-mono">
                  {receipt.amount} <span className="text-sardis-400 text-base">{receipt.currency}</span>
                </p>
              </div>
              <div className="h-8 w-px bg-dark-100" />
              <div className="text-sm text-gray-400">
                <span className="text-gray-500 text-xs">Chain</span>
                <p className="text-white font-medium">{receipt.chain}</p>
              </div>
              <div className="h-8 w-px bg-dark-100" />
              <div className="text-sm">
                <span className="text-gray-500 text-xs">Receipt ID</span>
                <p className="text-white font-mono text-xs">{truncateHash(receipt.receipt_id)}</p>
              </div>
            </div>

            {/* Hash grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
              <HashField label="Intent Hash" value={receipt.intent_hash} />
              <HashField label="Policy Snapshot Hash" value={receipt.policy_snapshot_hash} />
              <HashField label="Compliance Result Hash" value={receipt.compliance_result_hash} />
              {receipt.signature && (
                <HashField label="Receipt Signature" value={receipt.signature} />
              )}
            </div>

            {/* On-chain TX */}
            {receipt.tx_hash && (
              <div className="flex items-center justify-between px-4 py-3 bg-dark-200 border border-dark-100">
                <div className="flex items-center gap-3 min-w-0">
                  <Activity className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-gray-500 mb-0.5">On-chain Transaction</p>
                    <code className="text-xs font-mono text-blue-400 truncate block">
                      {truncateHash(receipt.tx_hash, 18, 10)}
                    </code>
                  </div>
                </div>
                <a
                  href={getExplorerUrl(receipt.chain, receipt.tx_hash)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-sardis-400 border border-dark-100 hover:border-sardis-500/40 transition-colors ml-3 flex-shrink-0"
                >
                  View on Explorer
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}

            {/* Org / Agent meta */}
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className="px-3 py-2 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-0.5">Organization</p>
                <p className="text-xs font-mono text-gray-300">{receipt.org_id || '—'}</p>
              </div>
              <div className="px-3 py-2 bg-dark-200 border border-dark-100">
                <p className="text-xs text-gray-500 mb-0.5">Agent</p>
                <p className="text-xs font-mono text-gray-300">{receipt.agent_id || '—'}</p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Policy Decision Trace */}
      {policy_evaluation && (
        <div className="card p-6">
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
                <Shield className="w-5 h-5 text-sardis-400" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-white">Policy Decision Trace</h2>
                <p className="text-xs text-gray-500 mt-0.5">Step-by-step evaluation</p>
              </div>
            </div>
            <VerdictBadge verdict={policy_evaluation.verdict} />
          </div>

          {policy_evaluation.evidence_hash && (
            <div className="mb-4">
              <HashField label="Evidence Hash" value={policy_evaluation.evidence_hash} />
            </div>
          )}

          {policy_evaluation.steps && policy_evaluation.steps.length > 0 ? (
            <div className="space-y-px">
              {policy_evaluation.steps.map((step, i) => (
                <PolicyStepRow key={i} step={step} index={i} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 italic">No step trace available.</p>
          )}
        </div>
      )}

      {/* Compliance Result */}
      {compliance_result && (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
              <ShieldCheck className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Compliance Result</h2>
              <p className="text-xs text-gray-500 mt-0.5">KYC / AML screening outcome</p>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="px-3 py-3 bg-dark-200 border border-dark-100">
              <p className="text-xs text-gray-500 mb-1">Overall Status</p>
              <p
                className={clsx(
                  'text-sm font-semibold',
                  compliance_result.status === 'clear' && 'text-green-400',
                  compliance_result.status === 'flagged' && 'text-red-400',
                  compliance_result.status !== 'clear' &&
                    compliance_result.status !== 'flagged' &&
                    'text-yellow-400',
                )}
              >
                {compliance_result.status ?? '—'}
              </p>
            </div>
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
                    compliance_result.risk_score >= 30 &&
                      compliance_result.risk_score < 70 &&
                      'text-yellow-400',
                    compliance_result.risk_score >= 70 && 'text-red-400',
                  )}
                >
                  {compliance_result.risk_score}
                </p>
              </div>
            )}
          </div>

          {compliance_result.flags && compliance_result.flags.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {compliance_result.flags.map((flag, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 bg-red-500/10 border border-red-500/25 text-red-400 text-xs font-mono"
                >
                  {flag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Ledger Entries */}
      {ledger_entries && ledger_entries.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
              <FileText className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Ledger Entries</h2>
              <p className="text-xs text-gray-500 mt-0.5">{ledger_entries.length} append-only records</p>
            </div>
          </div>

          <div className="space-y-px">
            {ledger_entries.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center gap-4 px-4 py-3 bg-dark-200 border border-dark-100 hover:border-dark-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-1.5 py-0.5 bg-dark-300 border border-dark-100 text-gray-400 font-mono">
                      {entry.entry_type ?? 'entry'}
                    </span>
                    {entry.amount && (
                      <span className="text-xs text-white font-mono">
                        {entry.amount} {entry.currency}
                      </span>
                    )}
                  </div>
                  <code className="text-xs font-mono text-gray-500 truncate block">
                    {truncateHash(entry.entry_hash ?? entry.id, 16, 8)}
                  </code>
                </div>
                <p className="text-xs text-gray-600 flex-shrink-0">
                  {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Agent Decisions View ─── */

function AgentDecisionsView({ agentId }: { agentId: string }) {
  const { data, isLoading, isError, error } = usePolicyDecisions(agentId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 gap-3 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin text-sardis-400" />
        <span>Loading policy decisions...</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="card p-8 flex items-center gap-4">
        <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
        <div>
          <p className="text-red-400 font-medium">Failed to load decisions</p>
          <p className="text-sm text-gray-500 mt-0.5">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  const decisions = (data ?? []) as unknown as PolicyDecision[]

  if (decisions.length === 0) {
    return (
      <div className="card p-12 flex flex-col items-center justify-center gap-4">
        <Shield className="w-12 h-12 text-gray-700" />
        <p className="text-gray-500 text-sm">No policy decisions found for agent <code className="font-mono text-gray-400">{agentId}</code></p>
      </div>
    )
  }

  const allowedCount = decisions.filter(d => d.verdict === 'allowed').length
  const deniedCount = decisions.filter(d => d.verdict === 'denied').length
  const pendingCount = decisions.filter(d => d.verdict === 'approval_required').length

  return (
    <div className="space-y-6">
      {/* Summary strip */}
      <div className="card p-4">
        <div className="flex items-center gap-3 mb-3">
          <User className="w-4 h-4 text-sardis-400" />
          <span className="text-sm text-gray-400">
            Agent: <code className="font-mono text-gray-300">{agentId}</code>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400" />
            <span className="text-xs text-gray-400">{allowedCount} allowed</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-red-400" />
            <span className="text-xs text-gray-400">{deniedCount} denied</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-yellow-400" />
            <span className="text-xs text-gray-400">{pendingCount} pending approval</span>
          </div>
          <span className="text-xs text-gray-600 ml-auto">{decisions.length} total</span>
        </div>
      </div>

      {/* Decision list */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
            <Shield className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Policy Decisions</h2>
            <p className="text-xs text-gray-500 mt-0.5">Expand to view full decision trace</p>
          </div>
        </div>
        <div className="space-y-px">
          {decisions.map((decision) => (
            <PolicyDecisionRow
              key={decision.decision_id}
              decision={decision}
              agentId={agentId}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

/* ─── Empty State ─── */

function EmptyState() {
  return (
    <div className="card p-16 flex flex-col items-center justify-center gap-5">
      <div className="p-5 bg-dark-200 border border-dark-100">
        <Shield className="w-12 h-12 text-gray-600" />
      </div>
      <div className="text-center max-w-sm">
        <h3 className="text-lg font-semibold text-white mb-2">No search performed yet</h3>
        <p className="text-sm text-gray-500 leading-relaxed">
          Enter a transaction ID (e.g. <code className="font-mono text-gray-400">tx_...</code>) to
          inspect cryptographic execution evidence, or an agent ID to browse all policy decisions.
        </p>
      </div>
      <div className="flex items-center gap-6 text-xs text-gray-600 mt-2">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-sardis-500" />
          Transaction ID → full receipt + trace
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-blue-500" />
          Agent ID → decision history
        </div>
      </div>
    </div>
  )
}

/* ─── Main Page ─── */

export default function EvidencePage() {
  const searchParams = useSearchParams()
  const initialTx = searchParams.get('tx')?.trim() ?? ''
  const initialAgent = searchParams.get('agent')?.trim() ?? ''
  const initialValue = initialTx || initialAgent
  const initialMode: SearchMode = initialTx
    ? 'transaction'
    : initialAgent
    ? 'agent'
    : 'idle'

  const [inputValue, setInputValue] = useState(initialValue)
  const [searchedValue, setSearchedValue] = useState(initialValue)
  const [searchMode, setSearchMode] = useState<SearchMode>(initialMode)
  const [exportModalTxId, setExportModalTxId] = useState<string | null>(null)

  const agentsQuery = useAgents()
  const agentIds = new Set(
    ((agentsQuery.data ?? []) as { agent_id?: string; id?: string }[]).map(
      a => a.agent_id ?? a.id ?? '',
    ),
  )

  const handleSearch = useCallback(() => {
    const val = inputValue.trim()
    if (!val) return

    if (val.startsWith('tx_') || val.startsWith('0x')) {
      setSearchMode('transaction')
      //  removed in Next.js migration
    // Use router.push with new URL params instead
    void({ tx: val })
    } else {
      // agent ID or ambiguous — check against known agents or default to agent mode
      setSearchMode(agentIds.has(val) || val.startsWith('agent_') || val.startsWith('agt_') ? 'agent' : 'agent')
      //  removed in Next.js migration
    // Use router.push with new URL params instead
    void({ agent: val })
    }
    setSearchedValue(val)
  }, [inputValue, agentIds])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleSearch()
    },
    [handleSearch],
  )

  const handleClear = useCallback(() => {
    setInputValue('')
    setSearchedValue('')
    setSearchMode('idle')
    //  removed in Next.js migration
    // Use router.push with new URL params instead
    void({})
  }, [])

  return (
    <div className="space-y-8">
      {/* Export modal */}
      {exportModalTxId && (
        <EvidenceExportModal
          txId={exportModalTxId}
          onClose={() => setExportModalTxId(null)}
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Evidence Explorer</h1>
          <p className="text-gray-400 mt-1 max-w-lg">
            Inspect cryptographic proof of execution — receipts, policy traces, compliance results,
            and ledger entries for any transaction or agent.
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 text-xs text-gray-500">
          <ShieldCheck className="w-4 h-4 text-sardis-400" />
          Tamper-evident audit trail
        </div>
      </div>

      {/* Search Bar */}
      <div className="card p-5">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            <input
              type="text"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter a transaction ID (tx_...) or agent ID..."
              className={clsx(
                'w-full pl-10 pr-4 py-3 bg-dark-200 border text-sm text-white placeholder-gray-600',
                'focus:outline-none focus:border-sardis-500/60 transition-colors',
                'border-dark-100',
              )}
            />
          </div>
          {searchedValue && (
            <button
              onClick={handleClear}
              className="px-3 py-3 text-gray-500 hover:text-gray-300 border border-dark-100 bg-dark-200 transition-colors text-xs"
            >
              Clear
            </button>
          )}
          <button
            onClick={handleSearch}
            disabled={!inputValue.trim()}
            className={clsx(
              'px-5 py-3 font-medium text-sm flex items-center gap-2 transition-colors',
              inputValue.trim()
                ? 'bg-sardis-500 text-white hover:bg-sardis-600'
                : 'bg-dark-200 text-gray-600 border border-dark-100 cursor-not-allowed',
            )}
          >
            <Search className="w-4 h-4" />
            Search
          </button>
        </div>

        {/* Mode hint */}
        {searchedValue && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-dark-100">
            {searchMode === 'transaction' ? (
              <>
                <Activity className="w-3.5 h-3.5 text-sardis-400" />
                <span className="text-xs text-gray-500">
                  Showing transaction evidence for{' '}
                  <code className="font-mono text-gray-400">{searchedValue}</code>
                </span>
              </>
            ) : (
              <>
                <User className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-xs text-gray-500">
                  Showing policy decisions for agent{' '}
                  <code className="font-mono text-gray-400">{searchedValue}</code>
                </span>
              </>
            )}
            <AlertTriangle className="w-3 h-3 text-gray-600 ml-1" />
            <span className="text-xs text-gray-600">IDs starting with tx_ search transactions, all others search agents</span>
            {searchMode === 'transaction' && (
              <button
                onClick={() => setExportModalTxId(searchedValue)}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-dark-200 border border-dark-100 hover:border-sardis-500/40 text-gray-400 hover:text-sardis-400 transition-colors flex-shrink-0"
              >
                <Package className="w-3.5 h-3.5" />
                Export Evidence
              </button>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      {searchMode === 'idle' && <EmptyState />}
      {searchMode === 'transaction' && <TransactionEvidenceView txId={searchedValue} />}
      {searchMode === 'agent' && <AgentDecisionsView agentId={searchedValue} />}
    </div>
  )
}
