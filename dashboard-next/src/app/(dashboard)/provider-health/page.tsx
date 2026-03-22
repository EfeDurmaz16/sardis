"use client";
import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  ExternalLink,
  Loader2,
  RefreshCw,
  Server,
  ShieldAlert,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'

import {
  reliabilityApi,
  type ProviderReliabilityScorecard,
} from '@/api/client'

type ProviderStatus = 'operational' | 'degraded' | 'down'
type SloStatus = 'ok' | 'warning' | 'breached'

interface ProviderAggregate {
  provider: string
  status: ProviderStatus
  availability: number
  errorRate: number
  avgLatencyMs: number
  p95LatencyMs: number
  totalCalls: number
  successCount: number
  failureCount: number
  chains: ProviderReliabilityScorecard[]
  computedAt: string
}

interface RailAggregate {
  chain: string
  providerCount: number
  primaryProvider: string
  status: ProviderStatus
  availability: number
  errorRate: number
  avgLatencyMs: number
  totalCalls: number
}

interface SloRow {
  label: string
  target: string
  current: string
  status: SloStatus
  note: string
}

function percent(value: number): number {
  return value * 100
}

function providerStatus(availability: number, errorRate: number): ProviderStatus {
  if (availability >= 0.995 && errorRate <= 0.01) return 'operational'
  if (availability >= 0.98 && errorRate <= 0.03) return 'degraded'
  return 'down'
}

function statusText(status: ProviderStatus): string {
  if (status === 'operational') return 'Operational'
  if (status === 'degraded') return 'Degraded'
  return 'Down'
}

function statusClasses(status: ProviderStatus): string {
  if (status === 'operational') return 'text-sardis-400 border-sardis-500/20 bg-sardis-500/5'
  if (status === 'degraded') return 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5'
  return 'text-red-400 border-red-500/20 bg-red-500/5'
}

function dotClasses(status: ProviderStatus): string {
  if (status === 'operational') return 'bg-sardis-400'
  if (status === 'degraded') return 'bg-yellow-400'
  return 'bg-red-400'
}

