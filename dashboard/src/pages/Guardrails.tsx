import { useState, useEffect } from 'react'
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
  Building
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'

// Mock data - will be replaced with API calls later
interface CircuitBreaker {
  id: string
  name: string
  scope: 'global' | 'organization' | 'agent'
  state: 'CLOSED' | 'HALF_OPEN' | 'OPEN'
  failure_threshold: number
  current_failures: number
  timeout_seconds: number
  last_triggered?: string
}

interface KillSwitch {
  id: string
  name: string
  scope: 'global' | 'organization' | 'agent'
  entity_id?: string
  is_active: boolean
  reason?: string
  activated_at?: string
  activated_by?: string
}

interface RateLimiter {
  id: string
  name: string
  scope: 'global' | 'organization' | 'agent'
  entity_id?: string
  max_requests: number
  current_requests: number
  window_seconds: number
  utilization: number
  resets_at: string
}

export default function GuardrailsPage() {
  const [circuitBreakers, setCircuitBreakers] = useState<CircuitBreaker[]>([
    {
      id: 'cb_1',
      name: 'Payment Execution',
      scope: 'global',
      state: 'CLOSED',
      failure_threshold: 5,
      current_failures: 0,
      timeout_seconds: 60,
    },
    {
      id: 'cb_2',
      name: 'Agent shopping_agent_001',
      scope: 'agent',
      state: 'HALF_OPEN',
      failure_threshold: 3,
      current_failures: 2,
      timeout_seconds: 120,
      last_triggered: '2024-01-15T10:30:00Z',
    },
    {
      id: 'cb_3',
      name: 'Chain: Base',
      scope: 'global',
      state: 'CLOSED',
      failure_threshold: 10,
      current_failures: 1,
      timeout_seconds: 300,
    },
    {
      id: 'cb_4',
      name: 'MPC Signing',
      scope: 'global',
      state: 'OPEN',
      failure_threshold: 5,
      current_failures: 5,
      timeout_seconds: 180,
      last_triggered: '2024-01-15T11:45:00Z',
    },
  ])

  const [killSwitches, setKillSwitches] = useState<KillSwitch[]>([
    {
      id: 'ks_1',
      name: 'Global Emergency Stop',
      scope: 'global',
      is_active: false,
    },
    {
      id: 'ks_2',
      name: 'Org: Acme Corp',
      scope: 'organization',
      entity_id: 'org_acme',
      is_active: false,
    },
    {
      id: 'ks_3',
      name: 'Agent: research_ai_003',
      scope: 'agent',
      entity_id: 'agent_research_003',
      is_active: true,
      reason: 'Suspicious spending pattern detected',
      activated_at: '2024-01-15T09:00:00Z',
      activated_by: 'system',
    },
  ])

  const [rateLimiters, setRateLimiters] = useState<RateLimiter[]>([
    {
      id: 'rl_1',
      name: 'Global Transaction Rate',
      scope: 'global',
      max_requests: 1000,
      current_requests: 247,
      window_seconds: 60,
      utilization: 24.7,
      resets_at: '2024-01-15T12:01:00Z',
    },
    {
      id: 'rl_2',
      name: 'Org: Tech Startup Inc',
      scope: 'organization',
      entity_id: 'org_tech_startup',
      max_requests: 500,
      current_requests: 478,
      window_seconds: 60,
      utilization: 95.6,
      resets_at: '2024-01-15T12:01:00Z',
    },
    {
      id: 'rl_3',
      name: 'Agent: trading_bot',
      scope: 'agent',
      entity_id: 'agent_trading_bot',
      max_requests: 100,
      current_requests: 12,
      window_seconds: 60,
      utilization: 12.0,
      resets_at: '2024-01-15T12:01:00Z',
    },
    {
      id: 'rl_4',
      name: 'Chain: Polygon',
      scope: 'global',
      max_requests: 200,
      current_requests: 156,
      window_seconds: 60,
      utilization: 78.0,
      resets_at: '2024-01-15T12:01:00Z',
    },
  ])

  const toggleCircuitBreaker = (id: string) => {
    setCircuitBreakers(prev => prev.map(cb => {
      if (cb.id === id) {
        let newState: CircuitBreaker['state'] = 'CLOSED'
        if (cb.state === 'CLOSED') newState = 'OPEN'
        else if (cb.state === 'OPEN') newState = 'HALF_OPEN'
        else newState = 'CLOSED'

        return {
          ...cb,
          state: newState,
          last_triggered: newState !== 'CLOSED' ? new Date().toISOString() : cb.last_triggered,
        }
      }
      return cb
    }))
  }

  const toggleKillSwitch = (id: string) => {
    setKillSwitches(prev => prev.map(ks => {
      if (ks.id === id) {
        return {
          ...ks,
          is_active: !ks.is_active,
          activated_at: !ks.is_active ? new Date().toISOString() : ks.activated_at,
          activated_by: !ks.is_active ? 'manual' : ks.activated_by,
          reason: !ks.is_active ? 'Manual activation from dashboard' : ks.reason,
        }
      }
      return ks
    }))
  }

  const getStateColor = (state: CircuitBreaker['state']) => {
    switch (state) {
      case 'CLOSED':
        return 'text-sardis-400'
      case 'HALF_OPEN':
        return 'text-yellow-500'
      case 'OPEN':
        return 'text-red-500'
    }
  }

  const getStateIcon = (state: CircuitBreaker['state']) => {
    switch (state) {
      case 'CLOSED':
        return <CheckCircle className="w-5 h-5" />
      case 'HALF_OPEN':
        return <AlertCircle className="w-5 h-5" />
      case 'OPEN':
        return <XCircle className="w-5 h-5" />
    }
  }

  const getScopeIcon = (scope: string) => {
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

  const activeKillSwitches = killSwitches.filter(ks => ks.is_active).length
  const openCircuitBreakers = circuitBreakers.filter(cb => cb.state === 'OPEN').length
  const highUtilizationLimiters = rateLimiters.filter(rl => rl.utilization > 80).length

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Guardrails</h1>
        <p className="text-gray-400 mt-1">
          Circuit breakers, kill switches, and rate limiters
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Circuit Breakers"
          value={circuitBreakers.length}
          change={`${openCircuitBreakers} open`}
          changeType={openCircuitBreakers > 0 ? 'negative' : 'positive'}
          icon={<Shield className="w-6 h-6" />}
        />
        <StatCard
          title="Kill Switches"
          value={killSwitches.length}
          change={`${activeKillSwitches} active`}
          changeType={activeKillSwitches > 0 ? 'negative' : 'positive'}
          icon={<Power className="w-6 h-6" />}
        />
        <StatCard
          title="Rate Limiters"
          value={rateLimiters.length}
          change={`${highUtilizationLimiters} high usage`}
          changeType={highUtilizationLimiters > 0 ? 'negative' : 'positive'}
          icon={<TrendingDown className="w-6 h-6" />}
        />
        <StatCard
          title="System Health"
          value="98.2%"
          change="Last 24h"
          changeType="positive"
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

        <div className="space-y-4">
          {circuitBreakers.map((cb) => (
            <div
              key={cb.id}
              className="p-4 bg-dark-200 border border-dark-100 hover:border-sardis-500/30 transition-all"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={clsx('flex items-center gap-2', getStateColor(cb.state))}>
                    {getStateIcon(cb.state)}
                    <span className="font-semibold text-white">{cb.name}</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                    {getScopeIcon(cb.scope)}
                    <span className="capitalize">{cb.scope}</span>
                  </div>
                </div>
                <button
                  onClick={() => toggleCircuitBreaker(cb.id)}
                  className={clsx(
                    'px-3 py-1.5 text-xs font-medium rounded transition-colors',
                    cb.state === 'CLOSED' && 'bg-sardis-500/10 text-sardis-400 hover:bg-sardis-500/20',
                    cb.state === 'HALF_OPEN' && 'bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20',
                    cb.state === 'OPEN' && 'bg-red-500/10 text-red-500 hover:bg-red-500/20'
                  )}
                >
                  {cb.state}
                </button>
              </div>

              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500 text-xs mb-1">Failures</p>
                  <p className="text-white font-medium mono-numbers">
                    {cb.current_failures} / {cb.failure_threshold}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Timeout</p>
                  <p className="text-white font-medium mono-numbers">{cb.timeout_seconds}s</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Health</p>
                  <div className="w-full bg-dark-300 rounded-full h-2 mt-1">
                    <div
                      className={clsx(
                        'h-2 rounded-full transition-all',
                        cb.state === 'CLOSED' && 'bg-sardis-500',
                        cb.state === 'HALF_OPEN' && 'bg-yellow-500',
                        cb.state === 'OPEN' && 'bg-red-500'
                      )}
                      style={{
                        width: `${((cb.failure_threshold - cb.current_failures) / cb.failure_threshold) * 100}%`,
                      }}
                    />
                  </div>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Last Triggered</p>
                  <p className="text-white font-medium text-xs">
                    {cb.last_triggered ? new Date(cb.last_triggered).toLocaleTimeString() : 'Never'}
                  </p>
                </div>
              </div>
            </div>
          ))}
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
            {killSwitches.map((ks) => (
              <div
                key={ks.id}
                className={clsx(
                  'p-4 border transition-all',
                  ks.is_active
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-dark-200 border-dark-100 hover:border-sardis-500/30'
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                      {getScopeIcon(ks.scope)}
                      <span className="capitalize">{ks.scope}</span>
                    </div>
                    <span className="text-sm font-medium text-white">{ks.name}</span>
                  </div>
                  <button
                    onClick={() => toggleKillSwitch(ks.id)}
                    className={clsx(
                      'px-3 py-1.5 text-xs font-medium rounded transition-colors',
                      ks.is_active
                        ? 'bg-red-500 text-white hover:bg-red-600'
                        : 'bg-dark-300 text-gray-400 hover:bg-sardis-500/20 hover:text-sardis-400'
                    )}
                  >
                    {ks.is_active ? 'ACTIVE' : 'Inactive'}
                  </button>
                </div>

                {ks.is_active && ks.reason && (
                  <div className="mt-2 pt-2 border-t border-red-500/20">
                    <p className="text-xs text-red-400">
                      <span className="text-gray-500">Reason:</span> {ks.reason}
                    </p>
                    {ks.activated_by && (
                      <p className="text-xs text-gray-500 mt-1">
                        By {ks.activated_by} at {new Date(ks.activated_at!).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
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

          <div className="space-y-4">
            {rateLimiters.map((rl) => (
              <div
                key={rl.id}
                className="p-4 bg-dark-200 border border-dark-100 hover:border-sardis-500/30 transition-all"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 px-2 py-0.5 bg-dark-300 rounded text-xs text-gray-400">
                      {getScopeIcon(rl.scope)}
                      <span className="capitalize">{rl.scope}</span>
                    </div>
                    <span className="text-sm font-medium text-white">{rl.name}</span>
                  </div>
                  <span
                    className={clsx(
                      'text-xs font-medium mono-numbers',
                      rl.utilization > 90 && 'text-red-500',
                      rl.utilization > 75 && rl.utilization <= 90 && 'text-yellow-500',
                      rl.utilization <= 75 && 'text-sardis-400'
                    )}
                  >
                    {rl.utilization.toFixed(1)}%
                  </span>
                </div>

                <div className="mb-2">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span className="mono-numbers">
                      {rl.current_requests} / {rl.max_requests} requests
                    </span>
                    <span>{rl.window_seconds}s window</span>
                  </div>
                  <div className="w-full bg-dark-300 rounded-full h-2">
                    <div
                      className={clsx(
                        'h-2 rounded-full transition-all',
                        rl.utilization > 90 && 'bg-red-500',
                        rl.utilization > 75 && rl.utilization <= 90 && 'bg-yellow-500',
                        rl.utilization <= 75 && 'bg-sardis-500'
                      )}
                      style={{ width: `${Math.min(rl.utilization, 100)}%` }}
                    />
                  </div>
                </div>

                <p className="text-xs text-gray-500">
                  Resets at {new Date(rl.resets_at).toLocaleTimeString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
