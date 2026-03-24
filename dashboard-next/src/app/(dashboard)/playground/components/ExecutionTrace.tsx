"use client";

import { useState } from 'react'
import { Activity, CheckCircle2, XCircle, Loader2, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

export interface TraceStep {
  id: string
  label: string
  status: 'pending' | 'running' | 'success' | 'error'
  detail?: string
}

interface ExecutionTraceProps {
  steps: TraceStep[]
  isRunning: boolean
}

function StepIcon({ status }: { status: TraceStep['status'] }) {
  switch (status) {
    case 'pending': return <Clock className="w-4 h-4 text-gray-600" />
    case 'running': return <Loader2 className="w-4 h-4 text-sardis-400 animate-spin" />
    case 'success': return <CheckCircle2 className="w-4 h-4 text-sardis-400" />
    case 'error': return <XCircle className="w-4 h-4 text-red-400" />
  }
}

function StepRow({ step }: { step: TraceStep }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetail = Boolean(step.detail)

  return (
    <div className={clsx(
      'border transition-colors',
      step.status === 'running' && 'border-sardis-500/30 bg-sardis-500/5',
      step.status === 'success' && 'border-dark-100 bg-dark-300/50',
      step.status === 'error' && 'border-red-500/30 bg-red-500/5',
      step.status === 'pending' && 'border-dark-100 bg-dark-300/30 opacity-50',
    )}>
      <button
        onClick={() => hasDetail && setExpanded(!expanded)}
        className={clsx('w-full flex items-center gap-3 px-3 py-2.5 text-left', hasDetail && 'cursor-pointer')}
        disabled={!hasDetail}
      >
        <StepIcon status={step.status} />
        <span className={clsx('text-sm font-medium flex-1', step.status === 'error' ? 'text-red-400' : step.status === 'pending' ? 'text-gray-600' : 'text-white')}>
          {step.label}
        </span>
        {hasDetail && (
          expanded ? <ChevronDown className="w-3.5 h-3.5 text-gray-500" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>
      {expanded && step.detail && (
        <div className="px-3 pb-2.5 pl-10">
          <p className="text-xs text-gray-400 font-mono">{step.detail}</p>
        </div>
      )}
    </div>
  )
}

export function ExecutionTrace({ steps, isRunning }: ExecutionTraceProps) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2"><Activity className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Execution Trace</h3></div>
        {isRunning && <span className="text-xs text-sardis-400 animate-pulse">Executing...</span>}
      </div>
      {steps.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500 text-sm gap-2">
          <Activity className="w-8 h-8 text-gray-600" />
          <p>Click &quot;Run Request&quot; to see the execution trace</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {steps.map((step) => (<StepRow key={step.id} step={step} />))}
        </div>
      )}
    </div>
  )
}
