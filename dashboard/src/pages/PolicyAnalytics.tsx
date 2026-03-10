/**
 * Policy Analytics Page — live policy outcome feedback and tuning surface
 *
 * Sections:
 *  1. Outcome Summary  — top stats for 24h / 7d / 30d
 *  2. Outcome Over Time — CSS-based stacked bar chart (no library dep)
 *  3. Top Deny Reasons — reason table with trend indicators
 *  4. Policy Version Impact — timeline showing before/after metrics
 *  5. Tuning Suggestions — deterministic, rule-based suggestion cards
 */

import { useState, useMemo } from 'react'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  XCircle,
  Clock,
  Lightbulb,
  GitBranch,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
import clsx from 'clsx'

// ── Types ────────────────────────────────────────────────────────────────────

type Period = '24h' | '7d' | '30d'

interface OutcomeSummary {
  total_checks: number
  allowed: number
  denied: number
  escalated: number
  allow_rate: number
  deny_rate: number
  escalation_rate: number
}

interface DailyOutcome {
  date: string
  allowed: number
  denied: number
  escalated: number
}

interface DenyReason {
  reason: string
  count: number
  pct_of_denials: number
  trend: 'up' | 'down' | 'flat'
}

interface PolicyVersion {
  version: string
  deployed_at: string
  label: string
  deny_rate_before: number
  deny_rate_after: number
  escalation_rate_before: number
  escalation_rate_after: number
}

interface TuningSuggestion {
  id: string
  severity: 'info' | 'warn' | 'action'
  title: string
  body: string
  action_label?: string
}

interface PolicyAnalyticsData {
  summary_24h: OutcomeSummary
  summary_7d: OutcomeSummary
  summary_30d: OutcomeSummary
  daily_outcomes: DailyOutcome[]
  deny_reasons: DenyReason[]
  policy_versions: PolicyVersion[]
  suggestions: TuningSuggestion[]
}

// ── Mock data ─────────────────────────────────────────────────────────────────

function buildSummary(
  total: number,
  allowPct: number,
  denyPct: number,
  escalPct: number,
): OutcomeSummary {
  const allowed = Math.round(total * allowPct)
  const denied = Math.round(total * denyPct)
  const escalated = Math.round(total * escalPct)
  return {
    total_checks: total,
    allowed,
    denied,
    escalated,
    allow_rate: allowPct * 100,
    deny_rate: denyPct * 100,
    escalation_rate: escalPct * 100,
  }
}

