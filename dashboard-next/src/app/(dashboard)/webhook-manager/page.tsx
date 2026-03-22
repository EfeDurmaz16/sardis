"use client";
import { useState } from 'react'
import {
  Plus,
  Webhook,
  Trash2,
  Play,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Edit2,
  CheckCircle,
  XCircle,
  Clock,
  Copy,
  Check,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { webhooksApiV2 } from '@/api/client'

// ─── Types ─────────────────────────────────────────────────────────────────

interface WebhookSubscription {
  subscription_id: string
  url: string
  events: string[]
  description?: string
  secret?: string
  is_active: boolean
  created_at: string
  last_triggered_at?: string
  last_delivery_at?: string
  total_deliveries?: number
  successful_deliveries?: number
  failed_deliveries?: number
  failed_attempts?: number
}

interface DeliveryAttempt {
  delivery_id: string
  event_type?: string
  status_code?: number
  duration_ms?: number
  attempted_at: string
  success: boolean
  error?: string
  response_body?: string
}

interface TestResult {
  success: boolean
  status_code?: number
  error?: string
  duration_ms: number
}

// ─── Hooks ──────────────────────────────────────────────────────────────────

function useWebhooks() {
  return useQuery({
    queryKey: ['webhooks-manager'],
    queryFn: () => webhooksApiV2.list() as unknown as Promise<WebhookSubscription[]>,
  })
}

function useEventTypes() {
  return useQuery({
    queryKey: ['webhook-event-types'],
    queryFn: webhooksApiV2.eventTypes,
    staleTime: 5 * 60 * 1000,
  })
}

function useWebhookDeliveries(subscriptionId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['webhook-deliveries', subscriptionId],
    queryFn: () => webhooksApiV2.deliveries(subscriptionId) as unknown as Promise<DeliveryAttempt[]>,
    enabled,
    refetchOnWindowFocus: false,
  })
}

function useCreateWebhook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { url: string; events: string[]; description?: string }) =>
      webhooksApiV2.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks-manager'] }),
  })
}

function useUpdateWebhook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { url?: string; events?: string[]; is_active?: boolean; description?: string } }) =>
      webhooksApiV2.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks-manager'] }),
  })
}

function useDeleteWebhook() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => webhooksApiV2.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks-manager'] }),
  })
}

function useTestWebhook() {
  return useMutation({
    mutationFn: (id: string) => webhooksApiV2.test(id) as unknown as Promise<TestResult>,
  })
}

function useRotateSecret() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => webhooksApiV2.rotateSecret(id) as unknown as Promise<{ secret: string }>,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['webhooks-manager'] }),
  })
}

// ─── Status Badge ───────────────────────────────────────────────────────────

function StatusCodeBadge({ code }: { code?: number }) {
  if (!code) return <span className="text-gray-500 text-xs">—</span>
  const colorClass =
    code >= 200 && code < 300
      ? 'bg-green-500/10 text-green-400'
      : code >= 400 && code < 500
      ? 'bg-yellow-500/10 text-yellow-400'
      : 'bg-red-500/10 text-red-400'
  return (
    <span className={clsx('px-2 py-0.5 rounded text-xs font-mono font-medium', colorClass)}>
      {code}
    </span>
  )
}

// ─── Copy Button ────────────────────────────────────────────────────────────

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      className="p-1 text-gray-500 hover:text-sardis-400 transition-colors"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

// ─── Delivery Log ───────────────────────────────────────────────────────────

