"use client";
import { useMemo } from 'react'
import {
  Shield,
  Zap,
  Power,
  TrendingDown,
  Activity,
  AlertCircle,
  CheckCircle,
  XCircle,
  Settings,
  Users,
  Building,
  Loader2,
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '@/components/StatCard'
import { useKillSwitchStatus } from '@/hooks/useApi'

interface KillSwitchRail {
  name: string
  is_active: boolean
  reason?: string
  activated_at?: string
  activated_by?: string
}

interface KillSwitchChain {
  chain: string
  is_active: boolean
  reason?: string
  activated_at?: string
}

function getScopeIcon(scope: string) {
  switch (scope) {
    case 'global':
      return <Shield className="w-4 h-4" />
    case 'organization':
      return <Building className="w-4 h-4" />
    case 'agent':
      return <Users className="w-4 h-4" />
    default:
      return <Settings className="w-4 h-4" />
  }
}

export default function GuardrailsPage() {
  const { data: killSwitchData, isLoading, isError, error } = useKillSwitchStatus()

  const killSwitchStatus = killSwitchData as Record<string, unknown> | undefined

  const rails = useMemo(() => {
    if (!killSwitchStatus) return []
    const railsObj = (killSwitchStatus.rails || {}) as Record<string, unknown>
    return Object.entries(railsObj).map(([name, val]) => {
      const v = val as Record<string, unknown>
      return {
        name,
        is_active: Boolean(v?.is_active),
        reason: (v?.reason as string) || undefined,
        activated_at: (v?.activated_at as string) || undefined,
        activated_by: (v?.activated_by as string) || undefined,
      } as KillSwitchRail
    })
  }, [killSwitchStatus])

  const chains = useMemo(() => {
    if (!killSwitchStatus) return []
    const chainsObj = (killSwitchStatus.chains || {}) as Record<string, unknown>
    return Object.entries(chainsObj).map(([chain, val]) => {
      const v = val as Record<string, unknown>
      return {
        chain,
        is_active: Boolean(v?.is_active),
        reason: (v?.reason as string) || undefined,
        activated_at: (v?.activated_at as string) || undefined,
      } as KillSwitchChain
    })
  }, [killSwitchStatus])

  const globalActive = Boolean(killSwitchStatus?.global_active)
  const activeKillSwitches = rails.filter(r => r.is_active).length + chains.filter(c => c.is_active).length + (globalActive ? 1 : 0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Guardrails</h1>
        <p className="text-gray-400 mt-1">
          Circuit breakers, kill switches, and rate limiters
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-sardis-400 animate-spin" />
          <span className="ml-3 text-gray-400">Loading guardrail status...</span>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="card p-6 border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-400">Failed to load guardrail status</p>
              <p className="text-xs text-gray-500 mt-1">{(error as Error)?.message || 'Unknown error'}</p>
            </div>
          </div>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Circuit Breakers"
              value="Server-managed"
              change="Auto-recovery enabled"
              changeType="positive"
              icon={<Shield className="w-6 h-6" />}
            />
            <StatCard
              title="Kill Switches"
              value={rails.length + chains.length + 1}
              change={`${activeKillSwitches} active`}
              changeType={activeKillSwitches > 0 ? 'negative' : 'positive'}
              icon={<Power className="w-6 h-6" />}
            />
            <StatCard
              title="Rate Limiters"
              value="Server-managed"
              change="Redis-enforced"
              changeType="positive"
              icon={<TrendingDown className="w-6 h-6" />}
            />
            <StatCard
              title="System Health"
              value={globalActive ? 'Halted' : 'Operational'}
              change={globalActive ? 'Global kill switch active' : 'All systems normal'}
              changeType={globalActive ? 'negative' : 'positive'}
              icon={<Activity className="w-6 h-6" />}
            />
          </div>

          {/* Circuit Breakers */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">Circuit Breakers</h2>
                <p className="text-sm text-gray-400 mt-1">Automatic failure protection and recovery</p>
              </div>
              <Shield className="w-5 h-5 text-sardis-400" />
            </div>

            <div className="p-8 bg-dark-200 border border-dark-100 text-center">
              <CheckCircle className="w-8 h-8 text-sardis-400 mx-auto mb-3" />
              <p className="text-sm text-white font-medium">Circuit breakers are server-managed</p>
              <p className="text-xs text-gray-500 mt-1">
                Automatic failure detection with exponential backoff recovery. Breakers trip after
                consecutive failures and auto-recover once the downstream service is healthy.
              </p>
            </div>
          </div>

          {/* Kill Switches & Rate Limiters */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Kill Switches */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">Kill Switches</h2>
                  <p className="text-sm text-gray-400 mt-1">Emergency stop controls</p>
                </div>
                <Power className="w-5 h-5 text-sardis-400" />
              </div>

              <div className="space-y-3">
                {/* Global kill switch */}
                <div
                  className={clsx(
                    'p-4 border transition-all',
                    globalActive
                      ? 'bg-red-500/10 border-red-500/30'
                      : 'bg-dark-200 border-dark-100'
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                        {getScopeIcon('global')}
                        <span className="capitalize">global</span>
                      </div>
                      <span className="text-sm font-medium text-white">Global Emergency Stop</span>
                    </div>
                    <span
                      className={clsx(
                        'px-3 py-1.5 text-xs font-medium rounded',
                        globalActive
                          ? 'bg-red-500 text-white'
                          : 'bg-dark-300 text-gray-400'
                      )}
                    >
                      {globalActive ? 'ACTIVE' : 'Inactive'}
                    </span>
                  </div>
                </div>

                {/* Rail kill switches */}
                {rails.map((rail) => (
                  <div
                    key={rail.name}
                    className={clsx(
                      'p-4 border transition-all',
                      rail.is_active
                        ? 'bg-red-500/10 border-red-500/30'
                        : 'bg-dark-200 border-dark-100'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                          {getScopeIcon('organization')}
                          <span>rail</span>
                        </div>
                        <span className="text-sm font-medium text-white">{rail.name}</span>
                      </div>
                      <span
                        className={clsx(
                          'px-3 py-1.5 text-xs font-medium rounded',
                          rail.is_active
                            ? 'bg-red-500 text-white'
                            : 'bg-dark-300 text-gray-400'
                        )}
                      >
                        {rail.is_active ? 'ACTIVE' : 'Inactive'}
                      </span>
                    </div>
                    {rail.is_active && rail.reason && (
                      <div className="mt-2 pt-2 border-t border-red-500/20">
                        <p className="text-xs text-red-400">
                          <span className="text-gray-500">Reason:</span> {rail.reason}
                        </p>
                        {rail.activated_by && rail.activated_at && (
                          <p className="text-xs text-gray-500 mt-1">
                            By {rail.activated_by} at {new Date(rail.activated_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Chain kill switches */}
                {chains.map((chain) => (
                  <div
                    key={chain.chain}
                    className={clsx(
                      'p-4 border transition-all',
                      chain.is_active
                        ? 'bg-red-500/10 border-red-500/30'
                        : 'bg-dark-200 border-dark-100'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                          {getScopeIcon('global')}
                          <span>chain</span>
                        </div>
                        <span className="text-sm font-medium text-white">Chain: {chain.chain}</span>
                      </div>
                      <span
                        className={clsx(
                          'px-3 py-1.5 text-xs font-medium rounded',
                          chain.is_active
                            ? 'bg-red-500 text-white'
                            : 'bg-dark-300 text-gray-400'
                        )}
                      >
                        {chain.is_active ? 'ACTIVE' : 'Inactive'}
                      </span>
                    </div>
                    {chain.is_active && chain.reason && (
                      <div className="mt-2 pt-2 border-t border-red-500/20">
                        <p className="text-xs text-red-400">
                          <span className="text-gray-500">Reason:</span> {chain.reason}
                        </p>
                      </div>
                    )}
                  </div>
                ))}

                {rails.length === 0 && chains.length === 0 && (
                  <div className="p-4 bg-dark-200 border border-dark-100 text-center">
                    <p className="text-sm text-gray-500">No rail or chain kill switches configured</p>
                  </div>
                )}
              </div>
            </div>

            {/* Rate Limiters */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">Rate Limiters</h2>
                  <p className="text-sm text-gray-400 mt-1">Request throttling and limits</p>
                </div>
                <Zap className="w-5 h-5 text-sardis-400" />
              </div>

              <div className="p-8 bg-dark-200 border border-dark-100 text-center">
                <Zap className="w-8 h-8 text-sardis-400 mx-auto mb-3" />
                <p className="text-sm text-white font-medium">Rate limiting is Redis-enforced</p>
                <p className="text-xs text-gray-500 mt-1">
                  Per-agent and per-API-key rate limits are enforced server-side via Redis
                  sliding-window counters. Configure per-key limits in API Keys settings.
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
