import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowSquareOut,
  ArrowsClockwise,
  ChartBar,
  CheckCircle,
  Clock,
  Lightbulb,
  SpinnerGap,
  TrendDown,
  TrendUp,
  Warning,
  XCircle,
} from '@phosphor-icons/react'
import clsx from 'clsx'

import {
  policyAnalyticsApi,
  type PolicyAnalyticsDenyReason,
  type PolicyAnalyticsDailyOutcome,
  type PolicyAnalyticsOutcomesResponse,
  type PolicyAnalyticsSuggestion,
  type PolicyAnalyticsSummary,
  type PolicyAnalyticsVersionImpact,
} from '../api/client'

type Period = '24h' | '7d' | '30d'

function emptySummary(): PolicyAnalyticsSummary {
  return {
    total_checks: 0,
    allowed: 0,
    denied: 0,
    escalated: 0,
    allow_rate: 0,
    deny_rate: 0,
    escalation_rate: 0,
  }
}

function trendIcon(trend: 'up' | 'down' | 'flat') {
  if (trend === 'up') return <TrendUp className="w-4 h-4 text-red-400" />
  if (trend === 'down') return <TrendDown className="w-4 h-4 text-sardis-400" />
  return <span className="text-gray-500">•</span>
}

function suggestionClasses(severity: PolicyAnalyticsSuggestion['severity']): string {
  if (severity === 'action') return 'border-red-500/20 bg-red-500/5'
  if (severity === 'warn') return 'border-yellow-500/20 bg-yellow-500/5'
  return 'border-sardis-500/20 bg-sardis-500/5'
}

function usePolicyAnalytics() {
  const [period, setPeriod] = useState<Period>('30d')
  const [outcomes, setOutcomes] = useState<PolicyAnalyticsOutcomesResponse | null>(null)
  const [denyReasons, setDenyReasons] = useState<PolicyAnalyticsDenyReason[]>([])
  const [suggestions, setSuggestions] = useState<PolicyAnalyticsSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const [outcomeResponse, denyReasonResponse, suggestionResponse] = await Promise.all([
        policyAnalyticsApi.getOutcomes({ period }),
        policyAnalyticsApi.getDenyReasons(),
        policyAnalyticsApi.getSuggestions(),
      ])
      setOutcomes(outcomeResponse)
      setDenyReasons(denyReasonResponse)
      setSuggestions(suggestionResponse)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load policy analytics')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [period])

  useEffect(() => {
    void load()
  }, [load])

  const summary = useMemo(() => {
    if (!outcomes) return emptySummary()
    if (period === '24h') return outcomes.summary_24h
    if (period === '7d') return outcomes.summary_7d
    return outcomes.summary_30d
  }, [outcomes, period])

  const dailyOutcomes = useMemo(() => {
    if (!outcomes) return [] as PolicyAnalyticsDailyOutcome[]
    if (period === '24h') return outcomes.daily_outcomes.slice(-1)
    if (period === '7d') return outcomes.daily_outcomes.slice(-7)
    return outcomes.daily_outcomes
  }, [outcomes, period])

  return {
    period,
    setPeriod,
    loading,
    refreshing,
    error,
    summary,
    dailyOutcomes,
    denyReasons,
    policyVersions: outcomes?.policy_versions ?? [],
    suggestions,
    refresh: () => load(true),
  }
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string
  sub: string
  accent: 'green' | 'red' | 'yellow' | 'gray'
}) {
  const accentClass = {
    green: 'text-sardis-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    gray: 'text-white',
  }[accent]

  return (
    <div className="bg-dark-300 border border-dark-100 p-5">
      <p className="text-xs uppercase tracking-wider text-gray-500">{label}</p>
      <p className={clsx('text-3xl font-bold font-mono mt-2', accentClass)}>{value}</p>
      <p className="text-xs text-gray-500 mt-2">{sub}</p>
    </div>
  )
}

function OutcomeBarChart({ data }: { data: PolicyAnalyticsDailyOutcome[] }) {
  const maxTotal = Math.max(...data.map((row) => row.allowed + row.denied + row.escalated), 1)

  return (
    <div className="grid grid-cols-1 gap-3">
      {data.map((row) => {
        const total = row.allowed + row.denied + row.escalated
        const allowWidth = total > 0 ? (row.allowed / maxTotal) * 100 : 0
        const denyWidth = total > 0 ? (row.denied / maxTotal) * 100 : 0
        const escalatedWidth = total > 0 ? (row.escalated / maxTotal) * 100 : 0

        return (
          <div key={row.date} className="grid grid-cols-[72px_1fr_80px] gap-4 items-center">
            <span className="text-xs text-gray-500 font-mono">{row.date}</span>
            <div className="h-4 bg-dark-200 border border-dark-100 flex overflow-hidden">
              <div className="bg-sardis-500/80" style={{ width: `${allowWidth}%` }} />
              <div className="bg-red-500/80" style={{ width: `${denyWidth}%` }} />
              <div className="bg-yellow-500/80" style={{ width: `${escalatedWidth}%` }} />
            </div>
            <span className="text-xs text-gray-400 text-right font-mono">{total}</span>
          </div>
        )
      })}
    </div>
  )
}