const MOCK_DATA: PolicyAnalyticsData = {
  summary_24h: buildSummary(214, 0.87, 0.09, 0.04),
  summary_7d: buildSummary(1482, 0.84, 0.12, 0.04),
  summary_30d: buildSummary(6341, 0.83, 0.13, 0.04),

  daily_outcomes: [
    { date: 'Feb 09', allowed: 182, denied: 28, escalated: 7 },
    { date: 'Feb 10', allowed: 195, denied: 31, escalated: 9 },
    { date: 'Feb 11', allowed: 170, denied: 25, escalated: 6 },
    { date: 'Feb 12', allowed: 210, denied: 38, escalated: 10 },
    { date: 'Feb 13', allowed: 188, denied: 29, escalated: 8 },
    { date: 'Feb 14', allowed: 164, denied: 22, escalated: 5 },
    { date: 'Feb 15', allowed: 201, denied: 30, escalated: 7 },
    { date: 'Feb 16', allowed: 220, denied: 35, escalated: 9 },
    { date: 'Feb 17', allowed: 196, denied: 28, escalated: 6 },
    { date: 'Feb 18', allowed: 175, denied: 20, escalated: 5 },
    { date: 'Feb 19', allowed: 188, denied: 24, escalated: 6 },
    { date: 'Feb 20', allowed: 210, denied: 27, escalated: 7 },
    { date: 'Feb 21', allowed: 199, denied: 25, escalated: 5 },
    { date: 'Feb 22', allowed: 215, denied: 31, escalated: 8 },
    { date: 'Feb 23', allowed: 230, denied: 34, escalated: 9 },
    { date: 'Feb 24', allowed: 205, denied: 28, escalated: 7 },
    { date: 'Feb 25', allowed: 190, denied: 22, escalated: 5 },
    { date: 'Feb 26', allowed: 225, denied: 26, escalated: 6 },
    { date: 'Feb 27', allowed: 240, denied: 30, escalated: 8 },
    { date: 'Feb 28', allowed: 218, denied: 24, escalated: 6 },
    { date: 'Mar 01', allowed: 198, denied: 20, escalated: 5 },
    { date: 'Mar 02', allowed: 210, denied: 22, escalated: 5 },
    { date: 'Mar 03', allowed: 225, denied: 18, escalated: 4 },
    { date: 'Mar 04', allowed: 232, denied: 15, escalated: 4 },
    { date: 'Mar 05', allowed: 245, denied: 14, escalated: 3 },
    { date: 'Mar 06', allowed: 250, denied: 12, escalated: 3 },
    { date: 'Mar 07', allowed: 248, denied: 11, escalated: 3 },
    { date: 'Mar 08', allowed: 260, denied: 10, escalated: 2 },
    { date: 'Mar 09', allowed: 255, denied: 10, escalated: 2 },
    { date: 'Mar 10', allowed: 214, denied: 19, escalated: 8 },
  ],

  deny_reasons: [
    { reason: 'per_transaction_limit', count: 312, pct_of_denials: 37.8, trend: 'down' },
    { reason: 'daily_limit_exceeded', count: 198, pct_of_denials: 24.0, trend: 'flat' },
    { reason: 'merchant_blocked', count: 141, pct_of_denials: 17.1, trend: 'up' },
    { reason: 'category_restricted', count: 88, pct_of_denials: 10.7, trend: 'flat' },
    { reason: 'time_window_violation', count: 54, pct_of_denials: 6.5, trend: 'down' },
    { reason: 'recipient_not_allowlisted', count: 32, pct_of_denials: 3.9, trend: 'up' },
  ],

  policy_versions: [
    {
      version: 'v1',
      deployed_at: '2026-01-15',
      label: 'Initial policy',
      deny_rate_before: 0,
      deny_rate_after: 18.4,
      escalation_rate_before: 0,
      escalation_rate_after: 6.2,
    },
    {
      version: 'v2',
      deployed_at: '2026-02-10',
      label: 'Raised daily limit $300 → $500',
      deny_rate_before: 18.4,
      deny_rate_after: 12.1,
      escalation_rate_before: 6.2,
      escalation_rate_after: 5.8,
    },
    {
      version: 'v3',
      deployed_at: '2026-03-05',
      label: 'Added Anthropic API to allowlist',
      deny_rate_before: 12.1,
      deny_rate_after: 4.2,
      escalation_rate_before: 5.8,
      escalation_rate_after: 3.1,
    },
  ],

  suggestions: [
    {
      id: 'raise-daily-limit',
      severity: 'action',
      title: 'Daily limit hit 8 times this week',
      body: 'Your daily limit ($500) was reached 8 times in the last 7 days, causing legitimate transactions to be denied. Consider raising it to $750.',
      action_label: 'Raise to $750',
    },
    {
      id: 'allowlist-anthropic',
      severity: 'action',
      title: '3 blocks from "Anthropic API"',
      body: 'Payments to Anthropic API were blocked 3 times by your merchant allowlist. If this is an expected vendor, consider adding it to the allowlist.',
      action_label: 'Add to allowlist',
    },
    {
      id: 'lower-escalation-threshold',
      severity: 'info',
      title: 'No escalations in 14 days',
      body: 'Your escalation threshold is set to $500, but you have had no escalations in 14 days. Consider lowering it to $200 to get earlier visibility on large transactions.',
      action_label: 'Lower threshold',
    },
    {
      id: 'review-category-blocks',
      severity: 'warn',
      title: '"travel" category blocked 18 times',
      body: 'The travel category was restricted 18 times this month. If your agents legitimately book travel, consider removing this category restriction.',
    },
  ],
}

// ── Hook ─────────────────────────────────────────────────────────────────────

