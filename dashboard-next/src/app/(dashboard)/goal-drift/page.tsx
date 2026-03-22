"use client";

import { Target, Activity, Zap, AlertTriangle, ArrowRight } from 'lucide-react'

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

      {/* Coming Soon Card */}
      <div className="card p-16 text-center">
        <div className="w-16 h-16 rounded-2xl bg-sardis-500/10 flex items-center justify-center mx-auto mb-6">
          <Target className="w-8 h-8 text-sardis-400" />
        </div>

        <h2 className="text-xl font-semibold text-white mb-3">
          Goal Drift Monitoring — Coming Soon
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

        <div className="flex items-center justify-center gap-2 text-sm text-sardis-400">
          <span>Anomaly detection engine is live</span>
          <ArrowRight className="w-4 h-4" />
          <span>Drift UI launching next sprint</span>
        </div>
      </div>
    </div>
  )
}
