import { useEffect, useState } from 'react'
import {
  Search,
  ShieldCheck,
  ShieldX,
  Clock,
  Plus,
  Pencil,
  Trash2,
  AlertCircle,
  Users,
  X,
  ChevronDown,
  BarChart2,
  type LucideIcon,
} from 'lucide-react'
import clsx from 'clsx'
import {
  counterpartiesApi,
  type Counterparty,
  type CounterpartyTrustProfile,
} from '../api/client'

// ─── Types ───────────────────────────────────────────────────────────────────

type TrustStatus = 'pending' | 'approved' | 'blocked'
type CounterpartyType = 'merchant' | 'vendor' | 'agent' | 'service'

// ─── Config maps ─────────────────────────────────────────────────────────────

const TRUST_STATUS_CONFIG: Record<
  TrustStatus,
  { label: string; color: string; bg: string; icon: LucideIcon }
> = {
  pending:  { label: 'Pending',  color: 'text-yellow-400', bg: 'bg-yellow-500/10', icon: Clock },
  approved: { label: 'Approved', color: 'text-green-400',  bg: 'bg-green-500/10',  icon: ShieldCheck },
  blocked:  { label: 'Blocked',  color: 'text-red-400',    bg: 'bg-red-500/10',    icon: ShieldX },
} as const

const TYPE_CONFIG: Record<CounterpartyType, { label: string; color: string; bg: string }> = {
  merchant: { label: 'Merchant', color: 'text-sardis-400', bg: 'bg-sardis-500/10' },
  vendor:   { label: 'Vendor',   color: 'text-blue-400',   bg: 'bg-blue-500/10' },
  agent:    { label: 'Agent',    color: 'text-purple-400', bg: 'bg-purple-500/10' },
  service:  { label: 'Service',  color: 'text-gray-400',   bg: 'bg-gray-500/10' },
}

const COUNTERPARTY_TYPES: CounterpartyType[] = ['merchant', 'vendor', 'agent', 'service']
const TRUST_STATUSES: TrustStatus[] = ['pending', 'approved', 'blocked']

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function safeTrustStatus(s: string): TrustStatus {
  return (TRUST_STATUSES as string[]).includes(s) ? (s as TrustStatus) : 'pending'
}

function safeType(s: string): CounterpartyType {
  return (COUNTERPARTY_TYPES as string[]).includes(s) ? (s as CounterpartyType) : 'service'
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-dark-100">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-dark-200 animate-pulse rounded w-3/4" />
        </td>
      ))}
    </tr>
  )
}

interface TrustBadgeProps {
  status: TrustStatus
  onClick?: () => void
  interactive?: boolean
}

function TrustBadge({ status, onClick, interactive }: TrustBadgeProps) {
  const cfg = TRUST_STATUS_CONFIG[status]
  const Icon = cfg.icon
  return (
    <button
      onClick={onClick}
      disabled={!interactive}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium transition-colors',
        cfg.bg,
        cfg.color,
        interactive && 'hover:opacity-80 cursor-pointer',
        !interactive && 'cursor-default'
      )}
    >
      <Icon className="w-3 h-3" />
      {cfg.label}
    </button>
  )
}

interface TypeBadgeProps {
  type: CounterpartyType
}

function TypeBadge({ type }: TypeBadgeProps) {
  const cfg = TYPE_CONFIG[type]
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 text-xs font-medium', cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  )
}

// ─── Modal ───────────────────────────────────────────────────────────────────

interface FormState {
  name: string
  type: CounterpartyType
  identifier: string
  category: string
  trust_status: TrustStatus
  approval_required: boolean
}

const EMPTY_FORM: FormState = {
  name: '',
  type: 'merchant',
  identifier: '',
  category: '',
  trust_status: 'pending',
  approval_required: false,
}

interface CounterpartyModalProps {
  initial?: Counterparty | null
  onClose: () => void
  onSave: (data: FormState) => Promise<void>
  saving: boolean
}

