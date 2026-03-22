"use client";
/**
 * Checkout Controls — operator-grade controls for hosted secure checkout.
 *
 * Two sections:
 *  1. Controls Config  — approval thresholds, KYC, chain/token restrictions,
 *                        evidence export, incident webhook, freeze-on-dispute
 *  2. Incidents        — table of checkout incidents with severity badges,
 *                        status, and auto-actions taken
 */

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  ShoppingCart,
  AlertTriangle,
  Settings2,
  Save,
  Loader2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
  Zap,
  FileSearch,
  Webhook,
  ExternalLink,
} from 'lucide-react'
import clsx from 'clsx'
import {
  checkoutControlsApi,
  type CheckoutControlConfig,
  type CheckoutIncidentResponse,
} from '@/api/client'

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  low: 'text-green-400 border-green-500/30 bg-green-500/10',
  medium: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
  high: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
  critical: 'text-red-400 border-red-500/30 bg-red-500/10',
}

const STATUS_COLORS: Record<string, string> = {
  open: 'text-red-400 border-red-500/30 bg-red-500/10',
  investigating: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
  resolved: 'text-green-400 border-green-500/30 bg-green-500/10',
}

const TYPE_LABELS: Record<string, string> = {
  dispute: 'Dispute',
  timeout: 'Timeout',
  fraud_flag: 'Fraud Flag',
  settlement_failure: 'Settlement Failure',
}

function Badge({
  children,
  color,
}: {
  children: React.ReactNode
  color: string
}) {
  return (
    <span className={clsx('px-2 py-0.5 text-xs border font-mono', color)}>
      {children}
    </span>
  )
}

function SectionHeader({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ElementType
  title: string
  description: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 bg-sardis-500/10 border border-sardis-500/20 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-sardis-400" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          <p className="text-sm text-gray-500 mt-0.5">{description}</p>
        </div>
      </div>
      {action}
    </div>
  )
}

// ── Controls Config Section ───────────────────────────────────────────────────

const DEFAULT_CONFIG: CheckoutControlConfig = {
  require_approval_above: null,
  require_kyc: false,
  allowed_chains: ['base'],
  allowed_tokens: ['USDC'],
  max_session_amount: null,
  evidence_export_auto: true,
  incident_webhook_url: null,
  freeze_on_dispute: true,
}

