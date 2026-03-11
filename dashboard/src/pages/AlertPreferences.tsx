/**
 * Alert Preferences Page
 *
 * Tabs:
 *  - Channels : configure Slack, Discord, Email, PagerDuty, WebSocket channels
 *  - Rules    : create, edit, enable/disable, delete alert rules
 */

import { useState, useEffect } from 'react'
import {
  Bell,
  Slack,
  Mail,
  Globe,
  AlertTriangle,
  Plus,
  Trash2,
  Edit2,
  Play,
  CheckCircle,
  XCircle,
  X,
  Save,
  Loader2,
  MessageSquare,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'

const API_BASE = import.meta.env.VITE_API_URL || ''

// ─── Types ───────────────────────────────────────────────────────────────────

type ChannelType = 'slack' | 'discord' | 'email' | 'pagerduty' | 'websocket'
type Severity = 'info' | 'warning' | 'critical'
type ConditionType =
  | 'amount_exceeds'
  | 'budget_percentage'
  | 'transaction_count'
  | 'status_change'
  | 'policy_blocked'
  | 'level_change'

interface AlertChannel {
  channel_type: ChannelType
  enabled: boolean
  config: Record<string, string>
  status?: string
}

interface AlertRule {
  rule_id: string
  name: string
  condition_type: ConditionType
  threshold: number
  severity: Severity
  channels: ChannelType[]
  enabled: boolean
}

type TabId = 'channels' | 'rules'

// ─── Constants ────────────────────────────────────────────────────────────────

const CHANNEL_LABELS: Record<ChannelType, string> = {
  slack: 'Slack',
  discord: 'Discord',
  email: 'Email',
  pagerduty: 'PagerDuty',
  websocket: 'WebSocket',
}

const CONDITION_LABELS: Record<ConditionType, string> = {
  amount_exceeds: 'Amount Exceeds',
  budget_percentage: 'Budget Percentage',
  transaction_count: 'Transaction Count',
  status_change: 'Status Change',
  policy_blocked: 'Policy Blocked',
  level_change: 'Level Change',
}

const SEVERITY_COLORS: Record<Severity, string> = {
  info: 'bg-blue-500/10 text-blue-400',
  warning: 'bg-yellow-500/10 text-yellow-400',
  critical: 'bg-red-500/10 text-red-400',
}

const ALL_CHANNEL_TYPES: ChannelType[] = [
  'slack',
  'discord',
  'email',
  'pagerduty',
  'websocket',
]

const CONDITION_TYPES: ConditionType[] = [
  'amount_exceeds',
  'budget_percentage',
  'transaction_count',
  'status_change',
  'policy_blocked',
  'level_change',
]

const SEVERITIES: Severity[] = ['info', 'warning', 'critical']

// ─── Small helpers ────────────────────────────────────────────────────────────

function ChannelIcon({ type, className }: { type: ChannelType; className?: string }) {
  const cls = clsx('w-5 h-5', className)
  switch (type) {
    case 'slack':
      return <Slack className={cls} />
    case 'discord':
      return <MessageSquare className={cls} />
    case 'email':
      return <Mail className={cls} />
    case 'pagerduty':
      return <AlertTriangle className={cls} />
    case 'websocket':
      return <Globe className={cls} />
  }
}

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        'relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none disabled:opacity-50',
        checked ? 'bg-sardis-500' : 'bg-dark-100'
      )}
    >
      <span
        className={clsx(
          'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200',
          checked ? 'translate-x-4' : 'translate-x-0'
        )}
      />
    </button>
  )
}

