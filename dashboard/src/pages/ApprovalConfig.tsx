/**
 * Approval Config — Approver groups, routing rules, quorum/SLA, and escalation.
 *
 * Three sections:
 *  1. Approver Groups  — list / add / edit / delete groups and their members
 *  2. Routing Rules    — condition-based routing with quorum, SLA, escalation
 *  3. Defaults         — fallback quorum, SLA, auto-expire, distinct-reviewer toggle
 */

import { useState, useEffect, useCallback } from 'react'
import {
  ArrowUp,

  CaretDown,
  CaretRight,
  Check,
  Clock,
  FloppyDisk,
  GearSix,
  GitBranch,
  PencilSimple,
  Plus,
  Shield,
  SpinnerGap,
  Trash,
  Users,
  Warning,
  X,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import {
  approvalConfigApi,
  type ApproverGroup,
  type RoutingRule,
  type ApprovalDefaults,
  type ApprovalConfigData,
} from '../api/client'

// ── Helpers ───────────────────────────────────────────────────────────────────

function uid() {
  return Math.random().toString(36).slice(2, 10)
}

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span className={clsx('px-2 py-0.5 text-xs border font-mono', color)}>
      {children}
    </span>
  )
}

// ── Section header ────────────────────────────────────────────────────────────

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

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({
  message,
  type,
  onDismiss,
}: {
  message: string
  type: 'success' | 'error'
  onDismiss: () => void
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div
      className={clsx(
        'fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 border text-sm font-medium shadow-lg',
        type === 'success'
          ? 'bg-sardis-500/10 border-sardis-500/40 text-sardis-300'
          : 'bg-red-500/10 border-red-500/40 text-red-300'
      )}
    >
      {type === 'success' ? <Check className="w-4 h-4" /> : <Warning className="w-4 h-4" />}
      {message}
      <button onClick={onDismiss} className="ml-2 opacity-60 hover:opacity-100">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

// ── Approver Groups section ───────────────────────────────────────────────────

interface GroupRowProps {
  group: ApproverGroup
  onEdit: (g: ApproverGroup) => void
  onDelete: (id: string) => void
}

function GroupRow({ group, onEdit, onDelete }: GroupRowProps) {
  return (
    <div className="flex items-center gap-4 p-4 bg-dark-200 border border-dark-100 hover:border-dark-50 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-white">{group.name}</span>
          <span className="text-xs text-gray-600 font-mono">#{group.id}</span>
          {group.is_fallback && (
            <Badge color="text-yellow-400 bg-yellow-500/10 border-yellow-500/30">
              fallback
            </Badge>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {group.members.map((m) => (
            <span
              key={m}
              className="px-2 py-0.5 text-xs bg-dark-300 border border-dark-100 text-gray-400 font-mono"
            >
              {m}
            </span>
          ))}
          {group.members.length === 0 && (
            <span className="text-xs text-gray-600 italic">No members</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={() => onEdit(group)}
          className="p-1.5 text-gray-500 hover:text-sardis-400 transition-colors"
          title="Edit group"
        >
          <PencilSimple className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete(group.id)}
          className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
          title="Delete group"
        >
          <Trash className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

interface GroupEditorProps {
  initial: ApproverGroup | null
  onSave: (g: ApproverGroup) => void
  onCancel: () => void
}

function GroupEditor({ initial, onSave, onCancel }: GroupEditorProps) {
  const [id, setId] = useState(initial?.id ?? uid())
  const [name, setName] = useState(initial?.name ?? '')
  const [membersRaw, setMembersRaw] = useState(initial?.members.join(', ') ?? '')
  const [isFallback, setIsFallback] = useState(initial?.is_fallback ?? false)

  const handleSave = () => {
    const members = membersRaw
      .split(',')
      .map((m) => m.trim())
      .filter(Boolean)
    onSave({ id, name, members, is_fallback: isFallback })
  }

  return (
    <div className="p-4 bg-dark-200 border border-sardis-500/30">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Group ID
          </label>
          <input
            value={id}
            onChange={(e) => setId(e.target.value)}
            disabled={!!initial}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 font-mono focus:outline-none focus:border-sardis-500/50 disabled:opacity-50"
            placeholder="finance"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Display Name
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
            placeholder="Finance Team"
          />
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
          Members (comma-separated emails)
        </label>
        <input
          value={membersRaw}
          onChange={(e) => setMembersRaw(e.target.value)}
          className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          placeholder="alice@company.com, bob@company.com"
        />
      </div>
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={isFallback}
            onChange={(e) => setIsFallback(e.target.checked)}
            className="accent-sardis-500"
          />
          <span className="text-sm text-gray-400">Fallback group</span>
        </label>
        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-dark-100 hover:border-dark-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!id.trim() || !name.trim()}
            className="px-3 py-1.5 text-sm bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            FloppyDisk Group
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Routing Rules section ─────────────────────────────────────────────────────

interface RuleRowProps {
  rule: RoutingRule
  groupName: (id: string) => string
  onEdit: (r: RoutingRule) => void
  onDelete: (id: string) => void
}

function RuleRow({ rule, groupName, onEdit, onDelete }: RuleRowProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-dark-200 border border-dark-100 hover:border-dark-50 transition-colors">
      <div className="flex items-center gap-4 p-4">
        <button
          onClick={() => setExpanded((p) => !p)}
          className="text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
        >
          {expanded ? <CaretDown className="w-4 h-4" /> : <CaretRight className="w-4 h-4" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm font-medium text-white">{rule.name}</span>
            <span className="text-xs text-gray-600 font-mono">#{rule.id}</span>
            <Badge color="text-blue-400 bg-blue-500/10 border-blue-500/30">
              {groupName(rule.approver_group)}
            </Badge>
            <Badge color="text-sardis-400 bg-sardis-500/10 border-sardis-500/30">
              quorum {rule.quorum}
            </Badge>
            <Badge color="text-purple-400 bg-purple-500/10 border-purple-500/30">
              SLA {rule.sla_hours}h
            </Badge>
            {rule.escalation_hours && (
              <Badge color="text-yellow-400 bg-yellow-500/10 border-yellow-500/30">
                esc {rule.escalation_hours}h
              </Badge>
            )}
          </div>
          <p className="text-xs text-gray-500 font-mono mt-1">{rule.condition}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => onEdit(rule)}
            className="p-1.5 text-gray-500 hover:text-sardis-400 transition-colors"
            title="Edit rule"
          >
            <PencilSimple className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(rule.id)}
            className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
            title="Delete rule"
          >
            <Trash className="w-4 h-4" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-dark-100 px-4 py-3 grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wide">Condition</span>
            <p className="text-gray-300 font-mono text-xs mt-1">{rule.condition}</p>
          </div>
          <div>
            <span className="text-gray-500 text-xs uppercase tracking-wide">Distinct reviewers</span>
            <p className="text-gray-300 mt-1">{rule.distinct_reviewers ? 'Required' : 'Not required'}</p>
          </div>
          {rule.escalation_group && (
            <div>
              <span className="text-gray-500 text-xs uppercase tracking-wide">Escalation group</span>
              <p className="text-gray-300 mt-1">{groupName(rule.escalation_group)}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface RuleEditorProps {
  initial: RoutingRule | null
  groups: ApproverGroup[]
  onSave: (r: RoutingRule) => void
  onCancel: () => void
}

function RuleEditor({ initial, groups, onSave, onCancel }: RuleEditorProps) {
  const [id, setId] = useState(initial?.id ?? uid())
  const [name, setName] = useState(initial?.name ?? '')
  const [condition, setCondition] = useState(initial?.condition ?? '')
  const [approverGroup, setApproverGroup] = useState(initial?.approver_group ?? groups[0]?.id ?? '')
  const [quorum, setQuorum] = useState(String(initial?.quorum ?? 1))
  const [distinctReviewers, setDistinctReviewers] = useState(initial?.distinct_reviewers ?? false)
  const [slaHours, setSlaHours] = useState(String(initial?.sla_hours ?? 24))
  const [escalationHours, setEscalationHours] = useState(
    initial?.escalation_hours != null ? String(initial.escalation_hours) : ''
  )
  const [escalationGroup, setEscalationGroup] = useState(initial?.escalation_group ?? '')

  const handleSave = () => {
    onSave({
      id,
      name,
      condition,
      approver_group: approverGroup,
      quorum: Math.max(1, parseInt(quorum, 10) || 1),
      distinct_reviewers: distinctReviewers,
      sla_hours: Math.max(1, parseInt(slaHours, 10) || 24),
      escalation_hours: escalationHours ? parseInt(escalationHours, 10) : null,
      escalation_group: escalationGroup || null,
    })
  }

  const isValid = id.trim() && name.trim() && condition.trim() && approverGroup

  return (
    <div className="p-4 bg-dark-200 border border-sardis-500/30 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Rule ID</label>
          <input
            value={id}
            onChange={(e) => setId(e.target.value)}
            disabled={!!initial}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 font-mono focus:outline-none focus:border-sardis-500/50 disabled:opacity-50"
            placeholder="high-value"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
            placeholder="High Value Payments"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Condition</label>
        <input
          value={condition}
          onChange={(e) => setCondition(e.target.value)}
          className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 font-mono focus:outline-none focus:border-sardis-500/50"
          placeholder="amount > 1000"
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Approver Group</label>
          <select
            value={approverGroup}
            onChange={(e) => setApproverGroup(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          >
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Quorum</label>
          <input
            type="number"
            min={1}
            value={quorum}
            onChange={(e) => setQuorum(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">SLA (hours)</label>
          <input
            type="number"
            min={1}
            value={slaHours}
            onChange={(e) => setSlaHours(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Escalation after (hours, optional)
          </label>
          <input
            type="number"
            min={1}
            value={escalationHours}
            onChange={(e) => setEscalationHours(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
            placeholder="Leave empty to disable"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Escalation Group (optional)
          </label>
          <select
            value={escalationGroup}
            onChange={(e) => setEscalationGroup(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          >
            <option value="">None</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={distinctReviewers}
            onChange={(e) => setDistinctReviewers(e.target.checked)}
            className="accent-sardis-500"
          />
          <span className="text-sm text-gray-400">Require distinct reviewers</span>
        </label>
        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white border border-dark-100 hover:border-dark-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!isValid}
            className="px-3 py-1.5 text-sm bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            FloppyDisk Rule
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Defaults section ──────────────────────────────────────────────────────────

interface DefaultsFormProps {
  defaults: ApprovalDefaults
  groups: ApproverGroup[]
  saving: boolean
  onSave: (d: ApprovalDefaults) => void
}

function DefaultsForm({ defaults, groups, saving, onSave }: DefaultsFormProps) {
  const [defaultGroup, setDefaultGroup] = useState(defaults.default_approver_group)
  const [defaultQuorum, setDefaultQuorum] = useState(String(defaults.default_quorum))
  const [defaultSla, setDefaultSla] = useState(String(defaults.default_sla_hours))
  const [autoExpire, setAutoExpire] = useState(String(defaults.auto_expire_hours))
  const [distinctReviewers, setDistinctReviewers] = useState(defaults.require_distinct_reviewers)

  const isDirty =
    defaultGroup !== defaults.default_approver_group ||
    defaultQuorum !== String(defaults.default_quorum) ||
    defaultSla !== String(defaults.default_sla_hours) ||
    autoExpire !== String(defaults.auto_expire_hours) ||
    distinctReviewers !== defaults.require_distinct_reviewers

  const handleSave = () => {
    onSave({
      default_approver_group: defaultGroup,
      default_quorum: Math.max(1, parseInt(defaultQuorum, 10) || 1),
      default_sla_hours: Math.max(1, parseInt(defaultSla, 10) || 24),
      auto_expire_hours: Math.max(1, parseInt(autoExpire, 10) || 168),
      require_distinct_reviewers: distinctReviewers,
    })
  }

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Default Approver Group
          </label>
          <select
            value={defaultGroup}
            onChange={(e) => setDefaultGroup(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          >
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Default Quorum
          </label>
          <input
            type="number"
            min={1}
            value={defaultQuorum}
            onChange={(e) => setDefaultQuorum(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Default SLA (hours)
          </label>
          <input
            type="number"
            min={1}
            value={defaultSla}
            onChange={(e) => setDefaultSla(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5 uppercase tracking-wide">
            Auto-expire (hours)
          </label>
          <input
            type="number"
            min={1}
            value={autoExpire}
            onChange={(e) => setAutoExpire(e.target.value)}
            className="w-full bg-dark-300 border border-dark-100 text-white text-sm px-3 py-2 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={distinctReviewers}
            onChange={(e) => setDistinctReviewers(e.target.checked)}
            className="accent-sardis-500"
          />
          <span className="text-sm text-gray-400">Require distinct reviewers by default</span>
        </label>
        <button
          onClick={handleSave}
          disabled={!isDirty || saving}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-sardis-500 text-dark-400 font-medium hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? <SpinnerGap className="w-4 h-4 animate-spin" /> : <FloppyDisk className="w-4 h-4" />}
          FloppyDisk Defaults
        </button>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ApprovalConfigPage() {
  const [config, setConfig] = useState<ApprovalConfigData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // editing state
  const [editingGroup, setEditingGroup] = useState<ApproverGroup | null | 'new'>(null)
  const [editingRule, setEditingRule] = useState<RoutingRule | null | 'new'>(null)

  // save states
  const [savingGroups, setSavingGroups] = useState(false)
  const [savingRules, setSavingRules] = useState(false)
  const [savingDefaults, setSavingDefaults] = useState(false)

  // toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }, [])

  // load
  useEffect(() => {
    approvalConfigApi
      .get()
      .then(setConfig)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const groupName = useCallback(
    (id: string) => config?.approver_groups.find((g) => g.id === id)?.name ?? id,
    [config]
  )

  // ── Groups ──────────────────────────────────────────────────────────────────

  const handleSaveGroup = async (group: ApproverGroup) => {
    if (!config) return
    const existing = config.approver_groups.find((g) => g.id === group.id)
    const updated = existing
      ? config.approver_groups.map((g) => (g.id === group.id ? group : g))
      : [...config.approver_groups, group]

    setSavingGroups(true)
    try {
      const result = await approvalConfigApi.updateGroups(updated)
      setConfig((prev) => prev ? { ...prev, approver_groups: result } : prev)
      setEditingGroup(null)
      showToast('Approver groups saved', 'success')
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Failed to save groups', 'error')
    } finally {
      setSavingGroups(false)
    }
  }

  const handleDeleteGroup = async (id: string) => {
    if (!config) return
    const updated = config.approver_groups.filter((g) => g.id !== id)
    setSavingGroups(true)
    try {
      const result = await approvalConfigApi.updateGroups(updated)
      setConfig((prev) => prev ? { ...prev, approver_groups: result } : prev)
      showToast('Group deleted', 'success')
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Failed to delete group', 'error')
    } finally {
      setSavingGroups(false)
    }
  }

  // ── Rules ───────────────────────────────────────────────────────────────────

  const handleSaveRule = async (rule: RoutingRule) => {
    if (!config) return
    const existing = config.routing_rules.find((r) => r.id === rule.id)
    const updated = existing
      ? config.routing_rules.map((r) => (r.id === rule.id ? rule : r))
      : [...config.routing_rules, rule]

    setSavingRules(true)
    try {
      const result = await approvalConfigApi.updateRules(updated)
      setConfig((prev) => prev ? { ...prev, routing_rules: result } : prev)
      setEditingRule(null)
      showToast('Routing rules saved', 'success')
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Failed to save rules', 'error')
    } finally {
      setSavingRules(false)
    }
  }

  const handleDeleteRule = async (id: string) => {
    if (!config) return
    const updated = config.routing_rules.filter((r) => r.id !== id)
    setSavingRules(true)
    try {
      const result = await approvalConfigApi.updateRules(updated)
      setConfig((prev) => prev ? { ...prev, routing_rules: result } : prev)
      showToast('Rule deleted', 'success')
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Failed to delete rule', 'error')
    } finally {
      setSavingRules(false)
    }
  }

  // ── Defaults ─────────────────────────────────────────────────────────────────

  const handleSaveDefaults = async (defaults: ApprovalDefaults) => {
    setSavingDefaults(true)
    try {
      const result = await approvalConfigApi.updateDefaults(defaults)
      setConfig((prev) => prev ? { ...prev, defaults: result } : prev)
      showToast('Defaults saved', 'success')
    } catch (e: unknown) {
      showToast((e as Error).message ?? 'Failed to save defaults', 'error')
    } finally {
      setSavingDefaults(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <SpinnerGap className="w-8 h-8 text-sardis-400 animate-spin" />
      </div>
    )
  }

  if (error || !config) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <Warning className="w-10 h-10 text-red-400" />
        <p className="text-sm text-gray-400">{error ?? 'Failed to load approval config'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-10 max-w-4xl">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white font-display">Approval Config</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure approver groups, routing rules, quorum, SLA targets, and escalation paths.
          Changes take effect immediately — no code deployment required.
        </p>
      </div>

      {/* ── Section 1: Approver Groups ──────────────────────────────────────── */}
      <section>
        <SectionHeader
          icon={Users}
          title="Approver Groups"
          description="Named groups of people who can approve payment requests."
          action={
            <button
              onClick={() => setEditingGroup('new')}
              disabled={savingGroups || editingGroup !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-sardis-500/40 text-sardis-400 hover:bg-sardis-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
              Add Group
            </button>
          }
        />

        <div className="space-y-2">
          {editingGroup === 'new' && (
            <GroupEditor
              initial={null}
              onSave={handleSaveGroup}
              onCancel={() => setEditingGroup(null)}
            />
          )}

          {config.approver_groups.map((group) =>
            editingGroup !== null && editingGroup !== 'new' && editingGroup.id === group.id ? (
              <GroupEditor
                key={group.id}
                initial={group}
                onSave={handleSaveGroup}
                onCancel={() => setEditingGroup(null)}
              />
            ) : (
              <GroupRow
                key={group.id}
                group={group}
                onEdit={(g) => setEditingGroup(g)}
                onDelete={handleDeleteGroup}
              />
            )
          )}

          {config.approver_groups.length === 0 && editingGroup === null && (
            <div className="p-6 text-center text-gray-600 border border-dashed border-dark-100">
              No approver groups. Add one to get started.
            </div>
          )}
        </div>

        {savingGroups && (
          <div className="flex items-center gap-2 mt-3 text-sm text-gray-500">
            <SpinnerGap className="w-3.5 h-3.5 animate-spin" />
            Saving groups…
          </div>
        )}
      </section>

      {/* ── Section 2: Routing Rules ────────────────────────────────────────── */}
      <section>
        <SectionHeader
          icon={GitBranch}
          title="Routing Rules"
          description="Condition-based rules that route approval requests to specific groups with custom quorum and SLA."
          action={
            <button
              onClick={() => setEditingRule('new')}
              disabled={savingRules || editingRule !== null || config.approver_groups.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-sardis-500/40 text-sardis-400 hover:bg-sardis-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title={
                config.approver_groups.length === 0
                  ? 'Add at least one approver group first'
                  : undefined
              }
            >
              <Plus className="w-4 h-4" />
              Add Rule
            </button>
          }
        />

        <div className="space-y-2">
          {editingRule === 'new' && (
            <RuleEditor
              initial={null}
              groups={config.approver_groups}
              onSave={handleSaveRule}
              onCancel={() => setEditingRule(null)}
            />
          )}

          {config.routing_rules.map((rule) =>
            editingRule !== null && editingRule !== 'new' && editingRule.id === rule.id ? (
              <RuleEditor
                key={rule.id}
                initial={rule}
                groups={config.approver_groups}
                onSave={handleSaveRule}
                onCancel={() => setEditingRule(null)}
              />
            ) : (
              <RuleRow
                key={rule.id}
                rule={rule}
                groupName={groupName}
                onEdit={(r) => setEditingRule(r)}
                onDelete={handleDeleteRule}
              />
            )
          )}

          {config.routing_rules.length === 0 && editingRule === null && (
            <div className="p-6 text-center text-gray-600 border border-dashed border-dark-100">
              No routing rules. Add one to override default routing.
            </div>
          )}
        </div>

        {/* Legend */}
        {config.routing_rules.length > 0 && (
          <div className="flex items-center gap-4 mt-4 text-xs text-gray-600">
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              SLA = target response window
            </div>
            <div className="flex items-center gap-1.5">
              <ArrowUp className="w-3.5 h-3.5" />
              Escalation = auto-escalate if no response
            </div>
            <div className="flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5" />
              Quorum = minimum approvals needed
            </div>
          </div>
        )}

        {savingRules && (
          <div className="flex items-center gap-2 mt-3 text-sm text-gray-500">
            <SpinnerGap className="w-3.5 h-3.5 animate-spin" />
            Saving rules…
          </div>
        )}
      </section>

      {/* ── Section 3: Defaults ─────────────────────────────────────────────── */}
      <section>
        <SectionHeader
          icon={GearSix}
          title="Defaults"
          description="Fallback settings applied when no routing rule matches the approval request."
        />
        <div className="p-5 bg-dark-200 border border-dark-100">
          <DefaultsForm
            defaults={config.defaults}
            groups={config.approver_groups}
            saving={savingDefaults}
            onSave={handleSaveDefaults}
          />
        </div>
      </section>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  )
}
