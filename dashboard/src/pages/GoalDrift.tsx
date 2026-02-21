import { useState, useEffect } from 'react'
import {
  Target,
  AlertTriangle,
  TrendingUp,
  Activity,
  Zap,
  Shield,
  BarChart3,
  Clock,
  DollarSign
} from 'lucide-react'
import clsx from 'clsx'
import StatCard from '../components/StatCard'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts'

// Mock data - will be replaced with API calls later
interface DriftAlert {
  id: string
  agent_id: string
  agent_name: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  drift_score: number
  category: string
  description: string
  detected_at: string
  status: 'active' | 'acknowledged' | 'resolved'
}

interface BehavioralFingerprint {
  agent_id: string
  metric: string
  baseline: number
  current: number
  drift_percentage: number
}

interface VelocityGovernor {
  agent_id: string
  agent_name: string
  tx_per_hour_limit: number
  current_tx_per_hour: number
  spending_velocity_limit: number
  current_spending_velocity: number
  is_throttled: boolean
  cooldown_until?: string
}

interface SpendingDistribution {
  category: string
  baseline: number
  current: number
}

export default function GoalDriftPage() {
  const [driftAlerts, setDriftAlerts] = useState<DriftAlert[]>([
    {
      id: 'alert_1',
      agent_id: 'agent_001',
      agent_name: 'shopping_agent',
      severity: 'medium',
      drift_score: 0.34,
      category: 'spending_pattern',
      description: 'Increased spending on new merchant category: Cloud Infrastructure',
      detected_at: '2024-01-15T12:00:00Z',
      status: 'active',
    },
    {
      id: 'alert_2',
      agent_id: 'agent_003',
      agent_name: 'research_ai',
      severity: 'critical',
      drift_score: 0.87,
      category: 'transaction_size',
      description: 'Transaction sizes 87% larger than baseline',
      detected_at: '2024-01-15T11:30:00Z',
      status: 'active',
    },
    {
      id: 'alert_3',
      agent_id: 'agent_002',
      agent_name: 'data_buyer',
      severity: 'low',
      drift_score: 0.15,
      category: 'merchant_diversity',
      description: 'Slight increase in merchant diversity',
      detected_at: '2024-01-15T11:00:00Z',
      status: 'acknowledged',
    },
    {
      id: 'alert_4',
      agent_id: 'agent_004',
      agent_name: 'trading_bot',
      severity: 'high',
      drift_score: 0.62,
      category: 'velocity',
      description: 'Transaction velocity exceeded normal operating range',
      detected_at: '2024-01-15T10:30:00Z',
      status: 'active',
    },
  ])

  const [fingerprints, setFingerprints] = useState<BehavioralFingerprint[]>([
    { agent_id: 'agent_001', metric: 'avg_transaction_size', baseline: 45.50, current: 67.20, drift_percentage: 47.7 },
    { agent_id: 'agent_001', metric: 'tx_per_day', baseline: 12, current: 18, drift_percentage: 50.0 },
    { agent_id: 'agent_001', metric: 'merchant_count', baseline: 3, current: 5, drift_percentage: 66.7 },
    { agent_id: 'agent_001', metric: 'refund_rate', baseline: 2.5, current: 1.8, drift_percentage: -28.0 },
    { agent_id: 'agent_001', metric: 'approval_time_seconds', baseline: 1.2, current: 0.9, drift_percentage: -25.0 },
  ])

  const [velocityGovernors, setVelocityGovernors] = useState<VelocityGovernor[]>([
    {
      agent_id: 'agent_001',
      agent_name: 'shopping_agent',
      tx_per_hour_limit: 10,
      current_tx_per_hour: 3,
      spending_velocity_limit: 500.00,
      current_spending_velocity: 145.50,
      is_throttled: false,
    },
    {
      agent_id: 'agent_002',
      agent_name: 'data_buyer',
      tx_per_hour_limit: 5,
      current_tx_per_hour: 2,
      spending_velocity_limit: 1000.00,
      current_spending_velocity: 320.00,
      is_throttled: false,
    },
    {
      agent_id: 'agent_003',
      agent_name: 'research_ai',
      tx_per_hour_limit: 3,
      current_tx_per_hour: 3,
      spending_velocity_limit: 200.00,
      current_spending_velocity: 195.00,
      is_throttled: true,
      cooldown_until: '2024-01-15T13:00:00Z',
    },
    {
      agent_id: 'agent_004',
      agent_name: 'trading_bot',
      tx_per_hour_limit: 50,
      current_tx_per_hour: 47,
      spending_velocity_limit: 5000.00,
      current_spending_velocity: 4650.00,
      is_throttled: false,
    },
  ])

  const [spendingDistribution, setSpendingDistribution] = useState<SpendingDistribution[]>([
    { category: 'Cloud Services', baseline: 40, current: 25 },
    { category: 'Data APIs', baseline: 30, current: 45 },
    { category: 'Software', baseline: 20, current: 15 },
    { category: 'Infrastructure', baseline: 10, current: 15 },
  ])

  // Behavioral fingerprint radar chart data
  const radarData = fingerprints.map(fp => ({
    metric: fp.metric.replace(/_/g, ' '),
    baseline: fp.baseline,
    current: fp.current,
  }))

  const handleAcknowledge = (alertId: string) => {
    setDriftAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, status: 'acknowledged' } : alert
    ))
  }

  const handleResolve = (alertId: string) => {
    setDriftAlerts(prev => prev.map(alert =>
      alert.id === alertId ? { ...alert, status: 'resolved' } : alert
    ))
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-500'
      case 'high':
        return 'text-orange-500'
      case 'medium':
        return 'text-yellow-500'
      case 'low':
        return 'text-blue-500'
      default:
        return 'text-gray-400'
    }
  }

  const getSeverityBgColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/30'
      case 'high':
        return 'bg-orange-500/10 border-orange-500/30'
      case 'medium':
        return 'bg-yellow-500/10 border-yellow-500/30'
      case 'low':
        return 'bg-blue-500/10 border-blue-500/30'
      default:
        return 'bg-dark-200 border-dark-100'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <AlertTriangle className="w-5 h-5" />
      case 'medium':
        return <Activity className="w-5 h-5" />
      case 'low':
        return <Target className="w-5 h-5" />
      default:
        return <Shield className="w-5 h-5" />
    }
  }

  const activeAlerts = driftAlerts.filter(a => a.status === 'active').length
  const criticalAlerts = driftAlerts.filter(a => a.severity === 'critical' && a.status === 'active').length
  const throttledAgents = velocityGovernors.filter(v => v.is_throttled).length
  const avgDriftScore = (driftAlerts.reduce((sum, a) => sum + a.drift_score, 0) / driftAlerts.length).toFixed(2)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Goal Drift Detection</h1>
        <p className="text-gray-400 mt-1">
          Monitor behavioral changes and spending pattern anomalies
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Alerts"
          value={activeAlerts}
          change={`${criticalAlerts} critical`}
          changeType={criticalAlerts > 0 ? 'negative' : 'positive'}
          icon={<AlertTriangle className="w-6 h-6" />}
        />
        <StatCard
          title="Avg Drift Score"
          value={avgDriftScore}
          change="Across all agents"
          changeType={parseFloat(avgDriftScore) > 0.5 ? 'negative' : 'positive'}
          icon={<Target className="w-6 h-6" />}
        />
        <StatCard
          title="Throttled Agents"
          value={throttledAgents}
          change="Velocity limited"
          changeType={throttledAgents > 0 ? 'negative' : 'positive'}
          icon={<Zap className="w-6 h-6" />}
        />
        <StatCard
          title="Monitoring"
          value={velocityGovernors.length}
          change="Agents tracked"
          changeType="positive"
          icon={<Activity className="w-6 h-6" />}
        />
      </div>

      {/* Drift Alerts */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Drift Alerts</h2>
            <p className="text-sm text-gray-400 mt-1">Behavioral anomalies and pattern changes</p>
          </div>
          <AlertTriangle className="w-5 h-5 text-sardis-400" />
        </div>

        <div className="space-y-3">
          {driftAlerts.map((alert) => (
            <div
              key={alert.id}
              className={clsx('p-4 border transition-all', getSeverityBgColor(alert.severity))}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={getSeverityColor(alert.severity)}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-white">{alert.agent_name}</span>
                      <span className={clsx(
                        'px-2 py-0.5 rounded text-xs font-medium uppercase',
                        getSeverityColor(alert.severity)
                      )}>
                        {alert.severity}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-dark-300 text-gray-400 rounded capitalize">
                        {alert.category.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300">{alert.description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={clsx('text-lg font-bold mono-numbers', getSeverityColor(alert.severity))}>
                    {(alert.drift_score * 100).toFixed(0)}%
                  </p>
                  <p className="text-xs text-gray-500">Drift</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-dark-100">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(alert.detected_at).toLocaleString()}</span>
                  <span>•</span>
                  <span className={clsx(
                    'capitalize',
                    alert.status === 'active' && 'text-yellow-500',
                    alert.status === 'acknowledged' && 'text-blue-500',
                    alert.status === 'resolved' && 'text-sardis-400'
                  )}>
                    {alert.status}
                  </span>
                </div>

                {alert.status === 'active' && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="px-3 py-1 text-xs font-medium bg-blue-500/10 text-blue-500 hover:bg-blue-500/20 border border-blue-500/30 transition-colors"
                    >
                      Acknowledge
                    </button>
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-3 py-1 text-xs font-medium bg-sardis-500/10 text-sardis-400 hover:bg-sardis-500/20 border border-sardis-500/30 transition-colors"
                    >
                      Resolve
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Behavioral Fingerprint & Spending Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Behavioral Fingerprint */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Behavioral Fingerprint</h2>
              <p className="text-sm text-gray-400 mt-1">Baseline vs current behavior</p>
            </div>
            <Target className="w-5 h-5 text-sardis-400" />
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="#2f2e2c" />
                <PolarAngleAxis
                  dataKey="metric"
                  stroke="#444341"
                  fontSize={11}
                  tick={{ fill: '#94a3b8' }}
                />
                <PolarRadiusAxis stroke="#444341" fontSize={10} />
                <Radar
                  name="Baseline"
                  dataKey="baseline"
                  stroke="#64748b"
                  fill="#64748b"
                  fillOpacity={0.2}
                />
                <Radar
                  name="Current"
                  dataKey="current"
                  stroke="#ff4f00"
                  fill="#ff4f00"
                  fillOpacity={0.3}
                />
                <Tooltip
                  contentStyle={{
                    background: '#1f1e1c',
                    border: '1px solid #2f2e2c',
                    borderRadius: '0px',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-gray-500 opacity-50" />
              <span className="text-xs text-gray-400">Baseline</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-sardis-500" />
              <span className="text-xs text-gray-400">Current</span>
            </div>
          </div>
        </div>

        {/* Spending Distribution */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Spending Distribution</h2>
              <p className="text-sm text-gray-400 mt-1">Category shifts from baseline</p>
            </div>
            <BarChart3 className="w-5 h-5 text-sardis-400" />
          </div>

          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={spendingDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2f2e2c" />
                <XAxis
                  dataKey="category"
                  stroke="#444341"
                  fontSize={11}
                  tickLine={false}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis stroke="#444341" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: '#1f1e1c',
                    border: '1px solid #2f2e2c',
                    borderRadius: '0px',
                  }}
                />
                <Bar dataKey="baseline" fill="#64748b" name="Baseline %" />
                <Bar dataKey="current" fill="#ff4f00" name="Current %" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Velocity Governors */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Velocity Governors</h2>
            <p className="text-sm text-gray-400 mt-1">Transaction and spending rate limits</p>
          </div>
          <Zap className="w-5 h-5 text-sardis-400" />
        </div>

        <div className="space-y-4">
          {velocityGovernors.map((governor) => (
            <div
              key={governor.agent_id}
              className={clsx(
                'p-4 border transition-all',
                governor.is_throttled
                  ? 'bg-red-500/10 border-red-500/30'
                  : 'bg-dark-200 border-dark-100 hover:border-sardis-500/30'
              )}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Zap className={clsx(
                    'w-5 h-5',
                    governor.is_throttled ? 'text-red-500' : 'text-sardis-400'
                  )} />
                  <span className="text-sm font-semibold text-white">{governor.agent_name}</span>
                  {governor.is_throttled && (
                    <span className="badge badge-error">Throttled</span>
                  )}
                </div>
                {governor.cooldown_until && (
                  <span className="text-xs text-red-500">
                    Cooldown until {new Date(governor.cooldown_until).toLocaleTimeString()}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-gray-500">Transaction Rate (per hour)</p>
                    <span className="text-xs font-medium text-white mono-numbers">
                      {governor.current_tx_per_hour} / {governor.tx_per_hour_limit}
                    </span>
                  </div>
                  <div className="w-full bg-dark-300 rounded-full h-2">
                    <div
                      className={clsx(
                        'h-2 rounded-full transition-all',
                        (governor.current_tx_per_hour / governor.tx_per_hour_limit) > 0.9
                          ? 'bg-red-500'
                          : (governor.current_tx_per_hour / governor.tx_per_hour_limit) > 0.75
                          ? 'bg-yellow-500'
                          : 'bg-sardis-500'
                      )}
                      style={{
                        width: `${Math.min((governor.current_tx_per_hour / governor.tx_per_hour_limit) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-gray-500">Spending Velocity ($/hr)</p>
                    <span className="text-xs font-medium text-white mono-numbers">
                      ${governor.current_spending_velocity.toFixed(0)} / ${governor.spending_velocity_limit.toFixed(0)}
                    </span>
                  </div>
                  <div className="w-full bg-dark-300 rounded-full h-2">
                    <div
                      className={clsx(
                        'h-2 rounded-full transition-all',
                        (governor.current_spending_velocity / governor.spending_velocity_limit) > 0.9
                          ? 'bg-red-500'
                          : (governor.current_spending_velocity / governor.spending_velocity_limit) > 0.75
                          ? 'bg-yellow-500'
                          : 'bg-sardis-500'
                      )}
                      style={{
                        width: `${Math.min((governor.current_spending_velocity / governor.spending_velocity_limit) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