function ConfirmDialog({
  title,
  message,
  confirmLabel,
  confirmClass,
  onConfirm,
  onCancel,
}: {
  title: string
  message: string
  confirmLabel: string
  confirmClass: string
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card max-w-sm w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
        <p className="text-sm text-gray-400 mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors text-sm"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={clsx('flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors', confirmClass)}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Channel Config Form ──────────────────────────────────────────────────────

function ChannelConfigForm({
  type,
  config,
  onChange,
}: {
  type: ChannelType
  config: Record<string, string>
  onChange: (key: string, value: string) => void
}) {
  const inputCls =
    'w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:outline-none focus:border-sardis-500/50 placeholder:text-gray-600'

  switch (type) {
    case 'slack':
      return (
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Webhook URL</label>
          <input
            type="url"
            value={config.webhook_url ?? ''}
            onChange={(e) => onChange('webhook_url', e.target.value)}
            className={inputCls}
            placeholder="https://hooks.slack.com/services/..."
          />
        </div>
      )
    case 'discord':
      return (
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Webhook URL</label>
          <input
            type="url"
            value={config.webhook_url ?? ''}
            onChange={(e) => onChange('webhook_url', e.target.value)}
            className={inputCls}
            placeholder="https://discord.com/api/webhooks/..."
          />
        </div>
      )
    case 'email':
      return (
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">
              Recipients <span className="text-gray-600">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={config.recipients ?? ''}
              onChange={(e) => onChange('recipients', e.target.value)}
              className={inputCls}
              placeholder="alerts@yourcompany.com, ops@yourcompany.com"
            />
          </div>
          <p className="text-xs text-gray-600">
            SMTP settings are configured at the organization level in Settings.
          </p>
        </div>
      )
    case 'pagerduty':
      return (
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Routing Key</label>
          <input
            type="text"
            value={config.routing_key ?? ''}
            onChange={(e) => onChange('routing_key', e.target.value)}
            className={inputCls}
            placeholder="your-pagerduty-routing-key"
          />
        </div>
      )
    case 'websocket':
      return (
        <p className="text-xs text-gray-500">
          WebSocket channel is automatically enabled and requires no additional configuration.
        </p>
      )
  }
}

// ─── Channel Card ─────────────────────────────────────────────────────────────

type TestStatus = 'idle' | 'loading' | 'success' | 'error'

function ChannelCard({
  channelType,
  existing,
  token,
  onSaved,
}: {
  channelType: ChannelType
  existing?: AlertChannel
  token: string
  onSaved: () => void
}) {
  const [open, setOpen] = useState(false)
  const [enabled, setEnabled] = useState(existing?.enabled ?? false)
  const [config, setConfig] = useState<Record<string, string>>(
    existing?.config ?? {}
  )
  const [saving, setSaving] = useState(false)
  const [testStatus, setTestStatus] = useState<TestStatus>('idle')
  const [testMessage, setTestMessage] = useState<string>('')

  const handleConfigChange = (key: string, value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch(`${API_BASE}/api/v2/alerts/channels`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ channel_type: channelType, config: { ...config, enabled } }),
      })
      onSaved()
      setOpen(false)
    } catch {
      // keep form open on error
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTestStatus('loading')
    setTestMessage('')
    try {
      const res = await fetch(`${API_BASE}/api/v2/alerts/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ channel_type: channelType }),
      })
      if (res.ok) {
        setTestStatus('success')
        setTestMessage('Test alert sent successfully.')
      } else {
        const data = await res.json().catch(() => ({}))
        setTestStatus('error')
        setTestMessage(data?.detail ?? 'Test failed.')
      }
    } catch {
      setTestStatus('error')
      setTestMessage('Network error.')
    }
  }

  const isWebSocket = channelType === 'websocket'
  const isConfigured = existing != null
  const iconColor = isConfigured && enabled ? 'text-sardis-400' : 'text-gray-500'
  const iconBg = isConfigured && enabled ? 'bg-sardis-500/10' : 'bg-dark-200'

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between gap-4">
        {/* Left: icon + label */}
        <div className="flex items-center gap-3">
          <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center', iconBg)}>
            <ChannelIcon type={channelType} className={iconColor} />
          </div>
          <div>
            <p className="text-sm font-medium text-white">{CHANNEL_LABELS[channelType]}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {isWebSocket
                ? 'Auto-configured'
                : isConfigured
                ? enabled
                  ? 'Active'
                  : 'Configured but disabled'
                : 'Not configured'}
            </p>
          </div>
        </div>

        {/* Right: toggle + actions */}
        <div className="flex items-center gap-3">
          {!isWebSocket && (
            <Toggle checked={enabled} onChange={setEnabled} />
          )}
          {isWebSocket && (
            <span className="text-xs text-gray-500 px-2 py-0.5 bg-dark-200 rounded">
              Always on
            </span>
          )}

          <button
            onClick={handleTest}
            disabled={testStatus === 'loading'}
            title="Send test alert"
            className="p-1.5 text-gray-400 hover:text-sardis-400 transition-colors disabled:opacity-50"
          >
            {testStatus === 'loading' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>

          {!isWebSocket && (
            <button
              onClick={() => setOpen((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-300 bg-dark-200 border border-dark-100 rounded-lg hover:bg-dark-100 hover:text-white transition-colors"
            >
              Configure
            </button>
          )}
        </div>
      </div>

      {/* Test result banner */}
      {(testStatus === 'success' || testStatus === 'error') && (
        <div
          className={clsx(
            'mt-3 px-3 py-2 rounded-lg text-xs flex items-center gap-2',
            testStatus === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
          )}
        >
          {testStatus === 'success' ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{testMessage}</span>
          <button
            onClick={() => setTestStatus('idle')}
            className="ml-auto opacity-60 hover:opacity-100"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Inline config form */}
      {open && (
        <div className="mt-4 pt-4 border-t border-dark-100 space-y-4">
          <ChannelConfigForm
            type={channelType}
            config={config}
            onChange={handleConfigChange}
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setOpen(false)}
              className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-sardis-500 text-dark-400 text-xs font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5" />
              )}
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Channels Tab ─────────────────────────────────────────────────────────────

function ChannelsTab({ token }: { token: string }) {
  const [channels, setChannels] = useState<AlertChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v2/alerts/channels`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('Failed to load channels')
        return res.json()
      })
      .then((data) => {
        if (!cancelled) {
          setChannels(Array.isArray(data) ? data : data.channels ?? [])
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Unknown error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [token, refreshKey])

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="card p-5 animate-pulse">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-dark-200 rounded-lg" />
              <div className="space-y-1.5">
                <div className="h-4 bg-dark-200 rounded w-24" />
                <div className="h-3 bg-dark-200 rounded w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <XCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">{error}</p>
        <button
          onClick={() => setRefreshKey((k) => k + 1)}
          className="mt-4 px-4 py-2 text-xs text-sardis-400 border border-sardis-500/30 rounded-lg hover:bg-sardis-500/10 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {ALL_CHANNEL_TYPES.map((type) => {
        const existing = channels.find((c) => c.channel_type === type)
        return (
          <ChannelCard
            key={type}
            channelType={type}
            existing={existing}
            token={token}
            onSaved={() => setRefreshKey((k) => k + 1)}
          />
        )
      })}
    </div>
  )
}