function ControlsConfigSection() {
  const [config, setConfig] = useState<CheckoutControlConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Local string states for comma-separated chain/token inputs
  const [chainsInput, setChainsInput] = useState('base')
  const [tokensInput, setTokensInput] = useState('USDC')

  useEffect(() => {
    checkoutControlsApi
      .getConfig()
      .then((cfg) => {
        setConfig(cfg)
        setChainsInput(cfg.allowed_chains.join(', '))
        setTokensInput(cfg.allowed_tokens.join(', '))
      })
      .catch(() => {
        // Use defaults if the endpoint is not yet available
        setConfig(DEFAULT_CONFIG)
      })
      .finally(() => setLoading(false))
  }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    setError(null)
    try {
      const updated: CheckoutControlConfig = {
        ...config,
        allowed_chains: chainsInput
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        allowed_tokens: tokensInput
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      }
      const result = await checkoutControlsApi.updateConfig(updated)
      setConfig(result)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [config, chainsInput, tokensInput])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400 py-8">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-sm">Loading config…</span>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Approval threshold */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
            Require Approval Above ($)
          </label>
          <input
            type="number"
            min={0}
            placeholder="No limit"
            value={config.require_approval_above ?? ''}
            onChange={(e) =>
              setConfig((c) => ({
                ...c,
                require_approval_above: e.target.value === '' ? null : Number(e.target.value),
              }))
            }
            className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Checkout sessions above this amount require operator approval.
          </p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
            Max Session Amount ($)
          </label>
          <input
            type="number"
            min={0}
            placeholder="No limit"
            value={config.max_session_amount ?? ''}
            onChange={(e) =>
              setConfig((c) => ({
                ...c,
                max_session_amount: e.target.value === '' ? null : Number(e.target.value),
              }))
            }
            className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Hard cap per checkout session. Sessions over this are rejected.
          </p>
        </div>
      </div>

      {/* Chains + tokens */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
            Allowed Chains
          </label>
          <input
            type="text"
            placeholder="base, polygon"
            value={chainsInput}
            onChange={(e) => setChainsInput(e.target.value)}
            className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500 font-mono"
          />
          <p className="text-xs text-gray-500 mt-1">Comma-separated chain names.</p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
            Allowed Tokens
          </label>
          <input
            type="text"
            placeholder="USDC, USDT"
            value={tokensInput}
            onChange={(e) => setTokensInput(e.target.value)}
            className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500 font-mono"
          />
          <p className="text-xs text-gray-500 mt-1">Comma-separated token symbols.</p>
        </div>
      </div>

      {/* Incident webhook */}
      <div>
        <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
          Incident Webhook URL
        </label>
        <input
          type="url"
          placeholder="https://ops.example.com/hooks/checkout-incident"
          value={config.incident_webhook_url ?? ''}
          onChange={(e) =>
            setConfig((c) => ({
              ...c,
              incident_webhook_url: e.target.value || null,
            }))
          }
          className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500 font-mono"
        />
        <p className="text-xs text-gray-500 mt-1">
          POST notifications are sent here for all checkout incidents.
        </p>
      </div>

      {/* Toggles */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            key: 'require_kyc' as const,
            label: 'Require KYC',
            description: 'Payer must pass KYC before checkout completes.',
            icon: Shield,
          },
          {
            key: 'evidence_export_auto' as const,
            label: 'Auto-Export Evidence',
            description: 'Automatically generate an evidence bundle on completion.',
            icon: FileSearch,
          },
          {
            key: 'freeze_on_dispute' as const,
            label: 'Freeze on Dispute',
            description: 'Auto-freeze the payer wallet when a dispute is filed.',
            icon: Zap,
          },
        ].map(({ key, label, description, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setConfig((c) => ({ ...c, [key]: !c[key] }))}
            className={clsx(
              'flex flex-col gap-2 p-4 border text-left transition-all duration-150',
              config[key]
                ? 'border-sardis-500/40 bg-sardis-500/5'
                : 'border-dark-100 bg-dark-200 hover:border-dark-50'
            )}
          >
            <div className="flex items-center justify-between">
              <Icon
                className={clsx(
                  'w-4 h-4',
                  config[key] ? 'text-sardis-400' : 'text-gray-500'
                )}
              />
              <div
                className={clsx(
                  'w-8 h-4 relative transition-colors duration-150',
                  config[key] ? 'bg-sardis-500' : 'bg-dark-100'
                )}
              >
                <div
                  className={clsx(
                    'absolute top-0.5 w-3 h-3 bg-white transition-transform duration-150',
                    config[key] ? 'translate-x-4' : 'translate-x-0.5'
                  )}
                />
              </div>
            </div>
            <span
              className={clsx(
                'text-sm font-medium',
                config[key] ? 'text-white' : 'text-gray-400'
              )}
            >
              {label}
            </span>
            <span className="text-xs text-gray-500 leading-snug">{description}</span>
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 px-4 py-2">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Save */}
      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className={clsx(
            'flex items-center gap-2 px-5 py-2 text-sm font-medium transition-all duration-150',
            saved
              ? 'bg-green-500/20 border border-green-500/30 text-green-400'
              : 'bg-sardis-500 text-dark-400 hover:bg-sardis-400 disabled:opacity-50'
          )}
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saving ? 'Saving…' : saved ? 'Saved' : 'Save Config'}
        </button>
      </div>
    </div>
  )
}

// ── Incidents Section ─────────────────────────────────────────────────────────

function IncidentsSection() {
  const [incidents, setIncidents] = useState<CheckoutIncidentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const data = await checkoutControlsApi.listIncidents(50)
      setIncidents(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div>
      <SectionHeader
        icon={AlertTriangle}
        title="Checkout Incidents"
        description="Disputes, fraud flags, timeouts, and settlement failures reported during checkout."
        action={
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 border border-dark-100 hover:text-white hover:border-gray-500 transition-all duration-150"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', refreshing && 'animate-spin')} />
            Refresh
          </button>
        }
      />

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 py-8">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading incidents…</span>
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 px-4 py-3">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      ) : incidents.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-gray-500">
          <CheckCircle2 className="w-10 h-10 text-green-500/40" />
          <p className="text-sm">No incidents reported. Checkout is healthy.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-100 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left py-3 pr-4 font-medium">Incident ID</th>
                <th className="text-left py-3 pr-4 font-medium">Session</th>
                <th className="text-left py-3 pr-4 font-medium">Type</th>
                <th className="text-left py-3 pr-4 font-medium">Severity</th>
                <th className="text-left py-3 pr-4 font-medium">Status</th>
                <th className="text-left py-3 pr-4 font-medium">Auto Actions</th>
                <th className="text-left py-3 font-medium">Time</th>
                <th className="text-right py-3 font-medium">Operator Flow</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {incidents.map((inc) => (
                <tr key={inc.incident_id} className="hover:bg-dark-200/50 transition-colors">
                  <td className="py-3 pr-4 font-mono text-sardis-400 text-xs">
                    {inc.incident_id}
                  </td>
                  <td className="py-3 pr-4 font-mono text-gray-300 text-xs">
                    {inc.session_id}
                  </td>
                  <td className="py-3 pr-4 text-gray-300">
                    {TYPE_LABELS[inc.incident_type] ?? inc.incident_type}
                  </td>
                  <td className="py-3 pr-4">
                    <Badge color={SEVERITY_COLORS[inc.severity] ?? 'text-gray-400 border-gray-500/30'}>
                      {inc.severity}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge color={STATUS_COLORS[inc.status] ?? 'text-gray-400 border-gray-500/30'}>
                      {inc.status}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 max-w-xs">
                    {inc.auto_actions_taken.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {inc.auto_actions_taken.map((a, i) => (
                          <span
                            key={i}
                            className="px-1.5 py-0.5 text-xs bg-dark-100 text-gray-400 border border-dark-50 font-mono"
                          >
                            {a}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-600 text-xs">—</span>
                    )}
                  </td>
                  <td className="py-3 text-gray-500 text-xs font-mono whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(inc.created_at).toLocaleString()}
                    </div>
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <Link
                        href="/control-center"
                        className="text-xs text-sardis-400 hover:text-sardis-300 transition-colors"
                      >
                        Control Center
                      </Link>
                      <Link
                        href="/evidence"
                        className="text-xs text-gray-400 hover:text-white transition-colors"
                      >
                        Evidence
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CheckoutControlsPage() {
  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-sardis-500/10 border border-sardis-500/20 flex items-center justify-center">
              <ShoppingCart className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white font-display">Checkout Controls</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                Operator-grade controls for hosted secure checkout — approval hooks, KYC, chain
                restrictions, evidence export, and incident management.
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500 max-w-2xl">
            Approval thresholds feed the shared approval queue, auto-exported evidence belongs in
            the same audit flow, and incident recovery should route operators back into the control
            center rather than a separate founder-only path.
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
            href="/evidence"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-300 border border-dark-100 hover:border-sardis-500/30 hover:text-sardis-400 transition-colors"
          >
            Evidence Explorer
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {/* Config section */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <SectionHeader
          icon={Settings2}
          title="Controls Configuration"
          description="Configure approval thresholds, allowed chains/tokens, KYC, evidence, and incident webhooks."
        />
        <ControlsConfigSection />
      </div>

      {/* Incidents section */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <IncidentsSection />
      </div>
    </div>
  )
}
