import { useState } from 'react'
import {
  Power,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  Activity,
  Link,
  Layers,
  RefreshCw,
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'
import {
  useKillSwitchStatus,
  useActivateKillSwitchRail,
  useDeactivateKillSwitchRail,
  useActivateKillSwitchChain,
  useDeactivateKillSwitchChain,
} from '../hooks/useApi'

/* ─── Constants ─── */

const RAILS = ['a2a', 'ap2', 'checkout'] as const
const CHAINS = ['base', 'ethereum', 'polygon', 'arbitrum', 'optimism', 'tempo_testnet', 'solana_devnet', 'morph'] as const

/* ─── Types ─── */

interface ActiveSwitch {
  reason: string
  activated_at: string
  activated_by: string
  notes?: string
  auto_reactivate_at?: string
}

interface ActivateFormState {
  reason: string
  notes: string
  auto_reactivate_after_seconds: string
}

interface PendingAction {
  type: 'rail' | 'chain'
  name: string
}

/* ─── Helpers ─── */

function formatDatetime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatTimeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.floor(diffHr / 24)}d ago`
}

/* ─── Activate Modal ─── */

interface ActivateModalProps {
  target: PendingAction
  onConfirm: (form: ActivateFormState) => void
  onCancel: () => void
  isLoading: boolean
}

function ActivateModal({ target, onConfirm, onCancel, isLoading }: ActivateModalProps) {
  const [form, setForm] = useState<ActivateFormState>({
    reason: '',
    notes: '',
    auto_reactivate_after_seconds: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.reason.trim()) return
    onConfirm(form)
  }

  const label = target.type === 'rail'
    ? `Rail: ${target.name.toUpperCase()}`
    : `Chain: ${target.name.charAt(0).toUpperCase() + target.name.slice(1)}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80"
        onClick={onCancel}
      />

      {/* Panel */}
      <div className="relative z-10 w-full max-w-lg bg-dark-300 border border-red-500/40 p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-red-500/10 border border-red-500/30">
            <Power className="w-5 h-5 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Activate Kill Switch</h2>
            <p className="text-sm text-red-400">{label}</p>
          </div>
        </div>

        <div className="bg-red-500/5 border border-red-500/20 p-3 mb-5">
          <p className="text-xs text-red-300">
            This will immediately halt all payments on this {target.type}. This action is logged and audited.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
              Reason <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
              placeholder="e.g. Suspicious transaction pattern detected"
              className="w-full px-3 py-2 bg-dark-400 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500/50"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
              Notes <span className="text-gray-600">(optional)</span>
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Additional context or incident reference..."
              rows={3}
              className="w-full px-3 py-2 bg-dark-400 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500/50 resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">
              Auto-reactivate after <span className="text-gray-600">(seconds, optional)</span>
            </label>
            <input
              type="number"
              min="60"
              value={form.auto_reactivate_after_seconds}
              onChange={(e) => setForm((f) => ({ ...f, auto_reactivate_after_seconds: e.target.value }))}
              placeholder="e.g. 3600 for 1 hour"
              className="w-full px-3 py-2 bg-dark-400 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-red-500/50"
            />
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-dark-400 border border-dark-100 text-gray-400 text-sm font-medium hover:border-gray-500 transition-all disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !form.reason.trim()}
              className="flex-1 px-4 py-2 bg-red-600 text-white text-sm font-bold hover:bg-red-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  Activate Kill Switch
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ─── Switch Card ─── */

interface SwitchCardProps {
  name: string
  activeSwitch: ActiveSwitch | null
  onActivate: () => void
  onDeactivate: () => void
  isDeactivating: boolean
  icon: React.ReactNode
  label: string
}