function CounterpartyModal({ initial, onClose, onSave, saving }: CounterpartyModalProps) {
  const [form, setForm] = useState<FormState>(
    initial
      ? {
          name: initial.name,
          type: safeType(initial.type),
          identifier: initial.identifier,
          category: initial.category ?? '',
          trust_status: safeTrustStatus(initial.trust_status),
          approval_required: initial.approval_required,
        }
      : EMPTY_FORM
  )

  const isEdit = Boolean(initial)

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-lg bg-dark-300 border border-dark-100 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-100">
          <h2 className="text-lg font-semibold text-white">
            {isEdit ? 'Edit Counterparty' : 'Add Counterparty'}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Display Name *
            </label>
            <input
              required
              type="text"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="e.g. AWS, Stripe, OpenAI API"
              className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 text-sm"
            />
          </div>

          {/* Type + Trust Status */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Type
              </label>
              <select
                value={form.type}
                onChange={(e) => set('type', e.target.value as CounterpartyType)}
                className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50 text-sm"
              >
                {COUNTERPARTY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_CONFIG[t].label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Trust Status
              </label>
              <select
                value={form.trust_status}
                onChange={(e) => set('trust_status', e.target.value as TrustStatus)}
                className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50 text-sm"
              >
                {TRUST_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {TRUST_STATUS_CONFIG[s].label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Identifier */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Identifier *
            </label>
            <input
              required
              type="text"
              value={form.identifier}
              onChange={(e) => set('identifier', e.target.value)}
              placeholder="Wallet address, domain, or agent ID"
              className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 text-sm font-mono"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
              Category
            </label>
            <input
              type="text"
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
              placeholder="e.g. cloud, api, saas, travel"
              className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50 text-sm"
            />
          </div>

          {/* Approval Required toggle */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => set('approval_required', !form.approval_required)}
              className={clsx(
                'relative w-10 h-5 rounded-full transition-colors',
                form.approval_required ? 'bg-sardis-500' : 'bg-dark-100'
              )}
            >
              <span
                className={clsx(
                  'absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform',
                  form.approval_required ? 'translate-x-5' : 'translate-x-0.5'
                )}
              />
            </button>
            <span className="text-sm text-gray-300">Require approval for payments</span>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-sardis-500 text-dark-400 font-medium text-sm hover:bg-sardis-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Add Counterparty'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Confirm dialog ───────────────────────────────────────────────────────────

interface ConfirmDeleteProps {
  name: string
  onConfirm: () => void
  onCancel: () => void
  deleting: boolean
}

function ConfirmDelete({ name, onConfirm, onCancel, deleting }: ConfirmDeleteProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm bg-dark-300 border border-dark-100 shadow-2xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-white">Delete Counterparty</h2>
        <p className="text-sm text-gray-400">
          Are you sure you want to remove <span className="text-white font-medium">{name}</span>?
          This action cannot be undone.
        </p>
        <div className="flex items-center justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="px-6 py-2.5 bg-red-500 text-white font-medium text-sm hover:bg-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Trust Profile types ──────────────────────────────────────────────────────

// ─── Trust Score Gauge ────────────────────────────────────────────────────────

function TrustScoreGauge({ score }: { score: number }) {
  // Gauge arc: half-circle, 0=left, 1=right
  const pct = Math.max(0, Math.min(1, score))
  const color = score >= 0.8 ? '#4ade80' : score >= 0.5 ? '#facc15' : '#f87171'

  // SVG arc path for the gauge track
  const r = 56
  const cx = 80
  const cy = 80
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const arcX = (deg: number) => cx + r * Math.cos(toRad(deg - 90))
  const arcY = (deg: number) => cy + r * Math.sin(toRad(deg - 90))

  // Full track: 180 deg arc
  const trackStart = { x: arcX(-90), y: arcY(-90) }
  const trackEnd   = { x: arcX(90),  y: arcY(90) }

  // Fill arc up to current score
  const fillDeg = pct * 180 - 90
  const fillEnd = { x: arcX(fillDeg), y: arcY(fillDeg) }
  const largeArc = pct > 0.5 ? 1 : 0

  return (
    <div className="flex flex-col items-center">
      <svg width="160" height="90" viewBox="0 0 160 90">
        {/* Track */}
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${r} ${r} 0 0 1 ${trackEnd.x} ${trackEnd.y}`}
          fill="none"
          stroke="#374151"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Fill */}
        {pct > 0 && (
          <path
            d={`M ${trackStart.x} ${trackStart.y} A ${r} ${r} 0 ${largeArc} 1 ${fillEnd.x} ${fillEnd.y}`}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
          />
        )}
        {/* Needle dot */}
        <circle cx={fillEnd.x} cy={fillEnd.y} r="5" fill={color} />
      </svg>
      <p className="text-3xl font-bold mono-numbers" style={{ color }}>
        {(pct * 100).toFixed(0)}
      </p>
      <p className="text-xs text-gray-500 uppercase tracking-wider mt-0.5">Trust Score</p>
    </div>
  )
}

// ─── Trust Profile Modal ──────────────────────────────────────────────────────

interface TrustProfileModalProps {
  counterpartyId: string
  onClose: () => void
}

const PROOF_STATUS_CONFIG = {
  verified: { label: 'Verified',  color: 'text-green-400',  bg: 'bg-green-500/10' },
  partial:  { label: 'Partial',   color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  none:     { label: 'No Proof',  color: 'text-red-400',    bg: 'bg-red-500/10' },
} as const

function TrustProfileModal({ counterpartyId, onClose }: TrustProfileModalProps) {
  const [profile, setProfile] = useState<CounterpartyTrustProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    counterpartiesApi
      .getTrustProfile(counterpartyId)
      .then(setProfile)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load trust profile'))
      .finally(() => setLoading(false))
  }, [counterpartyId])

  const proofCfg = profile
    ? PROOF_STATUS_CONFIG[profile.proof_status] ?? PROOF_STATUS_CONFIG.none
    : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-lg bg-dark-300 border border-dark-100 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-100">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-sardis-400" />
            Trust Profile
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          {loading && (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-4 bg-dark-200 animate-pulse rounded w-3/4" />
              ))}
            </div>
          )}

          {error && (
            <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {profile && (
            <div className="space-y-6">
              {/* Name + gauge */}
              <div className="flex items-center gap-6">
                <TrustScoreGauge score={profile.trust_score} />
                <div className="flex-1 space-y-2">
                  <p className="text-xl font-semibold text-white">{profile.name}</p>

                  {/* Policy compatible */}
                  <div className="flex items-center gap-2">
                    {profile.policy_compatible ? (
                      <ShieldCheck className="w-4 h-4 text-green-400" />
                    ) : (
                      <ShieldX className="w-4 h-4 text-red-400" />
                    )}
                    <span className={clsx('text-sm', profile.policy_compatible ? 'text-green-400' : 'text-red-400')}>
                      {profile.policy_compatible ? 'Policy Compatible' : 'Policy Incompatible'}
                    </span>
                  </div>

                  {/* Proof status */}
                  {proofCfg && (
                    <span className={clsx('inline-flex items-center px-2.5 py-0.5 text-xs font-medium', proofCfg.bg, proofCfg.color)}>
                      {proofCfg.label}
                    </span>
                  )}

                  {/* Flags */}
                  {profile.flags.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {profile.flags.map((flag) => (
                        <span key={flag} className="inline-flex items-center px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-400">
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Total Transactions', value: String(profile.total_transactions) },
                  { label: 'Total Volume',        value: profile.total_volume },
                  { label: 'Success Rate',        value: `${(profile.success_rate * 100).toFixed(0)}%` },
                  { label: 'Avg Settlement',      value: profile.avg_settlement_time },
                  { label: 'Settlement Via',      value: profile.settlement_preference.toUpperCase() },
                  { label: 'Last Transaction',    value: profile.last_transaction ?? 'Never' },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-dark-200 p-3">
                    <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
                    <p className="text-sm font-medium text-white mono-numbers">{value}</p>
                  </div>
                ))}
              </div>

              {/* Recent history placeholder */}
              <div className="bg-dark-200 p-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Recent Transactions</p>
                <p className="text-sm text-gray-600 text-center py-4">No transactions recorded yet</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end px-6 py-4 border-t border-dark-100">
          <button
            onClick={onClose}
            className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CounterpartiesPage() {
  const [counterparties, setCounterparties] = useState<Counterparty[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<CounterpartyType | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<TrustStatus | 'all'>('all')
  const [typeOpen, setTypeOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Counterparty | null>(null)
  const [saving, setSaving] = useState(false)

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<Counterparty | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Inline status toggle optimism
  const [togglingId, setTogglingId] = useState<string | null>(null)

  // Trust profile modal
  const [trustProfileTarget, setTrustProfileTarget] = useState<string | null>(null)

  // Load on mount
  const loadCounterparties = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await counterpartiesApi.list({ limit: 200 })
      setCounterparties(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load counterparties')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCounterparties()
  }, [])

  // Filtered view
  const filtered = counterparties.filter((c) => {
    const matchSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.identifier.toLowerCase().includes(search.toLowerCase()) ||
      (c.category ?? '').toLowerCase().includes(search.toLowerCase())
    const matchType = typeFilter === 'all' || c.type === typeFilter
    const matchStatus = statusFilter === 'all' || c.trust_status === statusFilter
    return matchSearch && matchType && matchStatus
  })

  // Stats
  const approvedCount = counterparties.filter((c) => c.trust_status === 'approved').length
  const pendingCount = counterparties.filter((c) => c.trust_status === 'pending').length
  const blockedCount = counterparties.filter((c) => c.trust_status === 'blocked').length

  // Handlers
  const handleOpenAdd = () => {
    setEditTarget(null)
    setModalOpen(true)
  }

  const handleOpenEdit = (c: Counterparty) => {
    setEditTarget(c)
    setModalOpen(true)
  }

  const handleSave = async (form: FormState) => {
    setSaving(true)
    try {
      if (editTarget) {
        const updated = await counterpartiesApi.update(editTarget.id, {
          name: form.name,
          trust_status: form.trust_status,
          approval_required: form.approval_required,
          category: form.category || undefined,
        })
        setCounterparties((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      } else {
        const created = await counterpartiesApi.create({
          name: form.name,
          type: form.type,
          identifier: form.identifier,
          category: form.category || undefined,
          trust_status: form.trust_status,
          approval_required: form.approval_required,
        })
        setCounterparties((prev) => [created, ...prev])
      }
      setModalOpen(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await counterpartiesApi.delete(deleteTarget.id)
      setCounterparties((prev) => prev.filter((c) => c.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete')
    } finally {
      setDeleting(false)
    }
  }

  const handleToggleStatus = async (c: Counterparty) => {
    const next: TrustStatus =
      c.trust_status === 'approved' ? 'blocked' : 'approved'
    setTogglingId(c.id)
    try {
      const updated = await counterpartiesApi.update(c.id, { trust_status: next })
      setCounterparties((prev) => prev.map((x) => (x.id === updated.id ? updated : x)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update status')
    } finally {
      setTogglingId(null)
    }
  }

  return (
    <div className="space-y-8">
      {/* Modals */}
      {modalOpen && (
        <CounterpartyModal
          initial={editTarget}
          onClose={() => setModalOpen(false)}
          onSave={handleSave}
          saving={saving}
        />
      )}
      {deleteTarget && (
        <ConfirmDelete
          name={deleteTarget.name}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          deleting={deleting}
        />
      )}
      {trustProfileTarget && (
        <TrustProfileModal
          counterpartyId={trustProfileTarget}
          onClose={() => setTrustProfileTarget(null)}
        />
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Trusted Counterparties</h1>
          <p className="text-gray-400 mt-1">
            Registry of approved vendors, merchants, and agent peers for policy referencing
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 font-medium text-sm hover:bg-sardis-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Counterparty
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total', value: counterparties.length, color: 'text-white' },
          { label: 'Approved', value: approvedCount, color: 'text-green-400' },
          { label: 'Pending', value: pendingCount, color: 'text-yellow-400' },
          { label: 'Blocked', value: blockedCount, color: 'text-red-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="card p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
            <p className={clsx('text-3xl font-bold mt-1 mono-numbers', color)}>
              {isLoading ? '—' : value}
            </p>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search by name, identifier, or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>

        {/* Type filter */}
        <div className="relative">
          <button
            onClick={() => { setTypeOpen(!typeOpen); setStatusOpen(false) }}
            className="flex items-center gap-2 px-4 py-3 bg-dark-200 border border-dark-100 text-gray-300 hover:border-sardis-500/50 transition-colors min-w-[160px] justify-between"
          >
            <span className="text-sm">
              {typeFilter === 'all' ? 'All Types' : TYPE_CONFIG[typeFilter].label}
            </span>
            <ChevronDown className={clsx('w-4 h-4 transition-transform', typeOpen && 'rotate-180')} />
          </button>
          {typeOpen && (
            <div className="absolute right-0 mt-1 w-full bg-dark-300 border border-dark-100 z-10 shadow-lg">
              <button
                onClick={() => { setTypeFilter('all'); setTypeOpen(false) }}
                className={clsx('w-full text-left px-4 py-2.5 text-sm hover:bg-dark-200', typeFilter === 'all' ? 'text-sardis-400' : 'text-gray-300')}
              >
                All Types
              </button>
              {COUNTERPARTY_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => { setTypeFilter(t); setTypeOpen(false) }}
                  className={clsx('w-full text-left px-4 py-2.5 text-sm hover:bg-dark-200', typeFilter === t ? 'text-sardis-400' : 'text-gray-300')}
                >
                  {TYPE_CONFIG[t].label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Status filter */}
        <div className="relative">
          <button
            onClick={() => { setStatusOpen(!statusOpen); setTypeOpen(false) }}
            className="flex items-center gap-2 px-4 py-3 bg-dark-200 border border-dark-100 text-gray-300 hover:border-sardis-500/50 transition-colors min-w-[160px] justify-between"
          >
            <span className="text-sm">
              {statusFilter === 'all' ? 'All Statuses' : TRUST_STATUS_CONFIG[statusFilter].label}
            </span>
            <ChevronDown className={clsx('w-4 h-4 transition-transform', statusOpen && 'rotate-180')} />
          </button>
          {statusOpen && (
            <div className="absolute right-0 mt-1 w-full bg-dark-300 border border-dark-100 z-10 shadow-lg">
              <button
                onClick={() => { setStatusFilter('all'); setStatusOpen(false) }}
                className={clsx('w-full text-left px-4 py-2.5 text-sm hover:bg-dark-200', statusFilter === 'all' ? 'text-sardis-400' : 'text-gray-300')}
              >
                All Statuses
              </button>
              {TRUST_STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setStatusOpen(false) }}
                  className={clsx('w-full text-left px-4 py-2.5 text-sm hover:bg-dark-200', statusFilter === s ? 'text-sardis-400' : 'text-gray-300')}
                >
                  {TRUST_STATUS_CONFIG[s].label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-dark-300">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Identifier
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Category
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Trust Status
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Approval
              </th>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Added
              </th>
              <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-100">
            {isLoading
              ? Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)
              : filtered.map((c) => {
                  const ts = safeTrustStatus(c.trust_status)
                  const ct = safeType(c.type)
                  const isToggling = togglingId === c.id
                  return (
                    <tr key={c.id} className="hover:bg-dark-200/50 transition-colors">
                      {/* Name */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-sardis-500/10 flex items-center justify-center flex-shrink-0">
                            <Users className="w-4 h-4 text-sardis-400" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{c.name}</p>
                            <p className="text-xs text-gray-500 font-mono">{c.id}</p>
                          </div>
                        </div>
                      </td>

                      {/* Type */}
                      <td className="px-6 py-4">
                        <TypeBadge type={ct} />
                      </td>

                      {/* Identifier */}
                      <td className="px-6 py-4 max-w-[200px]">
                        <span className="text-xs text-gray-400 font-mono truncate block" title={c.identifier}>
                          {c.identifier}
                        </span>
                      </td>

                      {/* Category */}
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">
                          {c.category ?? <span className="text-gray-600">—</span>}
                        </span>
                      </td>

                      {/* Trust Status — click to toggle approved/blocked */}
                      <td className="px-6 py-4">
                        {isToggling ? (
                          <span className="text-xs text-gray-500 animate-pulse">Updating...</span>
                        ) : (
                          <TrustBadge
                            status={ts}
                            interactive={ts !== 'pending'}
                            onClick={ts !== 'pending' ? () => handleToggleStatus(c) : undefined}
                          />
                        )}
                      </td>

                      {/* Approval Required */}
                      <td className="px-6 py-4">
                        <span
                          className={clsx(
                            'text-xs font-medium',
                            c.approval_required ? 'text-yellow-400' : 'text-gray-600'
                          )}
                        >
                          {c.approval_required ? 'Required' : 'No'}
                        </span>
                      </td>

                      {/* Added */}
                      <td className="px-6 py-4">
                        <span className="text-sm text-gray-400">{formatDate(c.created_at)}</span>
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setTrustProfileTarget(c.id)}
                            className="p-1.5 text-gray-500 hover:text-sardis-400 hover:bg-sardis-500/10 transition-colors"
                            title="View Trust Profile"
                          >
                            <BarChart2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleOpenEdit(c)}
                            className="p-1.5 text-gray-500 hover:text-white hover:bg-dark-200 transition-colors"
                            title="Edit"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setDeleteTarget(c)}
                            className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
          </tbody>
        </table>

        {/* Empty state */}
        {!isLoading && filtered.length === 0 && (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No counterparties found</h3>
            <p className="text-gray-400 mb-6">
              {search || typeFilter !== 'all' || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Add your first trusted counterparty to get started'}
            </p>
            {!search && typeFilter === 'all' && statusFilter === 'all' && (
              <button
                onClick={handleOpenAdd}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 font-medium text-sm hover:bg-sardis-400 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Counterparty
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
