/**
 * Environment Templates — Sandbox / Test / Live Lane Configs
 *
 * Three pre-built environment configurations with provider checklists,
 * policy defaults, and safety settings. One-click copy of env vars to
 * clipboard reduces pilot setup from hours to minutes.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  ArrowSquareOut,
  CaretDown,
  CaretUp,
  Check,
  CheckCircle,
  Circle,
  Copy,
  Cpu,
  Flask,
  Rocket,
  Scroll,
  Shield,
  SpinnerGap,
  Tag,
  WarningCircle,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { environmentTemplatesApi, type EnvironmentTemplate, type ProviderConfig } from '../api/client'

// ── Lane metadata ────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const LANE_META: Record<string, { label: string; icon: any; color: string; badge: string }> = {
  sandbox: {
    label: 'Sandbox',
    icon: Flask,
    color: 'border-blue-500/40 bg-blue-500/5',
    badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  },
  test: {
    label: 'Test',
    icon: Cpu,
    color: 'border-yellow-500/40 bg-yellow-500/5',
    badge: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  },
  live: {
    label: 'Live',
    icon: Rocket,
    color: 'border-sardis-500/40 bg-sardis-500/5',
    badge: 'bg-sardis-500/20 text-sardis-300 border-sardis-500/30',
  },
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function laneMeta(lane: string): { label: string; icon: any; color: string; badge: string } {
  return (
    LANE_META[lane] ?? {
      label: lane,
      icon: Flask,
      color: 'border-zinc-600 bg-zinc-800/50',
      badge: 'bg-zinc-700 text-zinc-300 border-zinc-600',
    }
  )
}

// ── Provider row ─────────────────────────────────────────────────────────────

function ProviderRow({ provider }: { provider: ProviderConfig }) {
  const isOptional = provider.status === 'optional'
  const isConfigured = provider.status === 'configured'

  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <div className="flex items-center gap-2 min-w-0">
        {isConfigured ? (
          <CheckCircle className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
        ) : (
          <Circle
            className={clsx(
              'h-3.5 w-3.5 shrink-0',
              isOptional ? 'text-zinc-500' : 'text-zinc-400',
            )}
          />
        )}
        <span
          className={clsx(
            'truncate',
            isOptional ? 'text-zinc-400' : 'text-zinc-200',
          )}
        >
          {provider.name}
        </span>
        {isOptional && (
          <span className="shrink-0 rounded border border-zinc-700 bg-zinc-800 px-1 py-0 text-[10px] text-zinc-500">
            optional
          </span>
        )}
        {provider.required && !isOptional && (
          <span className="shrink-0 rounded border border-zinc-700 bg-zinc-800 px-1 py-0 text-[10px] text-zinc-500">
            required
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 ml-2 shrink-0">
        <code className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-400">
          {provider.env_var}
        </code>
        {provider.docs_url && (
          <a
            href={provider.docs_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-500 hover:text-zinc-300 transition-colors"
            title="View docs"
          >
            <ArrowSquareOut className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  )
}

// ── Safety badge ─────────────────────────────────────────────────────────────

function SafetyBadge({ label, active }: { label: string; active: boolean }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium',
        active
          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
          : 'border-zinc-700 bg-zinc-800 text-zinc-500',
      )}
    >
      {label}
    </span>
  )
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyEnvButton({ envVars }: { envVars: Record<string, string> }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    const text = Object.entries(envVars)
      .map(([k, v]) => `${k}=${v}`)
      .join('\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [envVars])

  return (
    <button
      onClick={handleCopy}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs font-medium transition-all',
        copied
          ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
          : 'border-zinc-600 bg-zinc-800 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-700',
      )}
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5" />
          Copied!
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          Copy .env
        </>
      )}
    </button>
  )
}

// ── Template card ─────────────────────────────────────────────────────────────

function TemplateCard({ template }: { template: EnvironmentTemplate }) {
  const [expanded, setExpanded] = useState(false)
  const meta = laneMeta(template.lane)
  const LaneIcon = meta.icon

  const safetyEntries = Object.entries(template.safety_defaults)

  const requiredProviders = template.providers.filter((p) => p.required)
  const optionalProviders = template.providers.filter((p) => !p.required)

  return (
    <div
      className={clsx(
        'flex flex-col rounded-xl border p-5 transition-shadow hover:shadow-lg hover:shadow-black/20',
        meta.color,
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-800/80 border border-zinc-700">
            <LaneIcon className="h-4 w-4 text-zinc-300" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-zinc-100 truncate">{template.name}</h3>
            <span
              className={clsx(
                'mt-0.5 inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
                meta.badge,
              )}
            >
              {meta.label}
            </span>
          </div>
        </div>
        <CopyEnvButton envVars={template.env_vars} />
      </div>

      {/* Description */}
      <p className="mt-3 text-xs text-zinc-400 leading-relaxed">{template.description}</p>

      {/* Recommended for tags */}
      {template.recommended_for.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {template.recommended_for.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded border border-zinc-700 bg-zinc-800/60 px-1.5 py-0.5 text-[10px] text-zinc-400"
            >
              <Tag className="h-2.5 w-2.5" />
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Safety defaults row */}
      <div className="mt-4 flex flex-wrap gap-1.5">
        {safetyEntries.map(([key, val]) => (
          <SafetyBadge
            key={key}
            label={key.replace(/_/g, ' ')}
            active={val === true || val === 'armed'}
          />
        ))}
      </div>

      {/* Expand/collapse toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="mt-4 flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        {expanded ? (
          <>
            <CaretUp className="h-3.5 w-3.5" />
            Hide details
          </>
        ) : (
          <>
            <CaretDown className="h-3.5 w-3.5" />
            Show providers &amp; policy
          </>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Providers */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Cpu className="h-3.5 w-3.5 text-zinc-400" />
              <span className="text-xs font-medium text-zinc-300">Providers</span>
            </div>
            <div className="divide-y divide-zinc-700/50 rounded-lg border border-zinc-700 bg-zinc-900/60 px-3">
              {requiredProviders.map((p) => (
                <ProviderRow key={p.env_var} provider={p} />
              ))}
              {optionalProviders.map((p) => (
                <ProviderRow key={p.env_var} provider={p} />
              ))}
            </div>
          </div>

          {/* Policy defaults */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Scroll className="h-3.5 w-3.5 text-zinc-400" />
              <span className="text-xs font-medium text-zinc-300">Policy Defaults</span>
            </div>
            <p className="rounded-lg border border-zinc-700 bg-zinc-900/60 px-3 py-2.5 text-xs text-zinc-400 leading-relaxed">
              {template.policy_defaults}
            </p>
          </div>

          {/* Env vars */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <Shield className="h-3.5 w-3.5 text-zinc-400" />
              <span className="text-xs font-medium text-zinc-300">Environment Variables</span>
            </div>
            <div className="rounded-lg border border-zinc-700 bg-zinc-900/60 px-3 py-2.5 font-mono text-[11px] text-zinc-400 space-y-0.5">
              {Object.entries(template.env_vars).map(([k, v]) => (
                <div key={k}>
                  <span className="text-zinc-300">{k}</span>
                  <span className="text-zinc-600">=</span>
                  <span className="text-emerald-400">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function EnvironmentTemplatesPage() {
  const [templates, setTemplates] = useState<EnvironmentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    environmentTemplatesApi
      .list()
      .then(setTemplates)
      .catch((err) => setError(err.message ?? 'Failed to load templates'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-100">Environment Templates</h1>
        <p className="mt-1 text-sm text-zinc-400">
          Pre-built configurations for sandbox, test, and live lanes. Copy the env vars, apply the
          policy, and you are running in minutes.
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <SpinnerGap className="h-4 w-4 animate-spin" />
          Loading templates&hellip;
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <WarningCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Cards grid */}
      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
          {templates.map((t) => (
            <TemplateCard key={t.id} template={t} />
          ))}
        </div>
      )}

      {/* Footer note */}
      {!loading && !error && templates.length > 0 && (
        <p className="text-xs text-zinc-600">
          Provider status is shown as configured once the corresponding env var is detected at
          runtime. Click &quot;Copy .env&quot; to get the starter values for each lane.
        </p>
      )}
    </div>
  )
}