// ─── Rule Form Modal ──────────────────────────────────────────────────────────

interface RuleFormData {
  name: string
  condition_type: ConditionType
  threshold: number
  severity: Severity
  channels: ChannelType[]
  enabled: boolean
}

function RuleModal({
  mode,
  initial,
  isLoading,
  onClose,
  onSubmit,
}: {
  mode: 'create' | 'edit'
  initial?: Partial<RuleFormData>
  isLoading: boolean
  onClose: () => void
  onSubmit: (data: RuleFormData) => Promise<void>
}) {
  const [name, setName] = useState(initial?.name ?? '')
  const [conditionType, setConditionType] = useState<ConditionType>(
    initial?.condition_type ?? 'amount_exceeds'
  )
  const [threshold, setThreshold] = useState<string>(
    initial?.threshold != null ? String(initial.threshold) : ''
  )
  const [severity, setSeverity] = useState<Severity>(initial?.severity ?? 'warning')
  const [channels, setChannels] = useState<ChannelType[]>(initial?.channels ?? [])
  const [enabled, setEnabled] = useState(initial?.enabled ?? true)

  const toggleChannel = (ch: ChannelType) => {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit({
      name,
      condition_type: conditionType,
      threshold: Number(threshold),
      severity,
      channels,
      enabled,
    })
  }

  const inputCls =
    'w-full px-3 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:outline-none focus:border-sardis-500/50'

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="card max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">
            {mode === 'create' ? 'Create Alert Rule' : 'Edit Alert Rule'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
              placeholder="e.g. High spend alert"
            />
          </div>

          {/* Condition type */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">
              Condition Type <span className="text-red-500">*</span>
            </label>
            <select
              value={conditionType}
              onChange={(e) => setConditionType(e.target.value as ConditionType)}
              className={inputCls}
            >
              {CONDITION_TYPES.map((ct) => (
                <option key={ct} value={ct}>
                  {CONDITION_LABELS[ct]}
                </option>
              ))}
            </select>
          </div>

          {/* Threshold */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">
              Threshold <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              required
              min={0}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className={inputCls}
              placeholder="e.g. 500"
            />
          </div>

          {/* Severity */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Severity <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-2">
              {SEVERITIES.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverity(s)}
                  className={clsx(
                    'flex-1 px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all border',
                    severity === s
                      ? clsx(SEVERITY_COLORS[s], 'border-current/30')
                      : 'text-gray-400 bg-dark-300 border-dark-100 hover:border-gray-600'
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Channels */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Channels
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ALL_CHANNEL_TYPES.map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => toggleChannel(ch)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all border text-left',
                    channels.includes(ch)
                      ? 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
                      : 'text-gray-400 bg-dark-300 border-dark-100 hover:border-gray-600'
                  )}
                >
                  <ChannelIcon type={ch} className="w-3.5 h-3.5" />
                  {CHANNEL_LABELS[ch]}
                </button>
              ))}
            </div>
          </div>

          {/* Enabled */}
          <div className="flex items-center justify-between py-2 border-t border-dark-100">
            <label className="text-sm font-medium text-gray-400">Enabled</label>
            <Toggle checked={enabled} onChange={setEnabled} />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-dark-100 text-gray-400 rounded-lg hover:bg-dark-200 transition-colors text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50 text-sm"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {mode === 'create' ? 'Creating…' : 'Saving…'}
                </span>
              ) : mode === 'create' ? (
                'Create Rule'
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Rule Card ────────────────────────────────────────────────────────────────

function RuleCard({
  rule,
  token,
  onEdit,
  onDeleted,
  onToggled,
}: {
  rule: AlertRule
  token: string
  onEdit: (rule: AlertRule) => void
  onDeleted: (id: string) => void
  onToggled: (id: string, enabled: boolean) => void
}) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [toggling, setToggling] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleToggle = async (value: boolean) => {
    setToggling(true)
    try {
      await fetch(`${API_BASE}/api/v2/alerts/rules/${rule.rule_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled: value }),
      })
      onToggled(rule.rule_id, value)
    } finally {
      setToggling(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await fetch(`${API_BASE}/api/v2/alerts/rules/${rule.rule_id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      onDeleted(rule.rule_id)
    } finally {
      setDeleting(false)
      setShowConfirm(false)
    }
  }

  return (
    <>
      <div className="card p-5">
        <div className="flex items-start justify-between gap-4">
          {/* Left */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium text-white">{rule.name}</p>
              <span
                className={clsx(
                  'px-2 py-0.5 rounded text-xs font-medium capitalize',
                  SEVERITY_COLORS[rule.severity]
                )}
              >
                {rule.severity}
              </span>
              <span
                className={clsx(
                  'px-2 py-0.5 rounded text-xs',
                  rule.enabled
                    ? 'bg-green-500/10 text-green-400'
                    : 'bg-gray-500/10 text-gray-400'
                )}
              >
                {rule.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>

            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
              <span>
                Condition:{' '}
                <span className="text-gray-300">{CONDITION_LABELS[rule.condition_type]}</span>
              </span>
              <span>
                Threshold: <span className="text-gray-300">{rule.threshold}</span>
              </span>
            </div>

            {rule.channels.length > 0 && (
              <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                {rule.channels.map((ch) => (
                  <span
                    key={ch}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-dark-200 rounded text-xs text-gray-400"
                  >
                    <ChannelIcon type={ch} className="w-3 h-3" />
                    {CHANNEL_LABELS[ch]}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Right: toggle + edit + delete */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <Toggle
              checked={rule.enabled}
              onChange={handleToggle}
              disabled={toggling}
            />
            <button
              onClick={() => onEdit(rule)}
              title="Edit rule"
              className="p-1.5 text-gray-400 hover:text-blue-400 transition-colors"
            >
              <Edit2 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowConfirm(true)}
              disabled={deleting}
              title="Delete rule"
              className="p-1.5 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {showConfirm && (
        <ConfirmDialog
          title="Delete alert rule?"
          message={`This will permanently delete the rule "${rule.name}".`}
          confirmLabel="Delete"
          confirmClass="bg-red-600 hover:bg-red-500 text-white"
          onConfirm={handleDelete}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </>
  )
}

// ─── Rules Tab ────────────────────────────────────────────────────────────────

function RulesTab({
  token,
  showCreate,
  onCloseCreate,
}: {
  token: string
  showCreate: boolean
  onCloseCreate: () => void
}) {
  const [rules, setRules] = useState<AlertRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateInternal, setShowCreateInternal] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Either the header button or the empty-state button triggers create
  const isCreateOpen = showCreate || showCreateInternal

  const handleCloseCreate = () => {
    onCloseCreate()
    setShowCreateInternal(false)
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetch(`${API_BASE}/api/v2/alerts/rules`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('Failed to load rules')
        return res.json()
      })
      .then((data) => {
        if (!cancelled) {
          setRules(Array.isArray(data) ? data : data.rules ?? [])
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Unknown error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [token])

  const handleCreate = async (data: RuleFormData) => {
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/alerts/rules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Create failed')
      const created: AlertRule = await res.json()
      setRules((prev) => [...prev, created])
      handleCloseCreate()
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = async (data: RuleFormData) => {
    if (!editingRule) return
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/alerts/rules/${editingRule.rule_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Update failed')
      const updated: AlertRule = await res.json()
      setRules((prev) => prev.map((r) => (r.rule_id === updated.rule_id ? updated : r)))
      setEditingRule(null)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleted = (id: string) => {
    setRules((prev) => prev.filter((r) => r.rule_id !== id))
  }

  const handleToggled = (id: string, value: boolean) => {
    setRules((prev) =>
      prev.map((r) => (r.rule_id === id ? { ...r, enabled: value } : r))
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="card p-5 animate-pulse">
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-dark-200 rounded w-1/3" />
              <div className="h-3 bg-dark-200 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <XCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <p className="text-gray-400 text-sm">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 text-xs text-sardis-400 border border-sardis-500/30 rounded-lg hover:bg-sardis-500/10 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        {rules.length === 0 ? (
          <div className="card p-14 text-center">
            <Bell className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No alert rules</h3>
            <p className="text-gray-500 mb-6 text-sm">
              Create rules to get notified when spending patterns or agent behaviors exceed thresholds.
            </p>
            <button
              onClick={() => setShowCreateInternal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Create your first rule
            </button>
          </div>
        ) : (
          rules.map((rule) => (
            <RuleCard
              key={rule.rule_id}
              rule={rule}
              token={token}
              onEdit={setEditingRule}
              onDeleted={handleDeleted}
              onToggled={handleToggled}
            />
          ))
        )}
      </div>

      {isCreateOpen && (
        <RuleModal
          mode="create"
          isLoading={submitting}
          onClose={handleCloseCreate}
          onSubmit={handleCreate}
        />
      )}

      {editingRule && (
        <RuleModal
          mode="edit"
          initial={{
            name: editingRule.name,
            condition_type: editingRule.condition_type,
            threshold: editingRule.threshold,
            severity: editingRule.severity,
            channels: editingRule.channels,
            enabled: editingRule.enabled,
          }}
          isLoading={submitting}
          onClose={() => setEditingRule(null)}
          onSubmit={handleEdit}
        />
      )}
    </>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AlertPreferencesPage() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabId>('channels')
  const [showCreateRule, setShowCreateRule] = useState(false)

  const authToken = token ?? ''

  const tabs: { id: TabId; label: string }[] = [
    { id: 'channels', label: 'Channels' },
    { id: 'rules', label: 'Rules' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Alert Preferences</h1>
          <p className="text-gray-400 mt-1">
            Configure notification channels and define alert rules for your agents
          </p>
        </div>
        {activeTab === 'rules' && (
          <button
            onClick={() => setShowCreateRule(true)}
            className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
          >
            <Plus className="w-5 h-5" />
            Create Rule
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-dark-100">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              setActiveTab(tab.id)
              setShowCreateRule(false)
            }}
            className={clsx(
              'px-5 py-2.5 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-sardis-500 text-sardis-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'channels' && <ChannelsTab token={authToken} />}
      {activeTab === 'rules' && (
        <RulesTab
          token={authToken}
          showCreate={showCreateRule}
          onCloseCreate={() => setShowCreateRule(false)}
        />
      )}
    </div>
  )
}
