"use client";
import { Activity } from 'lucide-react'
export interface TraceStep { id: string; label: string; status: 'pending' | 'running' | 'success' | 'error'; detail?: string }
interface ExecutionTraceProps { steps: TraceStep[]; isRunning: boolean }
export function ExecutionTrace({ steps }: ExecutionTraceProps) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3"><Activity className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Execution Trace</h3></div>
      {steps.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Click &quot;Run Request&quot; to see the execution trace</div>
      ) : (
        <div className="space-y-2">{steps.map((step) => (<div key={step.id} className="text-sm text-gray-400">{step.label}: {step.status}</div>))}</div>
      )}
    </div>
  )
}
