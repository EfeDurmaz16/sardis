"use client";

import { Target, Activity, Zap, AlertTriangle } from 'lucide-react'

export default function GoalDriftPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Goal Drift Detection</h1>
        <p className="text-gray-400 mt-1">
          Monitor behavioral changes and spending pattern anomalies
        </p>
      </div>

      {/* Under Development Banner */}
      <div className="border border-yellow-500/30 bg-yellow-500/5 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-yellow-400">This feature is under development</p>
          <p className="text-xs text-gray-400 mt-1">
            Goal drift detection is not yet functional. The planned capabilities below are for reference only and do not reflect live functionality.
          </p>
        </div>
      </div>

      {/* Planned Capabilities (informational only) */}
      <div className="card p-16 text-center opacity-60">
        <div className="w-16 h-16 rounded-2xl bg-sardis-500/10 flex items-center justify-center mx-auto mb-6">
          <Target className="w-8 h-8 text-sardis-400" />
        </div>

        <h2 className="text-xl font-semibold text-white mb-3">
          Planned: Goal Drift Monitoring
        </h2>

        <p className="text-gray-400 max-w-lg mx-auto mb-8 leading-relaxed">
          Detect when AI agents deviate from their intended spending behavior.
          Behavioral fingerprinting, velocity governors, and drift alerting will
          surface anomalies before they become problems.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-3xl mx-auto mb-8">
          {[
            { label: 'Drift Alerts', desc: 'Pattern deviation detection', icon: <AlertTriangle className="w-5 h-5 text-yellow-500" /> },
            { label: 'Behavioral Fingerprint', desc: 'Baseline vs. current', icon: <Target className="w-5 h-5 text-sardis-400" /> },
            { label: 'Velocity Governors', desc: 'Rate limit monitoring', icon: <Zap className="w-5 h-5 text-orange-400" /> },
            { label: 'Spending Distribution', desc: 'Category shift tracking', icon: <Activity className="w-5 h-5 text-blue-400" /> },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-dark-300 border border-dark-100 p-4 text-left"
            >
              <div className="flex items-center gap-2 mb-2">
                {item.icon}
                <p className="text-sm font-medium text-white">{item.label}</p>
              </div>
              <p className="text-xs text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