function providerInitials(provider: string): string {
  return provider
    .split(/[\s/_-]+/)
    .map((part) => part[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function formatLatency(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms.toFixed(0)}ms`
}

function formatRelativeTime(value: string): string {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return 'unknown'

  const diffMs = Date.now() - timestamp
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000))
  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return `${Math.floor(diffHours / 24)}d ago`
}

function toProviderAggregates(scorecards: ProviderReliabilityScorecard[]): ProviderAggregate[] {
  const grouped = new Map<string, ProviderReliabilityScorecard[]>()

  for (const scorecard of scorecards) {
    const items = grouped.get(scorecard.provider) ?? []
    items.push(scorecard)
    grouped.set(scorecard.provider, items)
  }

  return Array.from(grouped.entries())
    .map(([provider, chains]) => {
      const totalCalls = chains.reduce((sum, card) => sum + card.total_calls, 0)
      const successCount = chains.reduce((sum, card) => sum + card.success_count, 0)
      const failureCount = chains.reduce((sum, card) => sum + card.failure_count, 0)
      const weightedLatency = chains.reduce(
        (sum, card) => sum + card.avg_latency_ms * Math.max(card.total_calls, 1),
        0,
      )
      const availability = totalCalls > 0 ? successCount / totalCalls : 1
      const errorRate = totalCalls > 0 ? failureCount / totalCalls : 0
      const avgLatencyMs = totalCalls > 0 ? weightedLatency / totalCalls : 0
      const p95LatencyMs = Math.max(...chains.map((card) => card.p95_latency_ms), 0)
      const computedTimes = chains
        .map((card) => card.computed_at)
        .sort()
      const computedAt =
        computedTimes[computedTimes.length - 1] ?? new Date().toISOString()

      return {
        provider,
        status: providerStatus(availability, errorRate),
        availability,
        errorRate,
        avgLatencyMs,
        p95LatencyMs,
        totalCalls,
        successCount,
        failureCount,
        chains: [...chains].sort((a, b) => a.chain.localeCompare(b.chain)),
        computedAt,
      }
    })
    .sort((left, right) => {
      const severityWeight = { operational: 0, degraded: 1, down: 2 }
      const severityDiff = severityWeight[right.status] - severityWeight[left.status]
      if (severityDiff !== 0) return severityDiff
      return right.totalCalls - left.totalCalls
    })
}

function toRailAggregates(scorecards: ProviderReliabilityScorecard[]): RailAggregate[] {
  const grouped = new Map<string, ProviderReliabilityScorecard[]>()

  for (const scorecard of scorecards) {
    const items = grouped.get(scorecard.chain) ?? []
    items.push(scorecard)
    grouped.set(scorecard.chain, items)
  }

  return Array.from(grouped.entries())
    .map(([chain, providers]) => {
      const totalCalls = providers.reduce((sum, card) => sum + card.total_calls, 0)
      const successCount = providers.reduce((sum, card) => sum + card.success_count, 0)
      const failureCount = providers.reduce((sum, card) => sum + card.failure_count, 0)
      const weightedLatency = providers.reduce(
        (sum, card) => sum + card.avg_latency_ms * Math.max(card.total_calls, 1),
        0,
      )
      const primary = [...providers].sort((a, b) => b.total_calls - a.total_calls)[0]
      const availability = totalCalls > 0 ? successCount / totalCalls : 1
      const errorRate = totalCalls > 0 ? failureCount / totalCalls : 0
      const avgLatencyMs = totalCalls > 0 ? weightedLatency / totalCalls : 0

      return {
        chain,
        providerCount: providers.length,
        primaryProvider: primary?.provider ?? 'n/a',
        status: providerStatus(availability, errorRate),
        availability,
        errorRate,
        avgLatencyMs,
        totalCalls,
      }
    })
    .sort((left, right) => right.totalCalls - left.totalCalls)
}

function buildSloRows(
  providers: ProviderAggregate[],
  rails: RailAggregate[],
): SloRow[] {
  const totalCalls = providers.reduce((sum, item) => sum + item.totalCalls, 0)
  const totalSuccess = providers.reduce((sum, item) => sum + item.successCount, 0)
  const weightedLatency = providers.reduce(
    (sum, item) => sum + item.avgLatencyMs * Math.max(item.totalCalls, 1),
    0,
  )
  const p95Max = Math.max(...providers.map((item) => item.p95LatencyMs), 0)
  const successRate = totalCalls > 0 ? totalSuccess / totalCalls : 1
  const avgLatencyMs = totalCalls > 0 ? weightedLatency / totalCalls : 0
  const degradedRails = rails.filter((rail) => rail.status !== 'operational').length

  const availabilityStatus: SloStatus =
    successRate >= 0.995 ? 'ok' : successRate >= 0.99 ? 'warning' : 'breached'
  const latencyStatus: SloStatus =
    p95Max <= 1500 ? 'ok' : p95Max <= 2500 ? 'warning' : 'breached'
  const railStatus: SloStatus =
    degradedRails === 0 ? 'ok' : degradedRails <= 2 ? 'warning' : 'breached'

  return [
    {
      label: 'Weighted success rate',
      target: '>= 99.5%',
      current: `${percent(successRate).toFixed(2)}%`,
      status: availabilityStatus,
      note: 'Rolls up success and failure counts across monitored providers.',
    },
    {
      label: 'Weighted avg latency',
      target: '<= 750ms',
      current: formatLatency(avgLatencyMs),
      status: avgLatencyMs <= 750 ? 'ok' : avgLatencyMs <= 1200 ? 'warning' : 'breached',
      note: 'Good proxy for routing confidence in day-to-day operations.',
    },
    {
      label: 'Worst provider p95 latency',
      target: '<= 1.5s',
      current: formatLatency(p95Max),
      status: latencyStatus,
      note: 'Flags when an outlier provider can slow critical payment paths.',
    },
    {
      label: 'Degraded rails',
      target: '0',
      current: String(degradedRails),
      status: railStatus,
      note: 'Any degraded rail should push operators toward fallback review.',
    },
  ]
}

function SloBadge({ status }: { status: SloStatus }) {
  const classes =
    status === 'ok'
      ? 'text-sardis-400 border-sardis-500/20 bg-sardis-500/5'
      : status === 'warning'
        ? 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5'
        : 'text-red-400 border-red-500/20 bg-red-500/5'

  return (
    <span className={clsx('px-2 py-0.5 text-xs border font-medium uppercase tracking-wide', classes)}>
      {status}
    </span>
  )
}

function ProviderCard({ provider }: { provider: ProviderAggregate }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={clsx('border bg-dark-300', statusClasses(provider.status))}>
      <div className="p-5 flex items-start gap-4">
        <div className="w-10 h-10 bg-dark-200 border border-dark-100 flex items-center justify-center text-sm font-mono text-white">
          {providerInitials(provider.provider)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-white">{provider.provider}</h3>
            <div className="flex items-center gap-1.5">
              <div className={clsx('w-2 h-2 rounded-full', dotClasses(provider.status))} />
              <span className="text-xs text-gray-400">{statusText(provider.status)}</span>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {provider.chains.length} chains monitored, refreshed {formatRelativeTime(provider.computedAt)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 px-5 pb-5 border-t border-dark-100/60 pt-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">Availability</p>
          <p className="text-sm font-semibold text-white">{percent(provider.availability).toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Error rate</p>
          <p className="text-sm font-semibold text-white">{percent(provider.errorRate).toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Avg latency</p>
          <p className="text-sm font-semibold text-white">{formatLatency(provider.avgLatencyMs)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">p95 latency</p>
          <p className="text-sm font-semibold text-white">{formatLatency(provider.p95LatencyMs)}</p>
        </div>
      </div>

      <button
        onClick={() => setExpanded((value) => !value)}
        className="w-full px-5 py-3 border-t border-dark-100/60 flex items-center justify-between text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <span>Chain breakdown</span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-dark-100/60 pt-3 space-y-3">
          {provider.chains.map((chain) => (
            <div key={`${chain.provider}-${chain.chain}`} className="flex items-center justify-between gap-4 text-sm">
              <div>
                <p className="text-white font-medium">{chain.chain}</p>
                <p className="text-xs text-gray-500">
                  {chain.total_calls.toLocaleString()} calls, refreshed {formatRelativeTime(chain.computed_at)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-white font-medium">{percent(chain.availability).toFixed(2)}%</p>
                <p className="text-xs text-gray-500">{formatLatency(chain.p95_latency_ms)} p95</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ProviderScorecardsPage() {
  const [scorecards, setScorecards] = useState<ProviderReliabilityScorecard[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const response = await reliabilityApi.listProviders()
      const cards24h = response.scorecards.filter((scorecard) => scorecard.period === '24h')
      setScorecards(cards24h)
      setLastRefreshed(new Date().toISOString())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load provider scorecards')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const providers = useMemo(() => toProviderAggregates(scorecards), [scorecards])
  const rails = useMemo(() => toRailAggregates(scorecards), [scorecards])
  const sloRows = useMemo(() => buildSloRows(providers, rails), [providers, rails])

  const operationalCount = providers.filter((provider) => provider.status === 'operational').length
  const degradedCount = providers.filter((provider) => provider.status === 'degraded').length
  const downCount = providers.filter((provider) => provider.status === 'down').length

  return (
    <div className="space-y-8 max-w-6xl">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold font-display text-white">Provider Health</h1>
          <p className="text-sm text-gray-400 mt-1">
            Live provider and rail scorecards sourced from Sardis reliability telemetry.
          </p>
          <p className="text-xs text-gray-500 mt-2 max-w-2xl">
            Use this surface to decide when to reroute, when to tighten degraded-mode policies,
            and when a payment issue belongs in the control center rather than ad hoc founder triage.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/control-center"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-sardis-400 border border-sardis-500/30 hover:bg-sardis-500/10 transition-colors"
          >
            Control Center
            <ExternalLink className="w-3 h-3" />
          </Link>
          <Link
            href="/fallback-rules"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-300 border border-dark-100 hover:border-sardis-500/30 hover:text-sardis-400 transition-colors"
          >
            Fallback Rules
            <ExternalLink className="w-3 h-3" />
          </Link>
          <button
            onClick={() => void load(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium border border-dark-100 text-gray-300 hover:text-white hover:border-sardis-500/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={clsx('w-4 h-4', refreshing && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-dark-300 border border-dark-100 p-4">
          <div className="flex items-center gap-2 mb-1">
            <Server className="w-4 h-4 text-gray-500" />
            <span className="text-xs uppercase tracking-wider text-gray-500">Providers</span>
          </div>
          <p className="text-2xl font-bold font-mono text-white">{providers.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">with 24h scorecards</p>
        </div>

        <div className="bg-dark-300 border border-sardis-500/20 p-4">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 className="w-4 h-4 text-sardis-400" />
            <span className="text-xs uppercase tracking-wider text-gray-500">Operational</span>
          </div>
          <p className="text-2xl font-bold font-mono text-sardis-400">{operationalCount}</p>
          <p className="text-xs text-gray-500 mt-0.5">healthy providers</p>
        </div>

        <div className="bg-dark-300 border border-yellow-500/20 p-4">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            <span className="text-xs uppercase tracking-wider text-gray-500">Degraded</span>
          </div>
          <p className="text-2xl font-bold font-mono text-yellow-400">{degradedCount}</p>
          <p className="text-xs text-gray-500 mt-0.5">needs routing review</p>
        </div>

        <div className="bg-dark-300 border border-red-500/20 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            <span className="text-xs uppercase tracking-wider text-gray-500">Down</span>
          </div>
          <p className="text-2xl font-bold font-mono text-red-400">{downCount}</p>
          <p className="text-xs text-gray-500 mt-0.5">operator action required</p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-3 text-gray-400 py-10">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading reliability scorecards…</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-3 px-4 py-3 border border-red-500/20 bg-red-500/5 text-red-400">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      ) : providers.length === 0 ? (
        <div className="border border-dark-100 bg-dark-300 p-8 text-center space-y-3">
          <Activity className="w-8 h-8 text-gray-600 mx-auto" />
          <h2 className="text-lg font-semibold text-white">No provider scorecards yet</h2>
          <p className="text-sm text-gray-500 max-w-xl mx-auto">
            Reliability telemetry is mounted, but no provider events have been recorded yet. Once
            routing traffic or tests run through tracked providers, this page will become decision
            support instead of a placeholder.
          </p>
        </div>
      ) : (
        <>
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Provider Scorecards</h2>
                <p className="text-sm text-gray-500">
                  Aggregated 24h health by provider across all tracked chains.
                </p>
              </div>
              {lastRefreshed && (
                <p className="text-xs text-gray-500 flex items-center gap-1.5">
                  <Clock3 className="w-3.5 h-3.5" />
                  Refreshed {formatRelativeTime(lastRefreshed)}
                </p>
              )}
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {providers.map((provider) => (
                <ProviderCard key={provider.provider} provider={provider} />
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
            <div className="bg-dark-300 border border-dark-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-5 h-5 text-sardis-400" />
                <div>
                  <h2 className="text-lg font-semibold text-white">Rail Posture</h2>
                  <p className="text-sm text-gray-500">
                    Chain-level health to support fallback and degraded-mode decisions.
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-100 text-xs uppercase tracking-wider text-gray-500">
                      <th className="text-left py-3 pr-4 font-medium">Rail</th>
                      <th className="text-left py-3 pr-4 font-medium">Primary provider</th>
                      <th className="text-left py-3 pr-4 font-medium">Status</th>
                      <th className="text-right py-3 pr-4 font-medium">Availability</th>
                      <th className="text-right py-3 font-medium">Avg latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dark-100">
                    {rails.map((rail) => (
                      <tr key={rail.chain}>
                        <td className="py-3 pr-4 text-white font-medium">{rail.chain}</td>
                        <td className="py-3 pr-4 text-gray-400">
                          {rail.primaryProvider} · {rail.providerCount} providers
                        </td>
                        <td className="py-3 pr-4">
                          <span className={clsx('px-2 py-0.5 border text-xs font-medium', statusClasses(rail.status))}>
                            {statusText(rail.status)}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-right text-white font-mono">
                          {percent(rail.availability).toFixed(2)}%
                        </td>
                        <td className="py-3 text-right text-white font-mono">
                          {formatLatency(rail.avgLatencyMs)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-dark-300 border border-dark-100 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-sardis-400" />
                <div>
                  <h2 className="text-lg font-semibold text-white">SLO Snapshot</h2>
                  <p className="text-sm text-gray-500">
                    A compact decision-support view rather than generic observability.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                {sloRows.map((row) => (
                  <div key={row.label} className="border border-dark-100 bg-dark-200 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-white">{row.label}</p>
                        <p className="text-xs text-gray-500 mt-1">{row.note}</p>
                      </div>
                      <SloBadge status={row.status} />
                    </div>
                    <div className="flex items-center justify-between gap-4 mt-3 text-xs">
                      <span className="text-gray-500">Target: {row.target}</span>
                      <span className="text-white font-mono">Current: {row.current}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