function usePolicyAnalytics() {
  const [period, setPeriod] = useState<Period>('30d')
  const [loading] = useState(false)

  const data = MOCK_DATA

  const summary: OutcomeSummary = useMemo(() => {
    if (period === '24h') return data.summary_24h
    if (period === '7d') return data.summary_7d
    return data.summary_30d
  }, [period, data])

  // For 7d slice only last 7 days; for 24h only last day
  const dailyOutcomes: DailyOutcome[] = useMemo(() => {
    if (period === '24h') return data.daily_outcomes.slice(-1)
    if (period === '7d') return data.daily_outcomes.slice(-7)
    return data.daily_outcomes
  }, [period, data])

  return {
    period,
    setPeriod,
    loading,
    summary,
    dailyOutcomes,
    denyReasons: data.deny_reasons,
    policyVersions: data.policy_versions,
    suggestions: data.suggestions,
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string | number
  sub: string
  accent: 'green' | 'red' | 'yellow' | 'gray'
}) {
  const accentClass = {
    green: 'text-emerald-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    gray: 'text-gray-400',
  }[accent]

  return (
    <div className="card p-5">
      <p className="text-sm font-medium text-gray-400 mb-1">{label}</p>
      <p className={clsx('text-3xl font-bold', accentClass)}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{sub}</p>
    </div>
  )
}

