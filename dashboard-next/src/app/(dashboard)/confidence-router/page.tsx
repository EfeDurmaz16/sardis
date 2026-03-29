"use client";

import { Shield, AlertTriangle } from 'lucide-react'

export default function ConfidenceRouterPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Confidence Router</h1>
        <p className="text-gray-400 mt-1">
          Confidence-based transaction routing and approval workflows
        </p>
      </div>

      {/* Under Development Banner */}
      <div className="border border-yellow-500/30 bg-yellow-500/5 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-yellow-400">This feature is under development</p>
          <p className="text-xs text-gray-400 mt-1">
            Confidence-based routing is not yet functional. The tier definitions below are planned design targets and do not reflect live behavior.
          </p>
        </div>
      </div>

      {/* Planned Tiers (informational only) */}
      <div className="card p-16 text-center opacity-60">
        <div className="w-16 h-16 rounded-2xl bg-sardis-500/10 flex items-center justify-center mx-auto mb-6">
          <Shield className="w-8 h-8 text-sardis-400" />
        </div>

        <h2 className="text-xl font-semibold text-white mb-3">
          Planned: Confidence Routing Tiers
        </h2>

        <p className="text-gray-400 max-w-lg mx-auto mb-8 leading-relaxed">
          Route transactions through auto-approve, manager, multi-sig, or human review tiers
          based on real-time confidence scoring. Thresholds and approval workflows will be
          fully configurable from this page.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-3xl mx-auto mb-8">
          {[
            { tier: 'Auto-Approve', range: '0.95 - 1.00', approvers: '0 approvers' },
            { tier: 'Manager', range: '0.85 - 0.95', approvers: '1 approver' },
            { tier: 'Multi-Sig', range: '0.70 - 0.85', approvers: '2 approvers' },
            { tier: 'Human Review', range: '0.00 - 0.70', approvers: '3+ approvers' },
          ].map((item) => (
            <div
              key={item.tier}
              className="bg-dark-300 border border-dark-100 p-4 text-left"
            >
              <p className="text-sm font-medium text-white mb-1">{item.tier}</p>
              <p className="text-xs text-gray-500 mb-0.5">Score: {item.range}</p>
              <p className="text-xs text-gray-500">{item.approvers}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