function DenyReasonsTable({ reasons }: { reasons: PolicyAnalyticsDenyReason[] }) {
  if (reasons.length === 0) {
    return <p className="text-sm text-gray-500">No deny or escalation reasons recorded yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-dark-100 text-xs uppercase tracking-wider text-gray-500">
            <th className="text-left py-3 pr-4 font-medium">Reason</th>
            <th className="text-right py-3 pr-4 font-medium">Count</th>
            <th className="text-right py-3 pr-4 font-medium">% of denials</th>
            <th className="text-right py-3 font-medium">Trend</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-dark-100">
          {reasons.map((reason) => (
            <tr key={reason.reason}>
              <td className="py-3 pr-4 text-white font-medium">{reason.reason}</td>
              <td className="py-3 pr-4 text-right text-white font-mono">{reason.count}</td>
              <td className="py-3 pr-4 text-right text-gray-300 font-mono">
                {reason.pct_of_denials.toFixed(1)}%
              </td>
              <td className="py-3 text-right">
                <span className="inline-flex items-center justify-end gap-1.5 text-xs text-gray-400">
                  {trendIcon(reason.trend)}
                  {reason.trend}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PolicyVersionTable({ versions }: { versions: PolicyAnalyticsVersionImpact[] }) {
  if (versions.length === 0) {
    return <p className="text-sm text-gray-500">No policy version history available yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-dark-100 text-xs uppercase tracking-wider text-gray-500">
            <th className="text-left py-3 pr-4 font-medium">Version</th>
            <th className="text-left py-3 pr-4 font-medium">Agent</th>
            <th className="text-left py-3 pr-4 font-medium">Label</th>
            <th className="text-right py-3 pr-4 font-medium">Deny before</th>
            <th className="text-right py-3 pr-4 font-medium">Deny after</th>
            <th className="text-right py-3 pr-4 font-medium">Escalate before</th>
            <th className="text-right py-3 pr-4 font-medium">Escalate after</th>
            <th className="text-right py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-dark-100">
          {versions.map((version) => (
            <tr key={version.policy_version_id}>
              <td className="py-3 pr-4 text-white font-medium">{version.version}</td>
              <td className="py-3 pr-4 text-gray-300 font-mono text-xs">{version.agent_id}</td>
              <td className="py-3 pr-4 text-gray-400 max-w-sm truncate">{version.label}</td>
              <td className="py-3 pr-4 text-right text-gray-300 font-mono">
                {version.deny_rate_before.toFixed(1)}%
              </td>
              <td className="py-3 pr-4 text-right text-white font-mono">
                {version.deny_rate_after.toFixed(1)}%
              </td>
              <td className="py-3 pr-4 text-right text-gray-300 font-mono">
                {version.escalation_rate_before.toFixed(1)}%
              </td>
              <td className="py-3 pr-4 text-right text-white font-mono">
                {version.escalation_rate_after.toFixed(1)}%
              </td>
              <td className="py-3 text-right">
                <div className="flex items-center justify-end gap-3">
                  <Link
                    to="/policy-manager"
                    className="text-xs text-sardis-400 hover:text-sardis-300 transition-colors"
                  >
                    Policy
                  </Link>
                  <Link
                    to="/simulation"
                    className="text-xs text-gray-400 hover:text-white transition-colors"
                  >
                    Scenario test
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SuggestionCard({ suggestion }: { suggestion: PolicyAnalyticsSuggestion }) {
  return (
    <div className={clsx('card border p-5 flex flex-col gap-3', suggestionClasses(suggestion.severity))}>
      <div className="flex items-start gap-3">
        <Lightbulb className="w-5 h-5 text-sardis-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <p className="text-sm font-semibold text-white">{suggestion.title}</p>
            <span className="text-xs px-2 py-0.5 rounded font-medium bg-dark-200 text-gray-400 uppercase">
              {suggestion.severity}
            </span>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">{suggestion.body}</p>
        </div>
      </div>
      {suggestion.action_label && (
        <div className="flex justify-end">
          <Link
            to="/policy-manager"
            className="text-xs font-medium px-3 py-1.5 bg-dark-200 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors rounded"
          >
            {suggestion.action_label}
          </Link>
        </div>
      )}
    </div>
  )
}

export default function PolicyAnalyticsPage() {
  const {
    period,
    setPeriod,
    loading,
    refreshing,
    error,
    summary,
    dailyOutcomes,
    denyReasons,
    policyVersions,
    suggestions,
    refresh,
  } = usePolicyAnalytics()

  const hasData = summary.total_checks > 0 || dailyOutcomes.some((row) => row.allowed + row.denied + row.escalated > 0)

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Policy Analytics</h1>
          <p className="text-gray-400 mt-1">
            Live policy outcome feedback driven by recorded policy decisions, not mock dashboards.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(['24h', '7d', '30d'] as Period[]).map((value) => (
            <button
              key={value}
              onClick={() => setPeriod(value)}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium transition-colors',
                period === value
                  ? 'bg-sardis-500 text-dark-400'
                  : 'bg-dark-200 text-gray-400 hover:bg-dark-100',
              )}
            >
              {value}
            </button>
          ))}
          <button
            onClick={refresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium border border-dark-100 text-gray-300 hover:text-white hover:border-sardis-500/30 transition-colors disabled:opacity-50"
          >
            <ArrowsClockwise className={clsx('w-4 h-4', refreshing && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-3 text-gray-400 py-10">
          <SpinnerGap className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading policy analytics…</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-3 px-4 py-3 border border-red-500/20 bg-red-500/5 text-red-400">
          <Warning className="w-4 h-4 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      ) : !hasData ? (
        <div className="border border-dark-100 bg-dark-300 p-8 text-center space-y-3">
          <ChartBar className="w-8 h-8 text-gray-600 mx-auto" />
          <h2 className="text-lg font-semibold text-white">No live policy outcome data yet</h2>
          <p className="text-sm text-gray-500 max-w-xl mx-auto">
            This page becomes useful once live policy decisions are recorded. Until then, use
            Policy Manager and Simulation to define rules, then come back here when real traffic
            starts generating outcome evidence.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              to="/policy-manager"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-sardis-400 border border-sardis-500/30 hover:bg-sardis-500/10 transition-colors"
            >
              Policy Manager
              <ArrowSquareOut className="w-3 h-3" />
            </Link>
            <Link
              to="/simulation"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-gray-300 border border-dark-100 hover:border-sardis-500/30 hover:text-sardis-400 transition-colors"
            >
              Scenario Testing
              <ArrowSquareOut className="w-3 h-3" />
            </Link>
          </div>
        </div>
      ) : (
        <>
          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <ChartBar className="w-5 h-5 text-sardis-400" />
              Outcome Summary
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label={`Total checks (${period})`}
                value={summary.total_checks.toLocaleString()}
                sub="recorded policy decisions"
                accent="gray"
              />
              <StatCard
                label="Allow rate"
                value={`${summary.allow_rate.toFixed(1)}%`}
                sub={`${summary.allowed.toLocaleString()} allowed`}
                accent="green"
              />
              <StatCard
                label="Deny rate"
                value={`${summary.deny_rate.toFixed(1)}%`}
                sub={`${summary.denied.toLocaleString()} denied`}
                accent="red"
              />
              <StatCard
                label="Escalation rate"
                value={`${summary.escalation_rate.toFixed(1)}%`}
                sub={`${summary.escalated.toLocaleString()} approval-required`}
                accent="yellow"
              />
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <ArrowsClockwise className="w-5 h-5 text-sardis-400" />
              Outcome Over Time
            </h2>
            <div className="card p-6">
              <OutcomeBarChart data={dailyOutcomes} />
            </div>
          </section>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            <section>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-400" />
                Top Deny Reasons
              </h2>
              <div className="card p-6">
                <DenyReasonsTable reasons={denyReasons} />
                <p className="text-xs text-gray-500 mt-4">
                  Trends compare the last 7 days to the preceding 7-day window.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-sardis-400" />
                Policy Version Impact
              </h2>
              <div className="card p-6">
                <PolicyVersionTable versions={policyVersions} />
              </div>
            </section>
          </div>

          <section>
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-sardis-400" />
              Deterministic Tuning Suggestions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {suggestions.map((suggestion) => (
                <SuggestionCard key={suggestion.id} suggestion={suggestion} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
