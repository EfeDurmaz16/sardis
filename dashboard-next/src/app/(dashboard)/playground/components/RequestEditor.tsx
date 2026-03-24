"use client";

import { useState } from 'react'
import { FileJson, ToggleLeft, ToggleRight } from 'lucide-react'
import clsx from 'clsx'
import type { EndpointDef } from '../page'

interface RequestEditorProps {
  endpoint: EndpointDef
  body: string
  onBodyChange: (body: string) => void
}

interface FieldDef {
  key: string
  label: string
  type: 'text' | 'number' | 'select'
  options?: string[]
  placeholder?: string
}

const ENDPOINT_FIELDS: Record<string, FieldDef[]> = {
  pay: [
    { key: 'agent_id', label: 'Agent ID', type: 'text', placeholder: 'agent_demo_001' },
    { key: 'amount', label: 'Amount (USD)', type: 'number', placeholder: '25.00' },
    { key: 'merchant', label: 'Merchant', type: 'text', placeholder: 'OpenAI API' },
    { key: 'merchant_category', label: 'Category', type: 'select', options: ['api', 'cloud', 'saas', 'hosting', 'analytics'] },
    { key: 'chain', label: 'Chain', type: 'select', options: ['base_sepolia', 'polygon', 'arbitrum', 'optimism', 'ethereum'] },
    { key: 'token', label: 'Token', type: 'select', options: ['USDC', 'USDT', 'EURC'] },
  ],
  'policy-check': [
    { key: 'agent_id', label: 'Agent ID', type: 'text', placeholder: 'agent_demo_002' },
    { key: 'amount', label: 'Amount (USD)', type: 'number', placeholder: '150.00' },
    { key: 'merchant', label: 'Merchant', type: 'text', placeholder: 'AWS Compute' },
  ],
  'create-wallet': [
    { key: 'agent_name', label: 'Agent Name', type: 'text', placeholder: 'Demo Agent' },
    { key: 'initial_balance', label: 'Balance (USD)', type: 'number', placeholder: '100.00' },
    { key: 'trust_level', label: 'Trust Level', type: 'select', options: ['low', 'medium', 'high'] },
  ],
  'demo-data': [],
}

export function RequestEditor({ endpoint, body, onBodyChange }: RequestEditorProps) {
  const [mode, setMode] = useState<'form' | 'json'>('form')
  const fields = ENDPOINT_FIELDS[endpoint.id] || []

  function getFormValues(): Record<string, unknown> {
    try { return JSON.parse(body) } catch { return {} }
  }

  function updateField(key: string, value: string, type: string) {
    const current = getFormValues()
    current[key] = type === 'number' ? (value ? parseFloat(value) : '') : value
    onBodyChange(JSON.stringify(current, null, 2))
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2"><FileJson className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Request Editor</h3></div>
        {fields.length > 0 && (
          <button onClick={() => setMode(mode === 'form' ? 'json' : 'form')} className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-400 hover:text-white bg-dark-200 border border-dark-100 transition-colors">
            {mode === 'form' ? (<><ToggleLeft className="w-3.5 h-3.5" />JSON</>) : (<><ToggleRight className="w-3.5 h-3.5" />Form</>)}
          </button>
        )}
      </div>
      {endpoint.method === 'GET' && fields.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">GET request — no body required</div>
      ) : mode === 'form' && fields.length > 0 ? (
        <div className="space-y-3">
          {fields.map((field) => {
            const values = getFormValues()
            const value = values[field.key] ?? ''
            return (
              <div key={field.key}>
                <label className="text-xs text-gray-500 uppercase tracking-wider block mb-1">{field.label}</label>
                {field.type === 'select' ? (
                  <select value={String(value)} onChange={(e) => updateField(field.key, e.target.value, 'text')} className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white text-sm focus:outline-none focus:border-sardis-500/50">
                    {field.options?.map((opt) => (<option key={opt} value={opt}>{opt}</option>))}
                  </select>
                ) : (
                  <input type={field.type} value={String(value)} onChange={(e) => updateField(field.key, e.target.value, field.type)} placeholder={field.placeholder} step={field.type === 'number' ? '0.01' : undefined} className="w-full px-3 py-2 bg-dark-300 border border-dark-100 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/50" />
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <textarea value={body} onChange={(e) => onBodyChange(e.target.value)} className="w-full h-64 px-4 py-3 bg-dark-300 border border-dark-100 text-white font-mono text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 resize-none" spellCheck={false} placeholder="Request body (JSON)" />
      )}
    </div>
  )
}
