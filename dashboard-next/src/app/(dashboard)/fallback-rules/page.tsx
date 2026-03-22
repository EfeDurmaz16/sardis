"use client";
/**
 * FallbackPolicies — cross-rail fallback rules and degraded-mode policies.
 *
 * Two sections:
 *  1. Fallback Rules   — table with add/edit/delete for rail-pair rules
 *  2. Degraded Modes   — card per rail with current mode and edit controls
 */

import { useState, useEffect, useCallback } from 'react'
import {
  GitBranch,
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  Loader2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  Activity,
  type LucideIcon,
} from 'lucide-react'
import clsx from 'clsx'
import {
  fallbackPoliciesApi,
  type FallbackRule,
  type DegradedModePolicy,
} from '@/api/client'

// ── Constants ─────────────────────────────────────────────────────────────────

const RAILS = ['stablecoin', 'virtual_card', 'x402', 'bank_transfer'] as const
type Rail = (typeof RAILS)[number]

const TRIGGERS = ['failure', 'degraded', 'timeout', 'unsafe'] as const
const BEHAVIORS = [
  'retry_then_fallback',
  'immediate_fallback',
  'escalate',
  'block',
] as const

const MODE_COLORS: Record<string, string> = {
  normal: 'text-green-400 border-green-500/30 bg-green-500/10',
  degraded: 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10',
  maintenance: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
  disabled: 'text-red-400 border-red-500/30 bg-red-500/10',
}

const RAIL_LABELS: Record<Rail, string> = {
  stablecoin: 'Stablecoin',
  virtual_card: 'Virtual Card',
  x402: 'x402',
  bank_transfer: 'Bank Transfer',
}

// ── Shared primitives ─────────────────────────────────────────────────────────

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
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
  icon: LucideIcon
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

// ── Fallback Rule Form (inline modal) ─────────────────────────────────────────

const EMPTY_RULE: Omit<FallbackRule, 'id'> = {
  name: '',
  primary_rail: 'stablecoin',
  fallback_rail: 'virtual_card',
  trigger: 'failure',
  behavior: 'retry_then_fallback',
  max_retries: 2,
  retry_delay_seconds: 5,
  enabled: true,
  audit_log: true,
}

