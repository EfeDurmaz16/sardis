/**
 * Workflow Templates — Design Partner Gallery
 *
 * Grid of opinionated template cards for common pilot workflows.
 * Each card shows category, limits, and approval threshold.
 * "Use Template" opens a detail panel with setup checklist and
 * a one-click "Apply to Policy Manager" action.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  AirplaneTilt,
  ArrowSquareOut,
  ArrowsLeftRight,
  CaretLeft,
  CaretRight,
  CheckCircle,
  ClipboardText,
  Copy,
  GearSix,
  ListChecks,
  Shield,
  ShoppingCart,
  SpinnerGap,
  WarningCircle,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { Link, useNavigate } from 'react-router-dom'
import { templatesApi } from '../api/client'

// ── Types ────────────────────────────────────────────────────────────────────

interface ApprovalConfig {
  require_approval_above: number
  auto_approve_below: number
  approval_timeout_hours: number
  notify_channels: string[]
  multi_sig_above?: number
  escrow_enabled?: boolean
}

interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  policy_text: string
  approval_config: ApprovalConfig
  evidence_expectations: string[]
  setup_steps: string[]
  assumptions: string[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CATEGORY_META: Record<string, { label: string; icon: any; color: string }> = {
  procurement: {
    label: 'Procurement',
    icon: ShoppingCart,
    color: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  },
  travel: {
    label: 'Travel & Expense',
    icon: AirplaneTilt,
    color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  },
  'agent-to-agent': {
    label: 'Agent-to-Agent',
    icon: ArrowsLeftRight,
    color: 'text-sardis-400 bg-sardis-500/10 border-sardis-500/30',
  },
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function categoryMeta(category: string): { label: string; icon: any; color: string } {
  return (
    CATEGORY_META[category] ?? {
      label: category,
      icon: GearSix,
      color: 'text-gray-400 bg-gray-500/10 border-gray-500/30',
    }
  )
}

function formatCurrency(value: number) {
  return `$${value.toLocaleString()}`
}

// ── Template Card ─────────────────────────────────────────────────────────────

interface TemplateCardProps {
  template: WorkflowTemplate
  onSelect: (t: WorkflowTemplate) => void
}

function TemplateCard({ template, onSelect }: TemplateCardProps) {
  const meta = categoryMeta(template.category)
  const Icon = meta.icon
  const cfg = template.approval_config

  return (
    <div className="bg-dark-200 border border-dark-100 hover:border-sardis-500/40 transition-all duration-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-dark-100">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={clsx('p-2 border', meta.color)}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-base">{template.name}</h3>
              <span
                className={clsx(
                  'inline-block mt-1 px-2 py-0.5 text-xs font-medium border',
                  meta.color
                )}
              >
                {meta.label}
              </span>
            </div>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-400 leading-relaxed">{template.description}</p>
      </div>

      {/* Key stats */}
      <div className="px-6 py-4 grid grid-cols-2 gap-3 border-b border-dark-100">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Auto-approve below</p>
          <p className="mt-1 text-sardis-400 font-mono font-semibold">
            {formatCurrency(cfg.auto_approve_below)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Requires approval above</p>
          <p className="mt-1 text-yellow-400 font-mono font-semibold">
            {formatCurrency(cfg.require_approval_above)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Approval timeout</p>
          <p className="mt-1 text-white font-mono">{cfg.approval_timeout_hours}h</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider">Setup steps</p>
          <p className="mt-1 text-white font-mono">{template.setup_steps.length}</p>
        </div>
      </div>

      {/* Action */}
      <div className="p-6 mt-auto">
        <button
          onClick={() => onSelect(template)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-sardis-500/10 hover:bg-sardis-500/20 text-sardis-400 border border-sardis-500/30 hover:border-sardis-500/60 transition-all duration-200 text-sm font-medium"
        >
          Use Template
          <CaretRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// ── Copy Button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [text])

  return (
    <button
      onClick={copy}
      className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-400 hover:text-white border border-dark-100 hover:border-gray-500 transition-all duration-200"
    >
      {copied ? (
        <>
          <CheckCircle className="w-3.5 h-3.5 text-sardis-400" />
          Copied
        </>
      ) : (
        <>
          <Copy className="w-3.5 h-3.5" />
          Copy
        </>
      )}
    </button>
  )
}

// ── Detail Panel ──────────────────────────────────────────────────────────────

type DetailTab = 'setup' | 'policy' | 'approval' | 'evidence'

interface DetailPanelProps {
  template: WorkflowTemplate
  onBack: () => void
  onApply: (policyText: string) => void
}

function DetailPanel({ template, onBack, onApply }: DetailPanelProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>('setup')
  const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set())
  const meta = categoryMeta(template.category)
  const Icon = meta.icon
  const cfg = template.approval_config

  const toggleStep = (index: number) => {
    setCheckedSteps((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tabs: { id: DetailTab; label: string; icon: any }[] = [
    { id: 'setup', label: 'Setup Steps', icon: ListChecks },
    { id: 'policy', label: 'Policy Text', icon: Shield },
    { id: 'approval', label: 'Approval Config', icon: ClipboardText },
    { id: 'evidence', label: 'Evidence', icon: CheckCircle },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Back + header */}
      <div>
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-4"
        >
          <CaretLeft className="w-4 h-4" />
          All Templates
        </button>

        <div className="flex items-start gap-4">
          <div className={clsx('p-3 border', meta.color)}>
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">{template.name}</h2>
            <span className={clsx('inline-block mt-1 px-2 py-0.5 text-xs font-medium border', meta.color)}>
              {meta.label}
            </span>
            <p className="mt-2 text-sm text-gray-400 max-w-2xl">{template.description}</p>
          </div>
        </div>
      </div>

      {/* Key numbers banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Auto-approve below', value: formatCurrency(cfg.auto_approve_below), color: 'text-sardis-400' },
          { label: 'Requires approval above', value: formatCurrency(cfg.require_approval_above), color: 'text-yellow-400' },
          { label: 'Approval timeout', value: `${cfg.approval_timeout_hours}h`, color: 'text-white' },
          {
            label: cfg.escrow_enabled ? 'Escrow' : cfg.multi_sig_above ? 'Multi-sig above' : 'Notify via',
            value: cfg.escrow_enabled
              ? 'Enabled'
              : cfg.multi_sig_above
              ? formatCurrency(cfg.multi_sig_above)
              : cfg.notify_channels.join(', '),
            color: 'text-white',
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-dark-200 border border-dark-100 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
            <p className={clsx('mt-1 font-mono font-semibold', color)}>{value}</p>
          </div>
        ))}
      </div>

      {/* Tab navigation */}
      <div className="border-b border-dark-100">
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const TabIcon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all duration-200',
                  activeTab === tab.id
                    ? 'border-sardis-500 text-sardis-400'
                    : 'border-transparent text-gray-400 hover:text-white'
                )}
              >
                <TabIcon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'setup' && (
          <div className="space-y-3">
            <p className="text-sm text-gray-400">
              Check off each step as you complete setup. Progress is tracked locally.
            </p>
            <div className="space-y-2">
              {template.setup_steps.map((step, i) => (
                <button
                  key={i}
                  onClick={() => toggleStep(i)}
                  className={clsx(
                    'w-full flex items-start gap-3 p-4 text-left border transition-all duration-200',
                    checkedSteps.has(i)
                      ? 'bg-sardis-500/5 border-sardis-500/30 text-gray-400'
                      : 'bg-dark-200 border-dark-100 text-white hover:border-dark-50'
                  )}
                >
                  <div
                    className={clsx(
                      'flex-shrink-0 w-5 h-5 mt-0.5 border-2 flex items-center justify-center transition-all',
                      checkedSteps.has(i)
                        ? 'bg-sardis-500 border-sardis-500'
                        : 'border-gray-600'
                    )}
                  >
                    {checkedSteps.has(i) && <CheckCircle className="w-3.5 h-3.5 text-dark-400" />}
                  </div>
                  <span className={clsx('text-sm', checkedSteps.has(i) && 'line-through')}>
                    <span className="text-gray-500 mr-2 font-mono text-xs">{i + 1}.</span>
                    {step}
                  </span>
                </button>
              ))}
            </div>
            {checkedSteps.size === template.setup_steps.length && template.setup_steps.length > 0 && (
              <div className="flex items-center gap-2 p-3 bg-sardis-500/10 border border-sardis-500/30 text-sardis-400 text-sm">
                <CheckCircle className="w-4 h-4" />
                All setup steps complete. Your agent is ready.
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
              <Link
                to="/go-live"
                className="flex items-center justify-center gap-2 px-4 py-2.5 border border-dark-100 text-sm text-gray-300 hover:text-white hover:border-sardis-500/40 transition-all duration-200"
              >
                <ListChecks className="w-4 h-4" />
                Open Go Live Checklist
              </Link>
              <Link
                to="/control-center"
                className="flex items-center justify-center gap-2 px-4 py-2.5 border border-dark-100 text-sm text-gray-300 hover:text-white hover:border-sardis-500/40 transition-all duration-200"
              >
                <ArrowSquareOut className="w-4 h-4" />
                Open Control Center
              </Link>
            </div>

            {/* Assumptions */}
            <div className="mt-6 pt-6 border-t border-dark-100">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Template Assumptions</h4>
              <ul className="space-y-2">
                {template.assumptions.map((assumption, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                    <span className="text-sardis-500 mt-0.5 flex-shrink-0">–</span>
                    {assumption}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'policy' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-400">
                Natural language policy definition. Copy and paste into Policy Manager or click Apply.
              </p>
              <CopyButton text={template.policy_text} />
            </div>
            <div className="bg-dark-300 border border-dark-100 p-5">
              <pre className="text-sm text-gray-200 whitespace-pre-wrap font-mono leading-relaxed">
                {template.policy_text}
              </pre>
            </div>
            <button
              onClick={() => onApply(template.policy_text)}
              className="flex items-center gap-2 px-4 py-2.5 bg-sardis-500 hover:bg-sardis-600 text-dark-400 font-semibold text-sm transition-all duration-200"
            >
              <ArrowSquareOut className="w-4 h-4" />
              Apply to Policy Manager
            </button>
          </div>
        )}

        {activeTab === 'approval' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Default approval workflow configuration shipped with this template.
            </p>
            <div className="bg-dark-200 border border-dark-100 divide-y divide-dark-100">
              {Object.entries(cfg).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between px-5 py-3.5">
                  <span className="text-sm text-gray-400 font-mono">{key}</span>
                  <span className="text-sm text-white font-mono">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'evidence' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Evidence artefacts collected automatically for every transaction using this template.
            </p>
            <ul className="space-y-2">
              {template.evidence_expectations.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 p-4 bg-dark-200 border border-dark-100 text-sm text-gray-200"
                >
                  <CheckCircle className="w-4 h-4 text-sardis-400 flex-shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function WorkflowTemplatesPage() {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<WorkflowTemplate | null>(null)

  useEffect(() => {
    setLoading(true)
    templatesApi
      .list()
      .then((data) => setTemplates(data as unknown as WorkflowTemplate[]))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const handleApply = useCallback(
    (policyText: string) => {
      // Navigate to Policy Manager with the policy text pre-filled via URL state
      navigate('/policy-manager', { state: { prefillPolicy: policyText } })
    },
    [navigate]
  )

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold font-display text-white">Workflow Templates</h1>
        <p className="mt-1 text-gray-400 text-sm">
          Opinionated configurations for the most common design-partner pilot workflows. Pick a
          template, follow the setup checklist, and apply the policy in one click.
        </p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 text-gray-400 py-12 justify-center">
          <SpinnerGap className="w-5 h-5 animate-spin" />
          Loading templates...
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          <WarningCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Detail panel */}
      {!loading && !error && selected && (
        <DetailPanel
          template={selected}
          onBack={() => setSelected(null)}
          onApply={handleApply}
        />
      )}

      {/* Template grid */}
      {!loading && !error && !selected && templates.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {templates.map((t) => (
            <TemplateCard key={t.id} template={t} onSelect={setSelected} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && !selected && templates.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <GearSix className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No templates available.</p>
        </div>
      )}
    </div>
  )
}
