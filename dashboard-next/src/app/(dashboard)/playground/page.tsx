"use client";

import { useState } from 'react'
import { Play, Terminal, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { RequestEditor } from './components/RequestEditor'
import { ExecutionTrace, type TraceStep } from './components/ExecutionTrace'
import { ResultInspector } from './components/ResultInspector'

export interface EndpointDef {
  id: string
  name: string
  method: 'POST' | 'GET'
  path: string
  description: string
  defaultBody: Record<string, unknown>
}

=======
/* ─── Endpoints ─── */

>>>>>>> 7d0ade61 (feat(api): add notification_configs table (migration 089))
const ENDPOINTS: EndpointDef[] = [
  {
    id: 'pay',
    name: 'sardis.pay()',
    method: 'POST',
    path: '/sandbox/payment',
    description: 'Simulate an agent-to-merchant payment with policy enforcement',
    defaultBody: {
      agent_id: 'agent_demo_001',
      amount: 25.00,
      merchant: 'OpenAI API',
      merchant_category: 'api',
      chain: 'base_sepolia',
      token: 'USDC',
    },
  },
  {
    id: 'policy-check',
    name: '/policy/check',
    method: 'POST',
    path: '/sandbox/policy-check',
<<<<<<< HEAD
    description: "Dry-run a payment against an agent's spending policy",
    defaultBody: {
      agent_id: 'agent_demo_002',
      amount: 150.00,
      merchant: 'AWS Compute',
    },
  },
  {
    id: 'create-wallet',
    name: '/wallets/create',
    method: 'POST',
    path: '/sandbox/create-wallet',
    description: 'Create a demo wallet with simulated testnet funds',
    defaultBody: {
      agent_name: 'Demo Agent',
      initial_balance: 100.00,
      trust_level: 'medium',
    },
  },
  {
    id: 'demo-data',
    name: '/sandbox/demo-data',
    method: 'GET',
    path: '/sandbox/demo-data',
    description: 'Retrieve all pre-seeded demo agents, wallets, and transactions',
    defaultBody: {},
  },
]

type MobileTab = 'editor' | 'trace' | 'result'

export default function PlaygroundPage() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDef>(ENDPOINTS[0])
  const [requestBody, setRequestBody] = useState<string>(JSON.stringify(ENDPOINTS[0].defaultBody, null, 2))
  const [isRunning, setIsRunning] = useState(false)
  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([])
  const [result, setResult] = useState<{ status: number; body: unknown } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mobileTab, setMobileTab] = useState<MobileTab>('editor')
  const [sandboxOnline, setSandboxOnline] = useState<boolean | null>(null)

  useState(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || ''
    fetch(apiBase + '/api/v2/sandbox/demo-data')
      .then((r) => setSandboxOnline(r.ok))
      .catch(() => setSandboxOnline(false))
  })

  function handleEndpointChange(endpoint: EndpointDef) {
    setSelectedEndpoint(endpoint)
    setRequestBody(JSON.stringify(endpoint.defaultBody, null, 2))
    setTraceSteps([])
    setResult(null)
    setError(null)
  }

  async function handleRun() {
    setIsRunning(true)
    setResult(null)
    setError(null)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || ''
    const url = apiBase + '/api/v2' + selectedEndpoint.path
    const steps: TraceStep[] = [
      { id: 'policy', label: 'Policy Check', status: 'pending' },
      { id: 'route', label: 'Route Selection', status: 'pending' },
      { id: 'execute', label: 'Chain Execute', status: 'pending' },
      { id: 'settle', label: 'Settlement', status: 'pending' },
      { id: 'audit', label: 'Audit Log', status: 'pending' },
    ]
    setTraceSteps([...steps])
    setMobileTab('trace')
    try {
      let body: Record<string, unknown> | undefined
      if (selectedEndpoint.method === 'POST') {
        try { body = JSON.parse(requestBody) } catch { setError('Invalid JSON in request body'); setIsRunning(false); return }
      }
      for (let i = 0; i < steps.length; i++) {
        steps[i].status = 'running'
        setTraceSteps([...steps])
        await new Promise((r) => setTimeout(r, 300 + Math.random() * 200))
        if (steps[i].id === 'execute') {
          try {
            const fetchOpts: RequestInit = { method: selectedEndpoint.method, headers: { 'Content-Type': 'application/json' } }
            if (body) fetchOpts.body = JSON.stringify(body)
            const response = await fetch(url, fetchOpts)
            const responseBody = await response.json().catch(() => null)
            if (!response.ok) {
              steps[i].status = 'error'
              steps[i].detail = responseBody?.detail || 'HTTP ' + response.status
              setTraceSteps([...steps])
              for (let j = i + 1; j < steps.length; j++) steps[j].status = 'error'
              setTraceSteps([...steps])
              setResult({ status: response.status, body: responseBody })
              setMobileTab('result')
              setIsRunning(false)
              return
            }
            steps[i].status = 'success'
            steps[i].detail = selectedEndpoint.method + ' ' + selectedEndpoint.path + ' => ' + response.status
            setTraceSteps([...steps])
            setResult({ status: response.status, body: responseBody })
          } catch (fetchErr) {
            steps[i].status = 'error'
            steps[i].detail = fetchErr instanceof Error ? fetchErr.message : 'Network error'
            setTraceSteps([...steps])
            for (let j = i + 1; j < steps.length; j++) steps[j].status = 'error'
            setTraceSteps([...steps])
            setError(fetchErr instanceof Error ? fetchErr.message : 'Network error')
            setIsRunning(false)
            return
          }
          continue
        }
        steps[i].status = 'success'
        setTraceSteps([...steps])
      }
      setMobileTab('result')
    } finally { setIsRunning(false) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">API Playground</h1>
          <p className="text-gray-400 mt-1">Interactive API explorer with execution trace</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <div className={clsx('w-2 h-2 rounded-full', sandboxOnline === true && 'bg-sardis-500 animate-pulse', sandboxOnline === false && 'bg-red-500', sandboxOnline === null && 'bg-gray-500')} />
            <span className="text-sm text-gray-400">{sandboxOnline === true ? 'Sandbox Online' : sandboxOnline === false ? 'Sandbox Offline' : 'Checking...'}</span>
          </div>
        </div>
      </div>
      <div className="flex gap-6">
        <div className="w-64 shrink-0 hidden lg:block space-y-4">
          <div className="card p-4">
            <div className="flex items-center gap-2 mb-4"><Terminal className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Endpoints</h3></div>
            <div className="space-y-1">
              {ENDPOINTS.map((ep) => (
                <button key={ep.id} onClick={() => handleEndpointChange(ep)} className={clsx('w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-all', selectedEndpoint.id === ep.id ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30' : 'text-gray-400 hover:text-white hover:bg-dark-200')}>
                  <span className={clsx('text-[10px] font-mono font-bold px-1.5 py-0.5 shrink-0', ep.method === 'POST' ? 'bg-blue-500/10 text-blue-400' : 'bg-sardis-500/10 text-sardis-400')}>{ep.method}</span>
                  <span className="truncate">{ep.name}</span>
                </button>
              ))}
            </div>
          </div>
          <button onClick={handleRun} disabled={isRunning} className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-sardis-500 text-dark-400 font-semibold hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm">
            {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {isRunning ? 'Running...' : 'Run Request'}
          </button>
          <div className="card p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Description</p>
            <p className="text-sm text-gray-300">{selectedEndpoint.description}</p>
            <div className="mt-3 flex items-center gap-2 text-xs text-gray-500 font-mono">
              <span className={clsx('px-1.5 py-0.5', selectedEndpoint.method === 'POST' ? 'bg-blue-500/10 text-blue-400' : 'bg-sardis-500/10 text-sardis-400')}>{selectedEndpoint.method}</span>
              <span className="text-gray-400">/api/v2{selectedEndpoint.path}</span>
            </div>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="lg:hidden mb-4 space-y-3">
            <select value={selectedEndpoint.id} onChange={(e) => { const ep = ENDPOINTS.find((x) => x.id === e.target.value); if (ep) handleEndpointChange(ep) }} className="w-full px-4 py-2.5 bg-dark-300 border border-dark-100 text-white focus:outline-none focus:border-sardis-500/50">
              {ENDPOINTS.map((ep) => (<option key={ep.id} value={ep.id}>{ep.method} {ep.name}</option>))}
            </select>
            <button onClick={handleRun} disabled={isRunning} className="w-full flex items-center justify-center gap-2 px-5 py-3 bg-sardis-500 text-dark-400 font-semibold hover:bg-sardis-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm">
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isRunning ? 'Running...' : 'Run Request'}
            </button>
          </div>
          <div className="lg:hidden flex border-b border-dark-100 mb-4" data-testid="mobile-tabs">
            {(['editor', 'trace', 'result'] as MobileTab[]).map((tab) => (
              <button key={tab} onClick={() => setMobileTab(tab)} className={clsx('flex-1 py-2.5 text-sm font-medium text-center border-b-2 transition-colors', mobileTab === tab ? 'border-sardis-500 text-sardis-400' : 'border-transparent text-gray-500 hover:text-gray-300')}>
                {tab === 'editor' && 'Editor'}{tab === 'trace' && 'Trace'}{tab === 'result' && 'Result'}
              </button>
            ))}
          </div>
          <div className="hidden lg:grid lg:grid-cols-3 gap-4">
            <RequestEditor endpoint={selectedEndpoint} body={requestBody} onBodyChange={setRequestBody} />
            <ExecutionTrace steps={traceSteps} isRunning={isRunning} />
            <ResultInspector result={result} error={error} endpoint={selectedEndpoint} requestBody={requestBody} />
          </div>
          <div className="lg:hidden">
            {mobileTab === 'editor' && <RequestEditor endpoint={selectedEndpoint} body={requestBody} onBodyChange={setRequestBody} />}
            {mobileTab === 'trace' && <ExecutionTrace steps={traceSteps} isRunning={isRunning} />}
            {mobileTab === 'result' && <ResultInspector result={result} error={error} endpoint={selectedEndpoint} requestBody={requestBody} />}
          </div>
        </div>
      </div>
    </div>
  )
}
