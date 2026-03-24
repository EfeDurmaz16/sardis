"use client";

import { useState } from 'react'
import { Code2, Copy, Check } from 'lucide-react'
import clsx from 'clsx'
import type { EndpointDef } from '../page'

interface ResultInspectorProps {
  result: { status: number; body: unknown } | null
  error: string | null
  endpoint: EndpointDef
  requestBody: string
}

type CodeTab = 'python' | 'typescript'

function statusColor(status: number): string {
  if (status >= 200 && status < 300) return 'bg-sardis-500/10 text-sardis-400 border-sardis-500/30'
  if (status >= 400 && status < 500) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
  return 'bg-red-500/10 text-red-400 border-red-500/30'
}

function generatePythonSnippet(endpoint: EndpointDef, body: string): string {
  if (endpoint.method === 'GET') {
    return 'import sardis\n\nclient = sardis.Client(api_key="sk_sandbox_...")\nresult = client.sandbox.demo_data()\nprint(result)'
  }
  let parsed: Record<string, unknown> = {}
  try { parsed = JSON.parse(body) } catch { /* */ }
  if (endpoint.id === 'pay') {
    return 'import sardis\n\nclient = sardis.Client(api_key="sk_sandbox_...")\nresult = client.pay(\n    agent_id="' + (parsed.agent_id || 'agent_demo_001') + '",\n    amount=' + (parsed.amount || 25) + ',\n    merchant="' + (parsed.merchant || 'OpenAI API') + '",\n    chain="' + (parsed.chain || 'base_sepolia') + '",\n)\nprint(result)'
  }
  if (endpoint.id === 'policy-check') {
    return 'import sardis\n\nclient = sardis.Client(api_key="sk_sandbox_...")\nresult = client.policy.check(\n    agent_id="' + (parsed.agent_id || 'agent_demo_002') + '",\n    amount=' + (parsed.amount || 150) + ',\n    merchant="' + (parsed.merchant || 'AWS Compute') + '",\n)\nprint(result)'
  }
  return 'import sardis\n\nclient = sardis.Client(api_key="sk_sandbox_...")\nresult = client.sandbox.create_wallet(\n    agent_name="' + (parsed.agent_name || 'Demo Agent') + '",\n    initial_balance=' + (parsed.initial_balance || 100) + ',\n)\nprint(result)'
}

function generateTSSnippet(endpoint: EndpointDef, body: string): string {
  if (endpoint.method === 'GET') {
    return 'import Sardis from "@sardis/sdk";\n\nconst client = new Sardis({ apiKey: "sk_sandbox_..." });\nconst result = await client.sandbox.demoData();\nconsole.log(result);'
  }
  let parsed: Record<string, unknown> = {}
  try { parsed = JSON.parse(body) } catch { /* */ }
  if (endpoint.id === 'pay') {
    return 'import Sardis from "@sardis/sdk";\n\nconst client = new Sardis({ apiKey: "sk_sandbox_..." });\nconst result = await client.pay({\n  agentId: "' + (parsed.agent_id || 'agent_demo_001') + '",\n  amount: ' + (parsed.amount || 25) + ',\n  merchant: "' + (parsed.merchant || 'OpenAI API') + '",\n  chain: "' + (parsed.chain || 'base_sepolia') + '",\n});\nconsole.log(result);'
  }
  if (endpoint.id === 'policy-check') {
    return 'import Sardis from "@sardis/sdk";\n\nconst client = new Sardis({ apiKey: "sk_sandbox_..." });\nconst result = await client.policy.check({\n  agentId: "' + (parsed.agent_id || 'agent_demo_002') + '",\n  amount: ' + (parsed.amount || 150) + ',\n  merchant: "' + (parsed.merchant || 'AWS Compute') + '",\n});\nconsole.log(result);'
  }
  return 'import Sardis from "@sardis/sdk";\n\nconst client = new Sardis({ apiKey: "sk_sandbox_..." });\nconst result = await client.sandbox.createWallet({\n  agentName: "' + (parsed.agent_name || 'Demo Agent') + '",\n  initialBalance: ' + (parsed.initial_balance || 100) + ',\n});\nconsole.log(result);'
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
  }
  return (
    <button onClick={handleCopy} className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-white bg-dark-200 border border-dark-100 transition-colors">
      {copied ? <Check className="w-3 h-3 text-sardis-400" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export function ResultInspector({ result, error, endpoint, requestBody }: ResultInspectorProps) {
  const [codeTab, setCodeTab] = useState<CodeTab>('python')

  const snippet = codeTab === 'python'
    ? generatePythonSnippet(endpoint, requestBody)
    : generateTSSnippet(endpoint, requestBody)

  return (
    <div className="card p-4 space-y-4">
      <div className="flex items-center gap-2 mb-0">
        <Code2 className="w-4 h-4 text-sardis-400" />
        <h3 className="text-sm font-semibold text-white">Result Inspector</h3>
      </div>

      {!result && !error ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500 text-sm gap-2">
          <Code2 className="w-8 h-8 text-gray-600" />
          <p>Run a request to see the response</p>
        </div>
      ) : error ? (
        <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
      ) : result && (
        <>
          <div className="flex items-center justify-between">
            <span className={clsx('inline-flex items-center px-2 py-0.5 text-xs font-medium border', statusColor(result.status))}>
              {result.status}
            </span>
            <CopyButton text={JSON.stringify(result.body, null, 2)} />
          </div>
          <pre className="text-xs text-gray-300 font-mono overflow-auto max-h-48 p-3 bg-dark-300 border border-dark-100">
            {JSON.stringify(result.body, null, 2)}
          </pre>
        </>
      )}

      {/* Code snippet */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-500 uppercase tracking-wider">SDK Equivalent</p>
          <div className="flex">
            {(['python', 'typescript'] as CodeTab[]).map((tab) => (
              <button key={tab} onClick={() => setCodeTab(tab)} className={clsx('px-2.5 py-1 text-xs font-medium transition-colors', codeTab === tab ? 'bg-dark-200 text-white border border-dark-100' : 'text-gray-500 hover:text-gray-300')}>
                {tab === 'python' ? 'Python' : 'TypeScript'}
              </button>
            ))}
          </div>
        </div>
        <div className="relative">
          <pre className="text-xs text-gray-400 font-mono overflow-auto max-h-40 p-3 bg-dark-300 border border-dark-100">
            {snippet}
          </pre>
          <div className="absolute top-2 right-2"><CopyButton text={snippet} /></div>
        </div>
      </div>
    </div>
  )
}
