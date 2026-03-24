"use client";
import { Code2 } from 'lucide-react'
import type { EndpointDef } from '../page'
interface ResultInspectorProps { result: { status: number; body: unknown } | null; error: string | null; endpoint: EndpointDef; requestBody: string }
export function ResultInspector({ result, error }: ResultInspectorProps) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3"><Code2 className="w-4 h-4 text-sardis-400" /><h3 className="text-sm font-semibold text-white">Result Inspector</h3></div>
      {!result && !error ? (
        <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Run a request to see the response</div>
      ) : error ? (
        <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
      ) : (
        <pre className="text-xs text-gray-300 font-mono overflow-auto max-h-64 p-3 bg-dark-300 border border-dark-100">{JSON.stringify(result?.body, null, 2)}</pre>
      )}
    </div>
  )
}