function OutcomeBarChart({ data }: { data: DailyOutcome[] }) {
  const maxTotal = Math.max(...data.map((d) => d.allowed + d.denied + d.escalated), 1)

  return (
    <div className="space-y-1">
      {/* Legend */}
      <div className="flex gap-5 text-xs text-gray-400 mb-3">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-emerald-500 inline-block" />
          Allowed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" />
          Denied
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-yellow-500 inline-block" />
          Escalated
        </span>
      </div>

      {/* Bars */}
      <div className="flex items-end gap-1 h-48">
        {data.map((day) => {
          const total = day.allowed + day.denied + day.escalated
          const allowedPct = (day.allowed / maxTotal) * 100
          const deniedPct = (day.denied / maxTotal) * 100
          const escalatedPct = (day.escalated / maxTotal) * 100

          return (
            <div
              key={day.date}
              className="flex-1 flex flex-col justify-end gap-px group relative"
              style={{ height: '100%' }}
            >
              {/* Tooltip */}
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-10 hidden group-hover:block pointer-events-none">
                <div className="bg-dark-100 border border-dark-100/80 rounded px-2 py-1.5 text-xs whitespace-nowrap shadow-lg">
                  <p className="font-medium text-white mb-1">{day.date}</p>
                  <p className="text-emerald-400">{day.allowed} allowed</p>
                  <p className="text-red-400">{day.denied} denied</p>
                  <p className="text-yellow-400">{day.escalated} escalated</p>
                  <p className="text-gray-400 border-t border-gray-700 mt-1 pt-1">Total: {total}</p>
                </div>
              </div>

              <div className="flex flex-col gap-px justify-end" style={{ height: '100%' }}>
                <div
                  className="w-full bg-yellow-500/80 rounded-t-sm"
                  style={{ height: `${escalatedPct}%`, minHeight: escalatedPct > 0 ? 2 : 0 }}
                />
                <div
                  className="w-full bg-red-500/80"
                  style={{ height: `${deniedPct}%`, minHeight: deniedPct > 0 ? 2 : 0 }}
                />
                <div
                  className="w-full bg-emerald-500/80"
                  style={{ height: `${allowedPct}%`, minHeight: allowedPct > 0 ? 2 : 0 }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* X-axis labels — show only every ~5th to avoid crowding */}
      <div className="flex gap-1 mt-1">
        {data.map((day, i) => (
          <div key={day.date} className="flex-1 text-center">
            {(i === 0 || i === Math.floor(data.length / 2) || i === data.length - 1) ? (
              <span className="text-xs text-gray-500 truncate block">{day.date}</span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}

function TrendIcon({ trend }: { trend: 'up' | 'down' | 'flat' }) {
  if (trend === 'up') return <TrendingUp className="w-4 h-4 text-red-400" />
  if (trend === 'down') return <TrendingDown className="w-4 h-4 text-emerald-400" />
  return <Minus className="w-4 h-4 text-gray-500" />
}

function DenyReasonsTable({ reasons }: { reasons: DenyReason[] }) {
  const maxCount = Math.max(...reasons.map((r) => r.count), 1)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 uppercase tracking-wider border-b border-dark-100">
            <th className="pb-3 font-medium">Reason</th>
            <th className="pb-3 font-medium text-right">Count</th>
            <th className="pb-3 font-medium text-right">% of denials</th>
            <th className="pb-3 font-medium text-center">Trend</th>
            <th className="pb-3 font-medium w-32">Distribution</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-dark-100">
          {reasons.map((r) => (
            <tr key={r.reason} className="hover:bg-dark-200/40 transition-colors">
              <td className="py-3 pr-4">
                <code className="text-xs bg-dark-100 px-2 py-1 rounded text-gray-300 font-mono">
                  {r.reason}
                </code>
              </td>
              <td className="py-3 text-right font-semibold text-white">{r.count}</td>
              <td className="py-3 text-right text-gray-300">{r.pct_of_denials.toFixed(1)}%</td>
              <td className="py-3 text-center">
                <div className="flex justify-center">
                  <TrendIcon trend={r.trend} />
                </div>
              </td>
              <td className="py-3">
                <div className="h-1.5 bg-dark-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500/70 rounded-full"
                    style={{ width: `${(r.count / maxCount) * 100}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PolicyVersionTimeline({ versions }: { versions: PolicyVersion[] }) {
  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-3.5 top-0 bottom-0 w-px bg-dark-100" />

      <div className="space-y-6">
        {versions.map((v, i) => {
          const denyDelta = v.deny_rate_after - v.deny_rate_before
          const escalDelta = v.escalation_rate_after - v.escalation_rate_before
          const isLast = i === versions.length - 1

          return (
            <div key={v.version} className="relative flex gap-4 pl-10">
              {/* Dot */}
              <div
                className={clsx(
                  'absolute left-0 w-7 h-7 rounded-full flex items-center justify-center border-2',
                  isLast
                    ? 'bg-sardis-500/20 border-sardis-500 text-sardis-400'
                    : 'bg-dark-200 border-dark-100 text-gray-500',
                )}
              >
                <GitBranch className="w-3.5 h-3.5" />
              </div>

              <div className="flex-1 card p-4">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <span className="text-xs font-mono text-sardis-400 bg-sardis-500/10 px-2 py-0.5 rounded">
                      {v.version}
                    </span>
                    <p className="text-sm font-medium text-white mt-1.5">{v.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">Deployed {v.deployed_at}</p>
                  </div>

                  <div className="flex gap-6 text-xs">
                    {/* Deny rate delta */}
                    <div className="text-center">
                      <p className="text-gray-500 mb-1">Deny rate</p>
                      <p className="text-gray-400">{v.deny_rate_before.toFixed(1)}%</p>
                      <p
                        className={clsx(
                          'font-semibold',
                          denyDelta < 0 ? 'text-emerald-400' : denyDelta > 0 ? 'text-red-400' : 'text-gray-400',
                        )}
                      >
                        {denyDelta === 0
                          ? '—'
                          : `${denyDelta > 0 ? '+' : ''}${denyDelta.toFixed(1)}%`}
                      </p>
                      <p className="text-white">{v.deny_rate_after.toFixed(1)}%</p>
                    </div>

                    {/* Escalation rate delta */}
                    <div className="text-center">
                      <p className="text-gray-500 mb-1">Escalation</p>
                      <p className="text-gray-400">{v.escalation_rate_before.toFixed(1)}%</p>
                      <p
                        className={clsx(
                          'font-semibold',
                          escalDelta < 0
                            ? 'text-emerald-400'
                            : escalDelta > 0
                            ? 'text-red-400'
                            : 'text-gray-400',
                        )}
                      >
                        {escalDelta === 0
                          ? '—'
                          : `${escalDelta > 0 ? '+' : ''}${escalDelta.toFixed(1)}%`}
                      </p>
                      <p className="text-white">{v.escalation_rate_after.toFixed(1)}%</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const SEVERITY_STYLES = {
  action: {
    border: 'border-sardis-500/40',
    bg: 'bg-sardis-500/5',
    icon: <Lightbulb className="w-5 h-5 text-sardis-400 flex-shrink-0 mt-0.5" />,
    badge: 'bg-sardis-500/20 text-sardis-400',
    badgeText: 'Action',
  },
  warn: {
    border: 'border-yellow-500/40',
    bg: 'bg-yellow-500/5',
    icon: <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />,
    badge: 'bg-yellow-500/20 text-yellow-400',
    badgeText: 'Warning',
  },
  info: {
    border: 'border-blue-500/40',
    bg: 'bg-blue-500/5',
    icon: <Lightbulb className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />,
    badge: 'bg-blue-500/20 text-blue-400',
    badgeText: 'Info',
  },
} as const

function SuggestionCard({ suggestion }: { suggestion: TuningSuggestion }) {
  const style = SEVERITY_STYLES[suggestion.severity]

  return (
    <div className={clsx('card border p-5 flex flex-col gap-3', style.border, style.bg)}>
      <div className="flex items-start gap-3">
        {style.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <p className="text-sm font-semibold text-white">{suggestion.title}</p>
            <span className={clsx('text-xs px-2 py-0.5 rounded font-medium', style.badge)}>
              {style.badgeText}
            </span>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">{suggestion.body}</p>
        </div>
      </div>
      {suggestion.action_label && (
        <div className="flex justify-end">
          <button className="text-xs font-medium px-3 py-1.5 bg-dark-200 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors rounded">
            {suggestion.action_label}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PolicyAnalytics() {
  const {
    period,
    setPeriod,
    loading,
    summary,
    dailyOutcomes,
    denyReasons,
    policyVersions,
    suggestions,
  } = usePolicyAnalytics()

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Policy Analytics</h1>
          <p className="text-gray-400 mt-1">
            Live policy outcome feedback — see what your policies allow, deny, and escalate.
          </p>
        </div>

        {/* Period picker */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Period:</span>
          {(['24h', '7d', '30d'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={clsx(
                'px-3 py-1.5 text-sm font-medium transition-colors',
                period === p
                  ? 'bg-sardis-500 text-dark-400'
                  : 'bg-dark-200 text-gray-400 hover:bg-dark-100',
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* 1. Outcome Summary */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-sardis-400" />
          Outcome Summary
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label={`Total checks (${period})`}
            value={summary.total_checks.toLocaleString()}
            sub="policy evaluations"
            accent="gray"
          />
          <StatCard
            label="Allow rate"
            value={`${summary.allow_rate.toFixed(1)}%`}
            sub={`${summary.allowed.toLocaleString()} transactions`}
            accent="green"
          />
          <StatCard
            label="Deny rate"
            value={`${summary.deny_rate.toFixed(1)}%`}
            sub={`${summary.denied.toLocaleString()} blocked`}
            accent="red"
          />
          <StatCard
            label="Escalation rate"
            value={`${summary.escalation_rate.toFixed(1)}%`}
            sub={`${summary.escalated.toLocaleString()} escalated`}
            accent="yellow"
          />
        </div>
      </section>

      {/* 2. Outcome Over Time */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-sardis-400" />
          Outcome Over Time
          <span className="text-xs text-gray-500 font-normal ml-1">(last {period})</span>
        </h2>
        <div className="card p-6">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500" />
            </div>
          ) : (
            <OutcomeBarChart data={dailyOutcomes} />
          )}
        </div>
      </section>

      {/* 3 + 4 — side by side on large screens */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* 3. Top Deny Reasons */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <XCircle className="w-5 h-5 text-red-400" />
            Top Deny Reasons
          </h2>
          <div className="card p-6">
            <DenyReasonsTable reasons={denyReasons} />
            <p className="text-xs text-gray-500 mt-4">
              Trend shows change vs previous {period} period. Up = more denials (bad), down = fewer (good).
            </p>
          </div>
        </section>

        {/* 4. Policy Version Impact */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-sardis-400" />
            Policy Version Impact
          </h2>
          <div className="card p-6">
            <PolicyVersionTimeline versions={policyVersions} />
            <p className="text-xs text-gray-500 mt-4">
              Each row shows deny rate and escalation rate before and after a policy version was deployed.
              Green delta = improvement.
            </p>
          </div>
        </section>
      </div>

      {/* 5. Tuning Suggestions */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-sardis-400" />
          Tuning Suggestions
          <span className="text-xs text-gray-500 font-normal ml-1">
            — deterministic, based on your activity patterns
          </span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {suggestions.map((s) => (
            <SuggestionCard key={s.id} suggestion={s} />
          ))}
        </div>
      </section>
    </div>
  )
}