function SwitchCard({
  name: _name,
  activeSwitch,
  onActivate,
  onDeactivate,
  isDeactivating,
  icon,
  label,
}: SwitchCardProps) {
  const isActive = activeSwitch !== null

  return (
    <div
      className={clsx(
        'border transition-all p-4',
        isActive
          ? 'bg-red-950/40 border-red-500/50'
          : 'bg-dark-300 border-dark-100 hover:border-dark-50'
      )}
    >
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Pulse indicator */}
          <div className="relative flex-shrink-0">
            <div
              className={clsx(
                'w-2.5 h-2.5',
                isActive ? 'bg-red-500' : 'bg-sardis-500/60'
              )}
            />
            {isActive && (
              <div className="absolute inset-0 bg-red-500 animate-ping opacity-60" />
            )}
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            {icon}
            <span className="text-sm font-semibold text-white">{label}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isActive ? (
            <span className="px-2 py-0.5 bg-red-500/20 border border-red-500/40 text-red-400 text-xs font-bold tracking-widest uppercase">
              SUSPENDED
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-sardis-500/10 border border-sardis-500/20 text-sardis-400 text-xs font-medium">
              Operational
            </span>
          )}

          {isActive ? (
            <button
              onClick={onDeactivate}
              disabled={isDeactivating}
              className="px-3 py-1.5 bg-dark-400 border border-dark-100 text-gray-300 text-xs font-medium hover:border-sardis-500/40 hover:text-sardis-400 transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              {isDeactivating ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3 h-3" />
              )}
              Restore
            </button>
          ) : (
            <button
              onClick={onActivate}
              className="px-3 py-1.5 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-all flex items-center gap-1.5"
            >
              <Power className="w-3 h-3" />
              Kill
            </button>
          )}
        </div>
      </div>

      {/* Active details */}
      {isActive && activeSwitch && (
        <div className="mt-3 pt-3 border-t border-red-500/20 space-y-2">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-300 leading-tight">{activeSwitch.reason}</p>
          </div>

          {activeSwitch.notes && (
            <p className="text-xs text-gray-500 pl-5">{activeSwitch.notes}</p>
          )}

          <div className="flex items-center gap-4 pl-5 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {activeSwitch.activated_by}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTimeAgo(activeSwitch.activated_at)} &middot; {formatDatetime(activeSwitch.activated_at)}
            </span>
          </div>

          {activeSwitch.auto_reactivate_at && (
            <div className="pl-5 flex items-center gap-1 text-xs text-yellow-500">
              <RefreshCw className="w-3 h-3" />
              Auto-restores {formatDatetime(activeSwitch.auto_reactivate_at)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Page ─── */

export default function KillSwitchPage() {
  const { data, isLoading, isError } = useKillSwitchStatus()

  const activateRail = useActivateKillSwitchRail()
  const deactivateRail = useDeactivateKillSwitchRail()
  const activateChain = useActivateKillSwitchChain()
  const deactivateChain = useDeactivateKillSwitchChain()

  const [pendingActivation, setPendingActivation] = useState<PendingAction | null>(null)

  /* ─── Derived state ─── */

  const rails = (data?.rails ?? {}) as Record<string, ActiveSwitch | null>
  const chains = (data?.chains ?? {}) as Record<string, ActiveSwitch | null>

  const railsBlocked = RAILS.filter((r) => !!rails[r]).length
  const chainsBlocked = CHAINS.filter((c) => !!chains[c]).length
  const totalActive = railsBlocked + chainsBlocked

  const anyActive = totalActive > 0

  /* ─── Handlers ─── */

  const handleActivateConfirm = (form: ActivateFormState) => {
    if (!pendingActivation) return

    const payload = {
      reason: form.reason,
      notes: form.notes || undefined,
      auto_reactivate_after_seconds: form.auto_reactivate_after_seconds
        ? parseInt(form.auto_reactivate_after_seconds, 10)
        : undefined,
    }

    if (pendingActivation.type === 'rail') {
      activateRail.mutate(
        { rail: pendingActivation.name, ...payload },
        { onSuccess: () => setPendingActivation(null) }
      )
    } else {
      activateChain.mutate(
        { chain: pendingActivation.name, ...payload },
        { onSuccess: () => setPendingActivation(null) }
      )
    }
  }

  const isMutating =
    activateRail.isPending ||
    activateChain.isPending

  /* ─── Render ─── */

  if (isLoading) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Kill Switch</h1>
          <p className="text-gray-400 mt-1">Emergency payment suspension controls</p>
        </div>
        <div className="flex items-center justify-center h-64 text-gray-500">
          <RefreshCw className="w-6 h-6 animate-spin mr-3" />
          Loading kill switch status...
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Kill Switch</h1>
          <p className="text-gray-400 mt-1">Emergency payment suspension controls</p>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 p-6 flex items-center gap-3">
          <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div>
            <p className="text-red-400 font-medium">Failed to load kill switch status</p>
            <p className="text-sm text-gray-500 mt-1">Check API connectivity and try refreshing.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Activate modal */}
      {pendingActivation && (
        <ActivateModal
          target={pendingActivation}
          onConfirm={handleActivateConfirm}
          onCancel={() => setPendingActivation(null)}
          isLoading={isMutating}
        />
      )}

      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-white font-display flex items-center gap-3">
            <Power className="w-8 h-8 text-red-500" />
            Kill Switch
          </h1>
          <p className="text-gray-400 mt-1">
            Emergency stop system — immediately suspend payment execution on individual rails or chains.
            All activations are audited.
          </p>
        </div>

        {/* Status banner */}
        <div
          className={clsx(
            'border p-5 flex items-center justify-between',
            anyActive
              ? 'bg-red-950/50 border-red-500/60'
              : 'bg-dark-300 border-sardis-500/20'
          )}
        >
          <div className="flex items-center gap-4">
            <div className="relative flex-shrink-0">
              <div
                className={clsx(
                  'w-4 h-4',
                  anyActive ? 'bg-red-500' : 'bg-sardis-500'
                )}
              />
              {anyActive && (
                <div className="absolute inset-0 bg-red-500 animate-ping opacity-75" />
              )}
            </div>
            <div>
              {anyActive ? (
                <>
                  <p className="text-xl font-bold text-red-400 tracking-wide">PAYMENTS SUSPENDED</p>
                  <p className="text-sm text-red-300/70 mt-0.5">
                    {totalActive} kill switch{totalActive > 1 ? 'es' : ''} active
                    {railsBlocked > 0 && chainsBlocked > 0
                      ? ` — ${railsBlocked} rail${railsBlocked > 1 ? 's' : ''}, ${chainsBlocked} chain${chainsBlocked > 1 ? 's' : ''}`
                      : railsBlocked > 0
                      ? ` — ${railsBlocked} rail${railsBlocked > 1 ? 's' : ''}`
                      : ` — ${chainsBlocked} chain${chainsBlocked > 1 ? 's' : ''}`}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-xl font-bold text-sardis-400">All Systems Operational</p>
                  <p className="text-sm text-gray-500 mt-0.5">No kill switches active — payments flowing normally</p>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Activity className="w-4 h-4" />
            <span>Polling every 10s</span>
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard
            title="Total Active"
            value={totalActive}
            change={totalActive > 0 ? `${totalActive} suspended` : 'All clear'}
            changeType={totalActive > 0 ? 'negative' : 'positive'}
            icon={<Power className="w-6 h-6" />}
          />
          <StatCard
            title="Rails Blocked"
            value={railsBlocked}
            change={`${RAILS.length} total rails`}
            changeType={railsBlocked > 0 ? 'negative' : 'positive'}
            icon={<Link className="w-6 h-6" />}
          />
          <StatCard
            title="Chains Blocked"
            value={chainsBlocked}
            change={`${CHAINS.length} total chains`}
            changeType={chainsBlocked > 0 ? 'negative' : 'positive'}
            icon={<Layers className="w-6 h-6" />}
          />
        </div>

        {/* Rails section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Link className="w-5 h-5 text-sardis-400" />
                Payment Rails
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                Suspend specific payment protocols — A2A, AP2, and Checkout
              </p>
            </div>
            {railsBlocked > 0 && (
              <span className="px-3 py-1 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-bold">
                {railsBlocked} BLOCKED
              </span>
            )}
          </div>

          <div className="space-y-3">
            {RAILS.map((rail) => (
              <SwitchCard
                key={rail}
                name={rail}
                label={rail.toUpperCase()}
                activeSwitch={rails[rail] ?? null}
                icon={<Link className="w-4 h-4" />}
                onActivate={() => setPendingActivation({ type: 'rail', name: rail })}
                onDeactivate={() => deactivateRail.mutate(rail)}
                isDeactivating={deactivateRail.isPending && deactivateRail.variables === rail}
              />
            ))}
          </div>
        </div>

        {/* Chains section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-sardis-400" />
                Blockchain Networks
              </h2>
              <p className="text-sm text-gray-400 mt-1">
                Halt execution on specific chains — Base, Ethereum, Polygon, Arbitrum, Optimism
              </p>
            </div>
            {chainsBlocked > 0 && (
              <span className="px-3 py-1 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-bold">
                {chainsBlocked} BLOCKED
              </span>
            )}
          </div>

          <div className="space-y-3">
            {CHAINS.map((chain) => (
              <SwitchCard
                key={chain}
                name={chain}
                label={chain.charAt(0).toUpperCase() + chain.slice(1)}
                activeSwitch={chains[chain] ?? null}
                icon={<Layers className="w-4 h-4" />}
                onActivate={() => setPendingActivation({ type: 'chain', name: chain })}
                onDeactivate={() => deactivateChain.mutate(chain)}
                isDeactivating={deactivateChain.isPending && deactivateChain.variables === chain}
              />
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
