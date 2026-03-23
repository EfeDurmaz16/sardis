import { useState } from 'react'
import {
  ArrowsClockwise,
  CaretDown,
  CaretRight,
  ChartBar,
  Gear,
  Lightning,
  Pulse,
  ShieldSlash,
  ShieldWarning,
  Sliders,
  SpinnerGap,
  Warning,
  XCircle,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'
import { useAnomalyEvents, useAnomalyConfig, useUpdateAnomalyConfig, useAssessRisk } from '../hooks/useApi'

/* ─── Types ─── */

type JsonObject = Record<string, unknown>

interface AnomalySignal {
  name: string
  score: number
  weight: number
  description?: string
}

interface AnomalyEvent {
  event_id?: string
  id?: string
  agent_id?: string
  agent?: string
  overall_score?: number
  score?: number
  action?: string
  signals?: AnomalySignal[]
  signal_scores?: Record<string, number>
  created_at?: string
  timestamp?: string
  metadata?: Record<string, unknown>
}

/* ─── Helpers ─── */

function scoreColor(score: number): string {
  if (score < 0.3) return 'text-sardis-400'
  if (score < 0.6) return 'text-yellow-400'
  if (score < 0.8) return 'text-orange-400'
  return 'text-red-400'
}

function scoreBg(score: number): string {
  if (score < 0.3) return 'bg-sardis-500'
  if (score < 0.6) return 'bg-yellow-400'
  if (score < 0.8) return 'bg-orange-400'
  return 'bg-red-400'
}

function scoreBorder(score: number): string {
  if (score < 0.3) return 'border-sardis-500/30 bg-sardis-500/5'
  if (score < 0.6) return 'border-yellow-400/30 bg-yellow-400/5'
  if (score < 0.8) return 'border-orange-400/30 bg-orange-400/5'
  return 'border-red-400/30 bg-red-400/5'
}

function formatTimeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.floor(diffHr / 24)}d ago`
}

function normalizeEvent(raw: JsonObject): AnomalyEvent {
  return raw as unknown as AnomalyEvent
}

function getScore(ev: AnomalyEvent): number {
  return ev.overall_score ?? ev.score ?? 0
}

function getTimestamp(ev: AnomalyEvent): string | undefined {
  return ev.created_at ?? ev.timestamp
}

function getAgentId(ev: AnomalyEvent): string {
  return ev.agent_id ?? ev.agent ?? '—'
}

function getEventId(ev: AnomalyEvent): string {
  return ev.event_id ?? ev.id ?? Math.random().toString(36).slice(2)
}

function normalizeSignals(ev: AnomalyEvent): AnomalySignal[] {
  if (Array.isArray(ev.signals) && ev.signals.length > 0) return ev.signals
  if (ev.signal_scores && typeof ev.signal_scores === 'object') {
    return Object.entries(ev.signal_scores).map(([name, score]) => ({
      name,
      score: typeof score === 'number' ? score : 0,
      weight: 1,
    }))
  }
  return []
}

/* ─── Action Badge ─── */

function ActionBadge({ action }: { action?: string }) {
  const upper = (action ?? '').toUpperCase()
  const isKill = upper === 'KILL_SWITCH'
  const isFrozen = upper === 'FREEZE_AGENT'
  const isApproval = upper === 'REQUIRE_APPROVAL'
  const isFlag = upper === 'FLAG'
  const isAllow = upper === 'ALLOW'

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider border font-mono',
        isKill && 'bg-red-500/20 text-red-400 border-red-500/40',
        isFrozen && 'bg-red-500/15 text-red-400 border-red-500/30',
        isApproval && 'bg-orange-400/15 text-orange-400 border-orange-400/30',
        isFlag && 'bg-yellow-400/15 text-yellow-400 border-yellow-400/30',
        isAllow && 'bg-sardis-500/15 text-sardis-400 border-sardis-500/30',
        !isKill && !isFrozen && !isApproval && !isFlag && !isAllow &&
          'bg-gray-500/15 text-gray-400 border-gray-500/30',
      )}
    >
      {isKill && <span className="relative flex h-1.5 w-1.5"><span className="animate-ping absolute inline-flex h-full w-full bg-red-400 opacity-75" /><span className="relative inline-flex h-1.5 w-1.5 bg-red-500" /></span>}
      {upper || 'UNKNOWN'}
    </span>
  )
}

/* ─── Score Gauge ─── */

function ScoreGauge({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' | 'lg' }) {
  const pct = Math.min(1, Math.max(0, score)) * 100

  return (
    <div className={clsx('flex items-center gap-2', size === 'lg' && 'flex-col')}>
      {size === 'lg' && (
        <span className={clsx('text-4xl font-bold font-mono', scoreColor(score))}>
          {score.toFixed(2)}
        </span>
      )}
      <div
        className={clsx(
          'relative bg-dark-100 overflow-hidden flex-1',
          size === 'sm' && 'h-1.5 w-20',
          size === 'md' && 'h-2 w-28',
          size === 'lg' && 'h-3 w-48',
        )}
      >
        <div
          className={clsx('h-full transition-all duration-300', scoreBg(score))}
          style={{ width: `${pct}%` }}
        />
      </div>
      {size !== 'lg' && (
        <span className={clsx('font-mono text-xs tabular-nums', scoreColor(score))}>
          {score.toFixed(2)}
        </span>
      )}
    </div>
  )
}

/* ─── Signal Bar Row ─── */

function SignalBar({ signal }: { signal: AnomalySignal }) {
  const pct = Math.min(1, Math.max(0, signal.score)) * 100

  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-xs text-gray-400 font-mono w-40 flex-shrink-0 truncate" title={signal.name}>
        {signal.name}
      </span>
      <div className="flex-1 relative bg-dark-100 h-1.5 overflow-hidden">
        <div
          className={clsx('h-full transition-all duration-300', scoreBg(signal.score))}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={clsx('text-xs font-mono w-10 text-right tabular-nums', scoreColor(signal.score))}>
        {signal.score.toFixed(2)}
      </span>
      {typeof signal.weight === 'number' && (
        <span className="text-xs text-gray-600 w-16 text-right tabular-nums">
          w:{signal.weight.toFixed(2)}
        </span>
      )}
    </div>
  )
}

/* ─── Event Row ─── */

function EventRow({ event }: { event: AnomalyEvent }) {
  const [expanded, setExpanded] = useState(false)
  const score = getScore(event)
  const ts = getTimestamp(event)
  const signals = normalizeSignals(event)

  return (
    <div className={clsx('border-b border-dark-100 last:border-b-0 transition-colors', expanded && 'bg-dark-200/60')}>
      <button
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-dark-200/40 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        {/* Timestamp */}
        <span className="text-xs text-gray-500 font-mono w-28 flex-shrink-0 truncate">
          {ts ? formatTimeAgo(ts) : '—'}
        </span>

        {/* Agent ID */}
        <span className="text-xs text-gray-300 font-mono w-44 flex-shrink-0 truncate" title={getAgentId(event)}>
          {getAgentId(event)}
        </span>

        {/* Score gauge */}
        <div className="w-44 flex-shrink-0">
          <ScoreGauge score={score} size="sm" />
        </div>

        {/* Action */}
        <div className="flex-1">
          <ActionBadge action={event.action} />
        </div>

        {/* Signals count */}
        <span className="text-xs text-gray-500 w-20 flex-shrink-0 text-right">
          {signals.length > 0 ? `${signals.length} signal${signals.length !== 1 ? 's' : ''}` : '—'}
        </span>

        {/* Expand chevron */}
        <span className="flex-shrink-0 ml-2">
          {expanded
            ? <CaretDown className="w-3.5 h-3.5 text-gray-500" />
            : <CaretRight className="w-3.5 h-3.5 text-gray-500" />}
        </span>
      </button>

      {/* Expanded signal breakdown */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-dark-100">
          <div className={clsx('p-3 border mb-3', scoreBorder(score))}>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Overall Score</p>
                <p className={clsx('text-2xl font-bold font-mono', scoreColor(score))}>
                  {score.toFixed(3)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Action</p>
                <ActionBadge action={event.action} />
              </div>
              {ts && (
                <div>
                  <p className="text-xs text-gray-500 mb-0.5">Timestamp</p>
                  <p className="text-xs text-gray-300 font-mono">
                    {new Date(ts).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {signals.length > 0 ? (
            <div className="space-y-0.5">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Signal Breakdown
              </p>
              {signals.map((sig, i) => (
                <SignalBar key={i} signal={sig} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-600 italic">No individual signal data available.</p>
          )}

          {event.metadata && Object.keys(event.metadata).length > 0 && (
            <div className="mt-3 pt-3 border-t border-dark-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Metadata</p>
              <pre className="text-xs text-gray-500 font-mono bg-dark-100 p-2 overflow-x-auto">
                {JSON.stringify(event.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Risk Assessment Tool ─── */

function AssessmentTool() {
  const assessRisk = useAssessRisk()
  const [open, setOpen] = useState(false)
  const [agentId, setAgentId] = useState('')
  const [amount, setAmount] = useState('')
  const [merchantId, setMerchantId] = useState('')
  const [mccCode, setMccCode] = useState('')

  const canSubmit = !!agentId && !!amount && !assessRisk.isPending

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    const payload: { agent_id: string; amount: string; merchant_id?: string; mcc_code?: string } = {
      agent_id: agentId,
      amount,
    }
    if (merchantId.trim()) payload.merchant_id = merchantId.trim()
    if (mccCode.trim()) payload.mcc_code = mccCode.trim()
    assessRisk.mutate(payload)
  }

  const result = assessRisk.data as JsonObject | undefined
  const resultScore = typeof result?.overall_score === 'number'
    ? result.overall_score
    : typeof result?.score === 'number'
    ? result.score
    : null

  const resultSignals = Array.isArray(result?.signals)
    ? (result.signals as AnomalySignal[])
    : result?.signal_scores && typeof result.signal_scores === 'object'
    ? Object.entries(result.signal_scores as Record<string, number>).map(([name, score]) => ({
        name, score, weight: 1,
      }))
    : []

  return (
    <div className="card overflow-hidden">
      <button
        className="w-full flex items-center justify-between gap-3 px-5 py-4 hover:bg-dark-200/50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-sardis-500/10 border border-sardis-500/20">
            <Lightning className="w-4 h-4 text-sardis-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-white">Risk Assessment Tool</p>
            <p className="text-xs text-gray-500">Assess risk score for a transaction on-demand</p>
          </div>
        </div>
        {open
          ? <CaretDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
          : <CaretRight className="w-4 h-4 text-gray-500 flex-shrink-0" />}
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-dark-100">
          <div className="flex flex-col lg:flex-row gap-5 mt-4">
            {/* Form */}
            <form onSubmit={handleSubmit} className="flex-1 space-y-4 max-w-md">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
                    Agent ID <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={agentId}
                    onChange={e => setAgentId(e.target.value)}
                    placeholder="agt_..."
                    className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
                    Amount <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="number"
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                    placeholder="e.g. 50.00"
                    className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
                    Merchant ID <span className="text-gray-600">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={merchantId}
                    onChange={e => setMerchantId(e.target.value)}
                    placeholder="merch_..."
                    className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
                    MCC Code <span className="text-gray-600">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={mccCode}
                    onChange={e => setMccCode(e.target.value)}
                    placeholder="e.g. 7372"
                    className="w-full px-3 py-2.5 bg-dark-200 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 transition-colors"
                  />
                </div>
              </div>

              {assessRisk.isError && (
                <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/5 border border-red-500/25">
                  <XCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-300">
                    {(assessRisk.error as Error)?.message ?? 'Assessment failed.'}
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={!canSubmit}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2.5 font-semibold text-sm transition-colors',
                  canSubmit
                    ? 'bg-sardis-500 text-white hover:bg-sardis-600'
                    : 'bg-dark-200 text-gray-600 border border-dark-100 cursor-not-allowed',
                )}
              >
                {assessRisk.isPending ? (
                  <>
                    <SpinnerGap className="w-4 h-4 animate-spin" />
                    Assessing...
                  </>
                ) : (
                  <>
                    <Lightning className="w-4 h-4" />
                    Assess Risk
                  </>
                )}
              </button>
            </form>

            {/* Result */}
            {result && !assessRisk.isPending && (
              <div className="flex-1 space-y-4">
                {/* Score gauge */}
                {resultScore !== null && (
                  <div className={clsx('p-4 border', scoreBorder(resultScore))}>
                    <p className="text-xs text-gray-500 mb-3 uppercase tracking-wider font-medium">Overall Risk Score</p>
                    <ScoreGauge score={resultScore} size="lg" />
                    {typeof result.action === 'string' && result.action && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-500 mb-1">Recommended Action</p>
                        <ActionBadge action={result.action} />
                      </div>
                    )}
                  </div>
                )}

                {/* Signals */}
                {resultSignals.length > 0 && (
                  <div className="p-4 bg-dark-200 border border-dark-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      Signal Breakdown
                    </p>
                    <div className="space-y-0.5">
                      {resultSignals.map((sig, i) => (
                        <SignalBar key={i} signal={sig} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {assessRisk.isPending && (
              <div className="flex-1 flex items-center justify-center min-h-[120px]">
                <div className="flex items-center gap-3 text-gray-500">
                  <SpinnerGap className="w-5 h-5 animate-spin text-sardis-400" />
                  <span className="text-sm">Evaluating risk signals...</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Threshold Config Panel ─── */

function ThresholdConfig() {
  const configQuery = useAnomalyConfig()
  const updateConfig = useUpdateAnomalyConfig()
  const [open, setOpen] = useState(false)

  // Local draft state mirrors what we'll PUT
  const [thresholds, setThresholds] = useState<Record<string, string>>({})
  const [weights, setWeights] = useState<Record<string, string>>({})
  const [initialized, setInitialized] = useState(false)

  // Initialize draft from remote once
  if (configQuery.data && !initialized) {
    const cfg = configQuery.data as JsonObject
    const remoteThresholds = (cfg.thresholds ?? {}) as Record<string, number>
    const remoteWeights = (cfg.signal_weights ?? {}) as Record<string, number>
    setThresholds(Object.fromEntries(Object.entries(remoteThresholds).map(([k, v]) => [k, String(v)])))
    setWeights(Object.fromEntries(Object.entries(remoteWeights).map(([k, v]) => [k, String(v)])))
    setInitialized(true)
  }

  const handleSave = () => {
    const parsedThresholds: Record<string, number> = {}
    const parsedWeights: Record<string, number> = {}

    for (const [k, v] of Object.entries(thresholds)) {
      const n = parseFloat(v)
      if (!isNaN(n)) parsedThresholds[k] = n
    }
    for (const [k, v] of Object.entries(weights)) {
      const n = parseFloat(v)
      if (!isNaN(n)) parsedWeights[k] = n
    }

    updateConfig.mutate({
      thresholds: Object.keys(parsedThresholds).length > 0 ? parsedThresholds : undefined,
      signal_weights: Object.keys(parsedWeights).length > 0 ? parsedWeights : undefined,
    })
  }

  const hasThresholds = Object.keys(thresholds).length > 0
  const hasWeights = Object.keys(weights).length > 0

  return (
    <div className="card overflow-hidden">
      <button
        className="w-full flex items-center justify-between gap-3 px-5 py-4 hover:bg-dark-200/50 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-dark-200 border border-dark-100">
            <Sliders className="w-4 h-4 text-gray-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-white">Threshold Configuration</p>
            <p className="text-xs text-gray-500">Configure action thresholds and signal weights</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {configQuery.isLoading && <SpinnerGap className="w-3.5 h-3.5 animate-spin text-gray-500" />}
          {open
            ? <CaretDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
            : <CaretRight className="w-4 h-4 text-gray-500 flex-shrink-0" />}
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-dark-100">
          {configQuery.isError && (
            <div className="flex items-center gap-2 mt-4 px-3 py-2.5 bg-red-500/5 border border-red-500/25">
              <Warning className="w-4 h-4 text-red-400 flex-shrink-0" />
              <p className="text-xs text-red-300">Failed to load config from API.</p>
            </div>
          )}

          {!configQuery.isLoading && !configQuery.isError && (
            <div className="mt-4 flex flex-col lg:flex-row gap-6">
              {/* Action thresholds */}
              <div className="flex-1">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Action Thresholds (0–1)
                </p>
                {hasThresholds ? (
                  <div className="space-y-3">
                    {Object.entries(thresholds).map(([key, val]) => (
                      <div key={key} className="flex items-center gap-3">
                        <label className="text-xs text-gray-300 font-mono w-40 flex-shrink-0">{key}</label>
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.01"
                          value={val}
                          onChange={e => setThresholds(t => ({ ...t, [key]: e.target.value }))}
                          className="w-28 px-3 py-2 bg-dark-200 border border-dark-100 text-white text-sm font-mono focus:outline-none focus:border-sardis-500/60 transition-colors"
                        />
                        <div className="flex-1 relative bg-dark-100 h-1.5 overflow-hidden">
                          <div
                            className={clsx('h-full', scoreBg(parseFloat(val) || 0))}
                            style={{ width: `${(parseFloat(val) || 0) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-600 italic">No threshold data returned by API.</p>
                )}
              </div>

              {/* Signal weights */}
              <div className="flex-1">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  Signal Weights
                </p>
                {hasWeights ? (
                  <div className="space-y-3">
                    {Object.entries(weights).map(([key, val]) => (
                      <div key={key} className="flex items-center gap-3">
                        <label className="text-xs text-gray-300 font-mono w-40 flex-shrink-0 truncate" title={key}>
                          {key}
                        </label>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={val}
                          onChange={e => setWeights(w => ({ ...w, [key]: e.target.value }))}
                          className="w-28 px-3 py-2 bg-dark-200 border border-dark-100 text-white text-sm font-mono focus:outline-none focus:border-sardis-500/60 transition-colors"
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-600 italic">No signal weight data returned by API.</p>
                )}
              </div>
            </div>
          )}

          {/* Save / status */}
          <div className="mt-5 flex items-center gap-3 pt-4 border-t border-dark-100">
            <button
              onClick={handleSave}
              disabled={updateConfig.isPending || (!hasThresholds && !hasWeights)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2.5 font-semibold text-sm transition-colors',
                !updateConfig.isPending && (hasThresholds || hasWeights)
                  ? 'bg-sardis-500 text-white hover:bg-sardis-600'
                  : 'bg-dark-200 text-gray-600 border border-dark-100 cursor-not-allowed',
              )}
            >
              {updateConfig.isPending ? (
                <>
                  <SpinnerGap className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Gear className="w-4 h-4" />
                  Save Configuration
                </>
              )}
            </button>
            {updateConfig.isSuccess && (
              <span className="text-xs text-sardis-400">Configuration saved.</span>
            )}
            {updateConfig.isError && (
              <span className="text-xs text-red-400">
                {(updateConfig.error as Error)?.message ?? 'Save failed.'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Events Table ─── */

function EventsTable({
  events,
  isLoading,
  isError,
  filterAgentId,
  setFilterAgentId,
  filterMinScore,
  setFilterMinScore,
  onRefresh,
}: {
  events: AnomalyEvent[]
  isLoading: boolean
  isError: boolean
  filterAgentId: string
  setFilterAgentId: (v: string) => void
  filterMinScore: string
  setFilterMinScore: (v: string) => void
  onRefresh: () => void
}) {
  return (
    <div className="card overflow-hidden">
      {/* Table header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-5 py-4 border-b border-dark-100">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-dark-200 border border-dark-100">
            <ChartBar className="w-4 h-4 text-gray-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Recent Anomaly Events</p>
            <p className="text-xs text-gray-500">{events.length} event{events.length !== 1 ? 's' : ''} — refreshes every 15s</p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="text"
            value={filterAgentId}
            onChange={e => setFilterAgentId(e.target.value)}
            placeholder="Filter by agent..."
            className="px-3 py-2 bg-dark-200 border border-dark-100 text-white text-xs placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 w-40 transition-colors"
          />
          <input
            type="number"
            value={filterMinScore}
            onChange={e => setFilterMinScore(e.target.value)}
            placeholder="Min score"
            min="0"
            max="1"
            step="0.1"
            className="px-3 py-2 bg-dark-200 border border-dark-100 text-white text-xs placeholder-gray-600 focus:outline-none focus:border-sardis-500/60 w-28 transition-colors"
          />
          <button
            onClick={onRefresh}
            className="p-2 bg-dark-200 border border-dark-100 hover:border-sardis-500/40 transition-colors"
            title="Refresh"
          >
            <ArrowsClockwise className={clsx('w-3.5 h-3.5 text-gray-400', isLoading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* Column headers */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-dark-100 bg-dark-200/40">
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider w-28 flex-shrink-0">Time</span>
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider w-44 flex-shrink-0">Agent</span>
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider w-44 flex-shrink-0">Score</span>
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider flex-1">Action</span>
        <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider w-20 flex-shrink-0 text-right">Signals</span>
        <span className="w-5 flex-shrink-0" />
      </div>

      {/* Rows */}
      {isLoading && (
        <div className="flex items-center justify-center gap-3 py-16 text-gray-500">
          <SpinnerGap className="w-5 h-5 animate-spin text-sardis-400" />
          <span className="text-sm">Loading events...</span>
        </div>
      )}

      {isError && !isLoading && (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-500">
          <Warning className="w-5 h-5 text-yellow-400" />
          <span className="text-sm">Failed to load anomaly events.</span>
        </div>
      )}

      {!isLoading && !isError && events.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-16">
          <div className="p-5 bg-dark-200 border border-dark-100">
            <Pulse className="w-10 h-10 text-gray-600" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-white mb-1">No anomaly events</p>
            <p className="text-xs text-gray-500">Events will appear here as risk signals are detected.</p>
          </div>
        </div>
      )}

      {!isLoading && !isError && events.length > 0 && (
        <div>
          {events.map(ev => (
            <EventRow key={getEventId(ev)} event={ev} />
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Main Page ─── */

export default function AnomalyDashboard() {
  const [filterAgentId, setFilterAgentId] = useState('')
  const [filterMinScore, setFilterMinScore] = useState('')

  const eventsQuery = useAnomalyEvents({
    agent_id: filterAgentId.trim() || undefined,
    min_score: filterMinScore ? parseFloat(filterMinScore) : undefined,
    limit: 50,
  })

  const rawEvents = ((eventsQuery.data ?? []) as JsonObject[]).map(normalizeEvent)

  // Stats
  const totalEvents = rawEvents.length
  const highRiskEvents = rawEvents.filter(ev => getScore(ev) >= 0.6).length
  const autoFrozenCount = rawEvents.filter(ev => {
    const a = (ev.action ?? '').toLowerCase()
    return a === 'freeze_agent' || a === 'kill_switch'
  }).length
  const avgScore = rawEvents.length > 0
    ? rawEvents.reduce((sum, ev) => sum + getScore(ev), 0) / rawEvents.length
    : 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
            <Pulse className="w-8 h-8 text-sardis-400" />
            Anomaly Detection
          </h1>
          <p className="text-gray-400 mt-1 max-w-xl">
            Real-time risk signal visualization and automatic response pipeline
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-dark-200 border border-dark-100 text-xs text-gray-500">
          <ShieldWarning className="w-4 h-4 text-sardis-400" />
          Live — refreshes every 15s
        </div>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Events"
          value={totalEvents}
          icon={<ChartBar className="w-5 h-5" />}
          subtitle="In current filter"
        />
        <StatCard
          title="High Risk"
          value={highRiskEvents}
          icon={<Warning className="w-5 h-5" />}
          subtitle="Score >= 0.60"
          changeType={highRiskEvents > 0 ? 'negative' : 'neutral'}
        />
        <StatCard
          title="Auto-Frozen"
          value={autoFrozenCount}
          icon={<ShieldSlash className="w-5 h-5" />}
          subtitle="Freeze / kill-switch"
          changeType={autoFrozenCount > 0 ? 'negative' : 'neutral'}
        />
        <StatCard
          title="Avg Risk Score"
          value={rawEvents.length > 0 ? avgScore.toFixed(3) : '—'}
          icon={<Pulse className="w-5 h-5" />}
          subtitle="Across filtered events"
          changeType={avgScore >= 0.6 ? 'negative' : avgScore >= 0.3 ? 'neutral' : 'positive'}
        />
      </div>

      {/* Risk Assessment Tool */}
      <AssessmentTool />

      {/* Events Table */}
      <EventsTable
        events={rawEvents}
        isLoading={eventsQuery.isLoading}
        isError={eventsQuery.isError}
        filterAgentId={filterAgentId}
        setFilterAgentId={setFilterAgentId}
        filterMinScore={filterMinScore}
        setFilterMinScore={setFilterMinScore}
        onRefresh={() => eventsQuery.refetch()}
      />

      {/* Threshold Configuration */}
      <ThresholdConfig />
    </div>
  )
}