function DeliveryLog({ subscriptionId }: { subscriptionId: string }) {
  const { data: deliveries = [], isLoading } = useWebhookDeliveries(subscriptionId, true)

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-dark-200 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (deliveries.length === 0) {
    return (
      <div className="p-6 text-center text-gray-500 text-sm">
        No delivery attempts yet
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-dark-100">
            <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Timestamp</th>
            <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Event</th>
            <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Status</th>
            <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Duration</th>
            <th className="text-left px-4 py-2 text-xs text-gray-500 font-medium">Result</th>
          </tr>
        </thead>
        <tbody>
          {deliveries.map((d) => (
            <tr key={d.delivery_id} className="border-b border-dark-100/50 hover:bg-dark-200/30">
              <td className="px-4 py-2 font-mono text-xs text-gray-400">
                {format(new Date(d.attempted_at), 'MMM d, HH:mm:ss')}
              </td>
              <td className="px-4 py-2 text-xs text-gray-400">
                {d.event_type || '—'}
              </td>
              <td className="px-4 py-2">
                <StatusCodeBadge code={d.status_code} />
              </td>
              <td className="px-4 py-2 text-xs text-gray-400">
                {d.duration_ms != null ? `${d.duration_ms}ms` : '—'}
              </td>
              <td className="px-4 py-2">
                {d.success ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <span title={d.error}>
                    <XCircle className="w-4 h-4 text-red-500" />
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Webhook Card ────────────────────────────────────────────────────────────

interface WebhookCardProps {
  webhook: WebhookSubscription
  onEdit: (webhook: WebhookSubscription) => void
}

function WebhookCard({ webhook, onEdit }: WebhookCardProps) {
  const [showDeliveries, setShowDeliveries] = useState(false)
  const [showConfirmDelete, setShowConfirmDelete] = useState(false)
  const [showConfirmRotate, setShowConfirmRotate] = useState(false)
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  const deleteWebhook = useDeleteWebhook()
  const testWebhook = useTestWebhook()
  const rotateSecret = useRotateSecret()

  const handleTest = async () => {
    setTestResult(null)
    try {
      const result = await testWebhook.mutateAsync(webhook.subscription_id)
      setTestResult(result)
    } catch {
      setTestResult({ success: false, error: 'Request failed', duration_ms: 0 })
    }
  }

  const handleRotate = async () => {
    setShowConfirmRotate(false)
    try {
      const result = await rotateSecret.mutateAsync(webhook.subscription_id)
      setNewSecret(result.secret)
    } catch {
      // no-op, mutation handles error state
    }
  }

  const handleDelete = async () => {
    setShowConfirmDelete(false)
    deleteWebhook.mutate(webhook.subscription_id)
  }

  const truncateUrl = (url: string, max = 60) =>
    url.length > max ? url.slice(0, max) + '…' : url

  return (
    <div className="card">
      {/* Main row */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          {/* Left: icon + info */}
          <div className="flex items-start gap-3 min-w-0">
            <div className={clsx(
              'mt-0.5 w-9 h-9 rounded-lg flex-shrink-0 flex items-center justify-center',
              webhook.is_active ? 'bg-green-500/10' : 'bg-gray-500/10'
            )}>
              <Webhook className={clsx(
                'w-4 h-4',
                webhook.is_active ? 'text-green-400' : 'text-gray-500'
              )} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-mono text-white truncate" title={webhook.url}>
                {truncateUrl(webhook.url)}
              </p>
              {webhook.description && (
                <p className="text-xs text-gray-500 mt-0.5">{webhook.description}</p>
              )}
              <p className="text-xs text-gray-600 mt-0.5">
                ID: {webhook.subscription_id}
              </p>
            </div>
          </div>

          {/* Right: status badge + actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={clsx(
              'px-2 py-0.5 rounded text-xs font-medium',
              webhook.is_active
                ? 'bg-green-500/10 text-green-400'
                : 'bg-gray-500/10 text-gray-400'
            )}>
              {webhook.is_active ? 'Active' : 'Inactive'}
            </span>

            {/* Test */}
            <button
              onClick={handleTest}
              disabled={testWebhook.isPending}
              title="Send test event"
              className="p-1.5 text-gray-400 hover:text-sardis-400 transition-colors disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
            </button>

            {/* Edit */}
            <button
              onClick={() => onEdit(webhook)}
              title="Edit webhook"
              className="p-1.5 text-gray-400 hover:text-blue-400 transition-colors"
            >
              <Edit2 className="w-4 h-4" />
            </button>

            {/* Rotate Secret */}
            <button
              onClick={() => setShowConfirmRotate(true)}
              title="Rotate signing secret"
              className="p-1.5 text-gray-400 hover:text-yellow-400 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            {/* Delete */}
            <button
              onClick={() => setShowConfirmDelete(true)}
              title="Delete webhook"
              className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Event badges */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {webhook.events?.map((event) => (
            <span
              key={event}
              className="px-2 py-0.5 bg-dark-100 rounded text-xs text-gray-400 font-mono"
            >
              {event}
            </span>
          ))}
          {(!webhook.events || webhook.events.length === 0) && (
            <span className="text-xs text-gray-600">No events configured</span>
          )}
        </div>

        {/* Stats + delivery toggle */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-dark-100">
          <div className="flex items-center gap-5 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
              {webhook.successful_deliveries ?? 0} delivered
            </span>
            {(webhook.failed_deliveries ?? webhook.failed_attempts ?? 0) > 0 && (
              <span className="flex items-center gap-1">
                <XCircle className="w-3.5 h-3.5 text-red-500" />
                {webhook.failed_deliveries ?? webhook.failed_attempts ?? 0} failed
              </span>
            )}
            {(webhook.last_triggered_at || webhook.last_delivery_at) && (
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Last: {format(
                  new Date(webhook.last_triggered_at || webhook.last_delivery_at || ''),
                  'MMM d, HH:mm'
                )}
              </span>
            )}
          </div>

          <button
            onClick={() => setShowDeliveries((v) => !v)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
          >
            {showDeliveries ? (
              <>Hide deliveries <ChevronUp className="w-3.5 h-3.5" /></>
            ) : (
              <>View deliveries <ChevronDown className="w-3.5 h-3.5" /></>
            )}
          </button>
        </div>

        {/* Inline test result */}
        {testResult !== null && (
          <div className={clsx(
            'mt-3 px-3 py-2 rounded-lg text-xs flex items-center gap-2',
            testResult.success
              ? 'bg-green-500/10 text-green-400'
              : 'bg-red-500/10 text-red-400'
          )}>
            {testResult.success ? (
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>
              {testResult.success
                ? `Test succeeded — ${testResult.status_code ?? ''} in ${testResult.duration_ms}ms`
                : `Test failed${testResult.error ? `: ${testResult.error}` : ''}`}
            </span>
            <button
              onClick={() => setTestResult(null)}
              className="ml-auto text-current opacity-60 hover:opacity-100"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* New secret reveal */}
        {newSecret && (
          <div className="mt-3 px-3 py-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <p className="text-xs text-yellow-400 mb-2 font-medium">
              New signing secret — copy now, it will not be shown again:
            </p>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono text-yellow-300 flex-1 break-all">
                {newSecret}
              </code>
              <CopyButton value={newSecret} />
              <button
                onClick={() => setNewSecret(null)}
                className="text-yellow-500 hover:text-yellow-300 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delivery log */}
      {showDeliveries && (
        <div className="border-t border-dark-100">
          <DeliveryLog subscriptionId={webhook.subscription_id} />
        </div>
      )}

      {/* Confirm delete dialog */}
      {showConfirmDelete && (
        <ConfirmDialog
          title="Delete webhook?"
          message={`This will permanently delete the webhook for ${truncateUrl(webhook.url, 45)} and stop all event deliveries.`}
          confirmLabel="Delete"
          confirmClass="bg-red-600 hover:bg-red-500 text-white"
          onConfirm={handleDelete}
          onCancel={() => setShowConfirmDelete(false)}
        />
      )}

      {/* Confirm rotate secret dialog */}
      {showConfirmRotate && (
        <ConfirmDialog
          title="Rotate signing secret?"
          message="The existing secret will be invalidated immediately. Update your receiver before confirming."
          confirmLabel="Rotate"
          confirmClass="bg-yellow-600 hover:bg-yellow-500 text-white"
          onConfirm={handleRotate}
          onCancel={() => setShowConfirmRotate(false)}
        />
      )}
    </div>
  )
}

// ─── Confirm Dialog ──────────────────────────────────────────────────────────

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

// ─── Create / Edit Modal ─────────────────────────────────────────────────────

interface WebhookFormData {
  url: string
  events: string[]
  description: string
}

interface WebhookModalProps {
  onClose: () => void
  onSubmit: (data: WebhookFormData) => Promise<void>
  isLoading: boolean
  eventTypes: string[]
  initialValues?: Partial<WebhookFormData>
  mode: 'create' | 'edit'
}

function WebhookModal({
  onClose,
  onSubmit,
  isLoading,
  eventTypes,
  initialValues,
  mode,
}: WebhookModalProps) {
  const [url, setUrl] = useState(initialValues?.url ?? '')
  const [description, setDescription] = useState(initialValues?.description ?? '')
  const [events, setEvents] = useState<string[]>(initialValues?.events ?? [])
  const [urlError, setUrlError] = useState('')

  const toggleEvent = (event: string) => {
    setEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    )
  }

  const toggleAll = () => {
    setEvents((prev) => (prev.length === eventTypes.length ? [] : [...eventTypes]))
  }

  const validateUrl = (val: string) => {
    try {
      new URL(val)
      setUrlError('')
      return true
    } catch {
      setUrlError('Please enter a valid URL starting with https://')
      return false
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateUrl(url)) return
    if (events.length === 0) return
    await onSubmit({ url, events, description })
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="card max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">
            {mode === 'create' ? 'Create Webhook' : 'Edit Webhook'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-500 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* URL */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">
              Endpoint URL <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                if (urlError) setUrlError('')
              }}
              onBlur={() => url && validateUrl(url)}
              className={clsx(
                'w-full px-4 py-2 bg-dark-300 border rounded-lg text-white text-sm focus:outline-none focus:border-sardis-500/50 placeholder:text-gray-600',
                urlError ? 'border-red-500/50' : 'border-dark-100'
              )}
              placeholder="https://your-app.com/webhooks/sardis"
            />
            {urlError && (
              <p className="mt-1 text-xs text-red-400">{urlError}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1.5">
              Description <span className="text-gray-600">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white text-sm focus:outline-none focus:border-sardis-500/50 placeholder:text-gray-600 resize-none"
              placeholder="e.g. Production payment alerts"
            />
          </div>

          {/* Events */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-400">
                Events <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={toggleAll}
                className="text-xs text-sardis-400 hover:text-sardis-300 transition-colors"
              >
                {events.length === eventTypes.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>
            {eventTypes.length === 0 ? (
              <p className="text-xs text-gray-600">Loading event types…</p>
            ) : (
              <div className="grid grid-cols-2 gap-1.5">
                {eventTypes.map((event) => (
                  <button
                    key={event}
                    type="button"
                    onClick={() => toggleEvent(event)}
                    className={clsx(
                      'px-3 py-2 rounded-lg text-xs font-mono font-medium transition-all text-left truncate',
                      events.includes(event)
                        ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                        : 'bg-dark-300 text-gray-400 border border-dark-100 hover:border-gray-600'
                    )}
                    title={event}
                  >
                    {event}
                  </button>
                ))}
              </div>
            )}
            {events.length === 0 && (
              <p className="mt-1.5 text-xs text-red-400">Select at least one event</p>
            )}
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
              disabled={isLoading || events.length === 0}
              className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50 text-sm"
            >
              {isLoading
                ? mode === 'create' ? 'Creating…' : 'Saving…'
                : mode === 'create' ? 'Create Webhook' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function WebhookManagerPage() {
  const { data: webhooks = [], isLoading } = useWebhooks()
  const { data: eventTypesData } = useEventTypes()
  const createWebhook = useCreateWebhook()
  const updateWebhook = useUpdateWebhook()

  const [showCreate, setShowCreate] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState<WebhookSubscription | null>(null)

  const eventTypes: string[] = eventTypesData?.event_types ?? [
    'payment.completed',
    'payment.failed',
    'payment.initiated',
    'wallet.created',
    'wallet.funded',
    'limit.exceeded',
    'risk.alert',
  ]

  const handleCreate = async (data: { url: string; events: string[]; description: string }) => {
    await createWebhook.mutateAsync(data)
    setShowCreate(false)
  }

  const handleEdit = async (data: { url: string; events: string[]; description: string }) => {
    if (!editingWebhook) return
    await updateWebhook.mutateAsync({
      id: editingWebhook.subscription_id,
      data: { url: data.url, events: data.events },
    })
    setEditingWebhook(null)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Webhooks</h1>
          <p className="text-gray-400 mt-1">
            Manage event subscriptions, test deliveries, and view logs
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
        >
          <Plus className="w-5 h-5" />
          Add Webhook
        </button>
      </div>

      {/* Stats bar */}
      {!isLoading && webhooks.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total</p>
            <p className="text-2xl font-bold text-white mt-1">{webhooks.length}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Active</p>
            <p className="text-2xl font-bold text-green-400 mt-1">
              {webhooks.filter((w) => w.is_active).length}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Total Deliveries</p>
            <p className="text-2xl font-bold text-white mt-1">
              {webhooks.reduce((acc, w) => acc + (w.total_deliveries ?? 0), 0)}
            </p>
          </div>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="flex gap-3">
                <div className="w-9 h-9 bg-dark-100 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-dark-100 rounded w-1/2" />
                  <div className="h-3 bg-dark-100 rounded w-1/4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : webhooks.length === 0 ? (
        <div className="card p-14 text-center">
          <Webhook className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No webhooks configured</h3>
          <p className="text-gray-500 mb-6 text-sm">
            Receive real-time event notifications by adding a webhook endpoint.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Create your first webhook
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {webhooks.map((webhook) => (
            <WebhookCard
              key={webhook.subscription_id}
              webhook={webhook}
              onEdit={setEditingWebhook}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <WebhookModal
          mode="create"
          eventTypes={eventTypes}
          isLoading={createWebhook.isPending}
          onClose={() => setShowCreate(false)}
          onSubmit={handleCreate}
        />
      )}

      {/* Edit modal */}
      {editingWebhook && (
        <WebhookModal
          mode="edit"
          eventTypes={eventTypes}
          isLoading={updateWebhook.isPending}
          onClose={() => setEditingWebhook(null)}
          onSubmit={handleEdit}
          initialValues={{
            url: editingWebhook.url,
            events: editingWebhook.events,
            description: editingWebhook.description ?? '',
          }}
        />
      )}
    </div>
  )
}