function RuleFormModal({
  initial,
  onSave,
  onClose,
}: {
  initial: Omit<FallbackRule, 'id'>
  onSave: (data: Omit<FallbackRule, 'id'>) => Promise<void>
  onClose: () => void
}) {
  const [form, setForm] = useState<Omit<FallbackRule, 'id'>>(initial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) {
      setError('Rule name is required')
      return
    }
    if (form.primary_rail === form.fallback_rail) {
      setError('Primary and fallback rails must be different')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await onSave(form)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const inputCls =
    'w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500'
  const selectCls =
    'w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-dark-300 border border-dark-100 w-full max-w-lg p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">
            {initial.name ? 'Edit Fallback Rule' : 'New Fallback Rule'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Rule Name
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="e.g. Stablecoin → Card on failure"
              className={inputCls}
            />
          </div>

          {/* Rail pair */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Primary Rail
              </label>
              <select
                value={form.primary_rail}
                onChange={(e) => set('primary_rail', e.target.value)}
                className={selectCls}
              >
                {RAILS.map((r) => (
                  <option key={r} value={r}>
                    {RAIL_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Fallback Rail
              </label>
              <select
                value={form.fallback_rail}
                onChange={(e) => set('fallback_rail', e.target.value)}
                className={selectCls}
              >
                {RAILS.map((r) => (
                  <option key={r} value={r}>
                    {RAIL_LABELS[r]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Trigger + Behavior */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Trigger
              </label>
              <select
                value={form.trigger}
                onChange={(e) => set('trigger', e.target.value)}
                className={selectCls}
              >
                {TRIGGERS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Behavior
              </label>
              <select
                value={form.behavior}
                onChange={(e) => set('behavior', e.target.value)}
                className={selectCls}
              >
                {BEHAVIORS.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Retries */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Max Retries
              </label>
              <input
                type="number"
                min={0}
                max={5}
                value={form.max_retries}
                onChange={(e) => set('max_retries', Number(e.target.value))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Retry Delay (s)
              </label>
              <input
                type="number"
                min={1}
                max={300}
                value={form.retry_delay_seconds}
                onChange={(e) => set('retry_delay_seconds', Number(e.target.value))}
                className={inputCls}
              />
            </div>
          </div>

          {/* Toggles */}
          <div className="flex items-center gap-6">
            {(
              [
                { key: 'enabled' as const, label: 'Enabled' },
                { key: 'audit_log' as const, label: 'Audit Log' },
              ] as const
            ).map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => set(key, !form[key])}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <div
                  className={clsx(
                    'w-8 h-4 relative transition-colors duration-150',
                    form[key] ? 'bg-sardis-500' : 'bg-dark-100'
                  )}
                >
                  <div
                    className={clsx(
                      'absolute top-0.5 w-3 h-3 bg-white transition-transform duration-150',
                      form[key] ? 'translate-x-4' : 'translate-x-0.5'
                    )}
                  />
                </div>
                <span className={form[key] ? 'text-white' : ''}>{label}</span>
              </button>
            ))}
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 px-3 py-2">
              <XCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 disabled:opacity-50 transition-all duration-150"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving…' : 'Save Rule'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-400 border border-dark-100 hover:text-white hover:border-gray-500 transition-all duration-150"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Fallback Rules Section ────────────────────────────────────────────────────

function FallbackRulesSection() {
  const [rules, setRules] = useState<FallbackRule[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<FallbackRule | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const data = await fallbackPoliciesApi.listRules()
      setRules(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rules')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleCreate = async (data: Omit<FallbackRule, 'id'>) => {
    const rule = await fallbackPoliciesApi.createRule(data)
    setRules((rs) => [...rs, rule])
    setCreating(false)
  }

  const handleUpdate = async (data: Omit<FallbackRule, 'id'>) => {
    if (!editing) return
    const updated = await fallbackPoliciesApi.updateRule(editing.id, data)
    setRules((rs) => rs.map((r) => (r.id === updated.id ? updated : r)))
    setEditing(null)
  }

  const handleDelete = async (id: string) => {
    setDeleting(id)
    try {
      await fallbackPoliciesApi.deleteRule(id)
      setRules((rs) => rs.filter((r) => r.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeleting(null)
    }
  }

  const handleToggle = async (rule: FallbackRule) => {
    const { id, ...rest } = rule
    const updated = await fallbackPoliciesApi.updateRule(id, {
      ...rest,
      enabled: !rule.enabled,
    })
    setRules((rs) => rs.map((r) => (r.id === updated.id ? updated : r)))
  }

  return (
    <div>
      <SectionHeader
        icon={GitBranch}
        title="Fallback Rules"
        description="Configure deterministic rail-pair fallback logic for failure, degraded, timeout, or unsafe triggers."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => load(true)}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 border border-dark-100 hover:text-white hover:border-gray-500 transition-all duration-150"
            >
              <RefreshCw className={clsx('w-3.5 h-3.5', refreshing && 'animate-spin')} />
              Refresh
            </button>
            <button
              onClick={() => setCreating(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-all duration-150"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Rule
            </button>
          </div>
        }
      />

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 px-4 py-2 mb-4">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 py-8">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading rules…</span>
        </div>
      ) : rules.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-gray-500">
          <GitBranch className="w-10 h-10 text-gray-600" />
          <p className="text-sm">No fallback rules configured.</p>
          <button
            onClick={() => setCreating(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-sardis-400 border border-sardis-500/30 hover:bg-sardis-500/10 transition-all duration-150"
          >
            <Plus className="w-3.5 h-3.5" />
            Add your first rule
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-100 text-gray-500 text-xs uppercase tracking-wider">
                <th className="text-left py-3 pr-4 font-medium">Name</th>
                <th className="text-left py-3 pr-4 font-medium">Rail Pair</th>
                <th className="text-left py-3 pr-4 font-medium">Trigger</th>
                <th className="text-left py-3 pr-4 font-medium">Behavior</th>
                <th className="text-left py-3 pr-4 font-medium">Retries</th>
                <th className="text-left py-3 pr-4 font-medium">Enabled</th>
                <th className="text-right py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-dark-200/50 transition-colors">
                  <td className="py-3 pr-4 text-white font-medium">{rule.name}</td>
                  <td className="py-3 pr-4">
                    <span className="font-mono text-xs text-sardis-400">
                      {RAIL_LABELS[rule.primary_rail as Rail] ?? rule.primary_rail}
                    </span>
                    <span className="text-gray-500 mx-1.5">→</span>
                    <span className="font-mono text-xs text-gray-300">
                      {RAIL_LABELS[rule.fallback_rail as Rail] ?? rule.fallback_rail}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge
                      color={
                        rule.trigger === 'unsafe'
                          ? 'text-red-400 border-red-500/30 bg-red-500/10'
                          : rule.trigger === 'degraded'
                            ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
                            : 'text-gray-400 border-gray-500/30 bg-gray-500/10'
                      }
                    >
                      {rule.trigger}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-gray-300">{rule.behavior}</td>
                  <td className="py-3 pr-4 text-gray-400 text-xs">
                    {rule.max_retries}× / {rule.retry_delay_seconds}s
                  </td>
                  <td className="py-3 pr-4">
                    <button
                      onClick={() => handleToggle(rule)}
                      className={clsx(
                        'w-8 h-4 relative transition-colors duration-150',
                        rule.enabled ? 'bg-sardis-500' : 'bg-dark-100'
                      )}
                    >
                      <div
                        className={clsx(
                          'absolute top-0.5 w-3 h-3 bg-white transition-transform duration-150',
                          rule.enabled ? 'translate-x-4' : 'translate-x-0.5'
                        )}
                      />
                    </button>
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditing(rule)}
                        className="p-1.5 text-gray-500 hover:text-white hover:bg-dark-100 transition-all duration-150"
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        disabled={deleting === rule.id}
                        className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all duration-150 disabled:opacity-50"
                        title="Delete"
                      >
                        {deleting === rule.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creating && (
        <RuleFormModal
          initial={EMPTY_RULE}
          onSave={handleCreate}
          onClose={() => setCreating(false)}
        />
      )}

      {editing && (
        <RuleFormModal
          initial={editing}
          onSave={handleUpdate}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}

// ── Degraded Mode Card ────────────────────────────────────────────────────────

const DEGRADED_MODES = ['normal', 'degraded', 'maintenance', 'disabled'] as const

function getRailIcon(rail: string): LucideIcon {
  switch (rail) {
    case 'stablecoin': return Activity
    case 'virtual_card': return ShieldAlert
    case 'x402': return AlertTriangle
    case 'bank_transfer': return GitBranch
    default: return Activity
  }
}

function DegradedModeCard({
  policy,
  onUpdate,
}: {
  policy: DegradedModePolicy
  onUpdate: (updated: DegradedModePolicy) => void
}) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<DegradedModePolicy>(policy)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const Icon = getRailIcon(policy.rail)

  useEffect(() => {
    setForm(policy)
  }, [policy])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await fallbackPoliciesApi.setDegradedMode(policy.rail, {
        rail: form.rail,
        mode: form.mode,
        reason: form.reason || null,
        max_amount_override: form.max_amount_override,
        require_approval: form.require_approval,
      })
      onUpdate(updated)
      setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const modeColor = MODE_COLORS[policy.mode] ?? 'text-gray-400 border-gray-500/30'
  const inputCls =
    'w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500'

  return (
    <div
      className={clsx(
        'bg-dark-200 border p-5 space-y-4 transition-colors duration-150',
        policy.mode === 'disabled'
          ? 'border-red-500/30'
          : policy.mode === 'maintenance'
            ? 'border-orange-500/30'
            : policy.mode === 'degraded'
              ? 'border-yellow-500/30'
              : 'border-dark-100'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={clsx(
              'w-8 h-8 border flex items-center justify-center',
              modeColor
            )}
          >
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">
              {RAIL_LABELS[policy.rail as Rail] ?? policy.rail}
            </p>
            <Badge color={modeColor}>{policy.mode}</Badge>
          </div>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="p-1.5 text-gray-500 hover:text-white hover:bg-dark-100 transition-all duration-150"
            title="Edit mode"
          >
            <Pencil className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Read-only summary */}
      {!editing && (
        <div className="space-y-1.5 text-xs text-gray-500">
          {policy.reason && (
            <p>
              <span className="text-gray-400">Reason:</span> {policy.reason}
            </p>
          )}
          {policy.max_amount_override != null && (
            <p>
              <span className="text-gray-400">Max amount:</span> ${policy.max_amount_override}
            </p>
          )}
          {policy.require_approval && (
            <p className="text-yellow-400">Approval required</p>
          )}
          {policy.updated_at && (
            <p className="font-mono text-gray-600">
              Updated {new Date(policy.updated_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Mode
            </label>
            <select
              value={form.mode}
              onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value }))}
              className={inputCls}
            >
              {DEGRADED_MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Reason (optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Provider outage"
              value={form.reason ?? ''}
              onChange={(e) =>
                setForm((f) => ({ ...f, reason: e.target.value || null }))
              }
              className={inputCls}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Max Amount Override ($)
            </label>
            <input
              type="number"
              min={0}
              placeholder="No override"
              value={form.max_amount_override ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  max_amount_override: e.target.value === '' ? null : Number(e.target.value),
                }))
              }
              className={inputCls}
            />
          </div>

          <button
            type="button"
            onClick={() =>
              setForm((f) => ({ ...f, require_approval: !f.require_approval }))
            }
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <div
              className={clsx(
                'w-8 h-4 relative transition-colors duration-150',
                form.require_approval ? 'bg-sardis-500' : 'bg-dark-100'
              )}
            >
              <div
                className={clsx(
                  'absolute top-0.5 w-3 h-3 bg-white transition-transform duration-150',
                  form.require_approval ? 'translate-x-4' : 'translate-x-0.5'
                )}
              />
            </div>
            <span className={form.require_approval ? 'text-white' : ''}>
              Require Approval
            </span>
          </button>

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 px-3 py-2">
              <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 disabled:opacity-50 transition-all duration-150"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5" />
              )}
              {saving ? 'Saving…' : 'Apply'}
            </button>
            <button
              onClick={() => {
                setForm(policy)
                setEditing(false)
                setError(null)
              }}
              className="px-3 py-1.5 text-xs text-gray-400 border border-dark-100 hover:text-white hover:border-gray-500 transition-all duration-150"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Degraded Modes Section ────────────────────────────────────────────────────

function DegradedModesSection() {
  const [modes, setModes] = useState<DegradedModePolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fallbackPoliciesApi
      .listDegradedModes()
      .then((data) => {
        setModes(data)
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load degraded modes')
      })
      .finally(() => setLoading(false))
  }, [])

  const handleUpdate = (updated: DegradedModePolicy) => {
    setModes((ms) => ms.map((m) => (m.rail === updated.rail ? updated : m)))
  }

  return (
    <div>
      <SectionHeader
        icon={ShieldAlert}
        title="Degraded Mode Controls"
        description="Set per-rail operating mode, amount overrides, and approval requirements during incidents."
      />

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 px-4 py-2 mb-4">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-400 py-8">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading degraded modes…</span>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {modes.map((m) => (
            <DegradedModeCard key={m.rail} policy={m} onUpdate={handleUpdate} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FallbackPoliciesPage() {
  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-sardis-500/10 border border-sardis-500/20 flex items-center justify-center">
            <GitBranch className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white font-display">Fallback Rules</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Operator-configurable cross-rail fallback rules with retry behavior, plus per-rail
              degraded mode controls with amount overrides and approval requirements.
            </p>
          </div>
        </div>
      </div>

      {/* Fallback Rules */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <FallbackRulesSection />
      </div>

      {/* Degraded Modes */}
      <div className="bg-dark-300 border border-dark-100 p-6">
        <DegradedModesSection />
      </div>
    </div>
  )
}
