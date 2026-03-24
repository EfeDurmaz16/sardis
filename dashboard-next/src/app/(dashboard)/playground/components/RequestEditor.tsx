"use client";
import { FileJson } from 'lucide-react'
import type { EndpointDef } from '../page'
interface RequestEditorProps { endpoint: EndpointDef; body: string; onBodyChange: (body: string) => void }
export function RequestEditor({ endpoint, body, onBodyChange }: RequestEditorProps) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3"><FileJson className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Request Editor</h3></div>
      <textarea value={body} onChange={(e) => onBodyChange(e.target.value)} className="w-full h-64 px-4 py-3 bg-dark-300 border border-dark-100 text-white font-mono text-sm placeholder-gray-600 focus:outline-none focus:border-sardis-500/50 resize-none" spellCheck={false} placeholder="Request body (JSON)" />
    </div>
  )
}
