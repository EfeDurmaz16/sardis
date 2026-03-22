"use client";

import { useEffect, useState, useCallback } from 'react'
import { FileText, FlaskConical, Send, Clock, Loader2, CheckCircle2, XCircle, AlertTriangle, RotateCcw, DollarSign, Tag, ShieldCheck, Eye, Sparkles, Info } from 'lucide-react'
import clsx from 'clsx'
import { usePathname } from 'next/navigation'
import { useAgents, usePolicy, usePolicyHistory, useParsePolicy, useApplyPolicy, usePolicyTestDraft, useWallets } from '@/hooks/useApi'
import { policiesApi, type ActivePolicyRecord, type PolicyHistoryCommit } from '@/api/client'

type TabId = 'author' | 'test' | 'deploy' | 'history'

interface ParsedPolicy { spending_limits?: { per_tx?: number | null; daily?: number | null; weekly?: number | null; monthly?: number | null; total?: number | null }; category_restrictions?: { blocked?: string[]; allowed?: string[] }; time_restrictions?: { window?: string; allowed_hours?: string }; approval_threshold?: number | null; merchant_restrictions?: string[]; warnings?: string[]; [key: string]: unknown }

function fmt(val: number | null | undefined, prefix = '$') { if (val == null) return '\u2014'; return `${prefix}${val.toLocaleString()}` }
function parseCurrencyValue(value: string | null | undefined): number | null { if (value == null || value === '') return null; const parsed = Number(value); return Number.isFinite(parsed) ? parsed : null }

function toParsedPolicy(activePolicy: ActivePolicyRecord): ParsedPolicy {
  return { spending_limits: { per_tx: parseCurrencyValue(activePolicy.limit_per_tx), daily: parseCurrencyValue(activePolicy.daily_limit), weekly: parseCurrencyValue(activePolicy.weekly_limit), monthly: parseCurrencyValue(activePolicy.monthly_limit), total: parseCurrencyValue(activePolicy.limit_total) }, category_restrictions: { blocked: activePolicy.blocked_merchant_categories, allowed: [] }, approval_threshold: parseCurrencyValue(activePolicy.approval_threshold), warnings: activePolicy.require_preauth ? ['Live policy requires pre-authorization before execution.'] : [] }
}

function policyTextFromSnapshot(snapshot: Record<string, unknown>): string {
  const nl = snapshot.natural_language; if (typeof nl === 'string' && nl.trim()) return nl.trim();
  const lines: string[] = []; const perTx = parseCurrencyValue(snapshot.limit_per_tx as string | null); const daily = parseCurrencyValue(snapshot.daily_limit as string | null); const weekly = parseCurrencyValue(snapshot.weekly_limit as string | null); const monthly = parseCurrencyValue(snapshot.monthly_limit as string | null); const total = parseCurrencyValue(snapshot.limit_total as string | null); const at = parseCurrencyValue(snapshot.approval_threshold as string | null); const blocked = Array.isArray(snapshot.blocked_merchant_categories) ? (snapshot.blocked_merchant_categories as unknown[]).filter((x): x is string => typeof x === 'string') : [];
  if (perTx != null) lines.push(`Allow up to $${perTx} per transaction.`); if (daily != null) lines.push(`Cap daily spend at $${daily}.`); if (weekly != null) lines.push(`Cap weekly spend at $${weekly}.`); if (monthly != null) lines.push(`Cap monthly spend at $${monthly}.`); if (total != null) lines.push(`Cap total spend at $${total}.`); if (at != null) lines.push(`Require approval above $${at}.`); if (blocked.length > 0) lines.push(`Block categories: ${blocked.join(', ')}.`);
  return lines.join(' ') || 'Imported policy snapshot from history.'
}

function getInitialTab(): TabId { if (typeof window === 'undefined') return 'author'; const hash = window.location.hash.replace('#', ''); const valid: TabId[] = ['author', 'test', 'deploy', 'history']; return valid.includes(hash as TabId) ? (hash as TabId) : 'author' }

function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'default' | 'success' | 'danger' | 'warn' }) {
  return <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded', variant === 'success' && 'bg-green-500/10 text-green-400 border border-green-500/20', variant === 'danger' && 'bg-red-500/10 text-red-400 border border-red-500/20', variant === 'warn' && 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20', variant === 'default' && 'bg-dark-200 text-gray-400 border border-dark-100')}>{children}</span>
}

function PolicyPreview({ parsed }: { parsed: ParsedPolicy }) {
  const limits = parsed.spending_limits ?? {}; const cats = parsed.category_restrictions ?? {}; const time = parsed.time_restrictions ?? {};
  return (
    <div className="space-y-4">
      <div className="bg-dark-200 border border-dark-100 p-4 space-y-3"><div className="flex items-center gap-2 text-sm font-semibold text-white"><DollarSign className="w-4 h-4 text-sardis-400" />Spending Limits</div><div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">{[{ label: 'Per transaction', val: limits.per_tx }, { label: 'Daily', val: limits.daily }, { label: 'Weekly', val: limits.weekly }, { label: 'Monthly', val: limits.monthly }, { label: 'Total cap', val: limits.total }].map(({ label, val }) => (<div key={label} className="flex justify-between"><span className="text-gray-400">{label}</span><span className={clsx('font-mono', val == null ? 'text-gray-600' : 'text-white')}>{fmt(val)}</span></div>))}{parsed.approval_threshold != null && <div className="flex justify-between col-span-2"><span className="text-gray-400">Requires approval above</span><span className="font-mono text-yellow-400">{fmt(parsed.approval_threshold)}</span></div>}</div></div>
      {(cats.blocked?.length || cats.allowed?.length) ? <div className="bg-dark-200 border border-dark-100 p-4 space-y-2"><div className="flex items-center gap-2 text-sm font-semibold text-white"><Tag className="w-4 h-4 text-sardis-400" />Category Rules</div>{cats.blocked?.length ? <div><p className="text-xs text-gray-500 mb-1.5">Blocked categories</p><div className="flex flex-wrap gap-1.5">{cats.blocked.map(c => <Badge key={c} variant="danger">{c}</Badge>)}</div></div> : null}{cats.allowed?.length ? <div><p className="text-xs text-gray-500 mb-1.5">Allowed only</p><div className="flex flex-wrap gap-1.5">{cats.allowed.map(c => <Badge key={c} variant="success">{c}</Badge>)}</div></div> : null}</div> : null}
      {(time.window || time.allowed_hours) ? <div className="bg-dark-200 border border-dark-100 p-4 space-y-2"><div className="flex items-center gap-2 text-sm font-semibold text-white"><Clock className="w-4 h-4 text-sardis-400" />Time Windows</div>{time.window && <p className="text-sm text-gray-300">{time.window}</p>}{time.allowed_hours && <p className="text-sm text-gray-400 font-mono">{time.allowed_hours}</p>}</div> : null}
      {parsed.warnings?.length ? <div className="bg-yellow-500/5 border border-yellow-500/20 p-3 flex gap-2"><AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" /><ul className="space-y-1">{parsed.warnings.map((w, i) => <li key={i} className="text-sm text-yellow-300">{w}</li>)}</ul></div> : null}
    </div>
  )
}

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'author', label: 'Author', icon: <FileText className="w-4 h-4" /> },
  { id: 'test', label: 'Draft Scenarios', icon: <FlaskConical className="w-4 h-4" /> },
  { id: 'deploy', label: 'Deploy', icon: <Send className="w-4 h-4" /> },
  { id: 'history', label: 'History', icon: <Clock className="w-4 h-4" /> },
]

export default function PolicyManagerPage() {
  const pathname = usePathname()
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab)
  const [draftText, setDraftText] = useState('')
  const [parsedPolicy, setParsedPolicy] = useState<ParsedPolicy | null>(null)
  const parse = useParsePolicy()

  const switchTab = useCallback((id: TabId) => { setActiveTab(id); window.location.hash = id }, [])

  async function handleParse() { if (!draftText.trim()) return; try { const result = await parse.mutateAsync(draftText); setParsedPolicy(result as ParsedPolicy) } catch {} }

  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-bold text-white font-display">Policy Manager</h1><p className="text-gray-400 mt-1">Author, draft-test, deploy, and roll back spending policies through one lifecycle.</p></div>
      <div className="flex items-center gap-3 text-sm">
        <div className={clsx('flex items-center gap-1.5 px-3 py-1.5 border text-xs font-medium', draftText.trim() ? 'bg-sardis-500/10 border-sardis-500/30 text-sardis-400' : 'bg-dark-200 border-dark-100 text-gray-500')}><FileText className="w-3.5 h-3.5" />{draftText.trim() ? `Draft: ${draftText.trim().slice(0, 60)}${draftText.length > 60 ? '\u2026' : ''}` : 'No draft'}</div>
        {parsedPolicy && <Badge variant="success"><CheckCircle2 className="w-3 h-3" />Parsed</Badge>}
      </div>
      <div className="border-b border-dark-100"><nav className="-mb-px flex gap-1">{TABS.map((tab) => (<button key={tab.id} onClick={() => switchTab(tab.id)} className={clsx('flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap', activeTab === tab.id ? 'border-sardis-500 text-sardis-400' : 'border-transparent text-gray-400 hover:text-white hover:border-dark-100')}>{tab.icon}{tab.label}</button>))}</nav></div>
      <div>
        {activeTab === 'author' && (
          <div className="space-y-6">
            <div className="flex items-start gap-2 text-sm text-gray-400 bg-dark-200 border border-dark-100 p-3"><Info className="w-4 h-4 text-sardis-400 flex-shrink-0 mt-0.5" />Write a spending policy in plain English. Sardis will parse it into structured rules that govern agent payments.</div>
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-300">Natural language policy</label>
                <textarea value={draftText} onChange={(e) => { setDraftText(e.target.value); if (parsedPolicy) setParsedPolicy(null) }} placeholder={'E.g. "Allow up to $500 per transaction and $2000 per day. Block gambling and adult content."'} rows={14} className="w-full px-4 py-3 bg-dark-200 border border-dark-100 text-sm text-white placeholder-gray-600 font-mono focus:outline-none focus:border-sardis-500/60 resize-none" />
                <button onClick={handleParse} disabled={!draftText.trim() || parse.isPending} className="flex items-center gap-2 px-5 py-2.5 bg-sardis-500 text-dark-400 text-sm font-semibold hover:bg-sardis-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">{parse.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}{parse.isPending ? 'Parsing\u2026' : 'Parse Policy'}</button>
                {parse.isError && <p className="text-sm text-red-400">{(parse.error as Error)?.message ?? 'Parse failed.'}</p>}
              </div>
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-300">Structured preview</label>
                {parsedPolicy ? <PolicyPreview parsed={parsedPolicy} /> : <div className="h-full min-h-48 bg-dark-200 border border-dashed border-dark-100 flex items-center justify-center"><div className="text-center text-gray-600 space-y-2"><Eye className="w-8 h-8 mx-auto opacity-40" /><p className="text-sm">Parse your policy to see the structured output</p></div></div>}
              </div>
            </div>
          </div>
        )}
        {activeTab === 'test' && <div className="bg-dark-200 border border-dark-100 p-8 text-center text-gray-500"><FlaskConical className="w-8 h-8 mx-auto mb-2 opacity-40" /><p className="text-sm">Write a draft policy in the Author tab, then test scenarios here.</p></div>}
        {activeTab === 'deploy' && <div className="bg-dark-200 border border-dark-100 p-8 text-center text-gray-500"><Send className="w-8 h-8 mx-auto mb-2 opacity-40" /><p className="text-sm">Parse a draft policy, then deploy it to an agent.</p></div>}
        {activeTab === 'history' && <div className="bg-dark-200 border border-dark-100 p-8 text-center text-gray-500"><Clock className="w-8 h-8 mx-auto mb-2 opacity-40" /><p className="text-sm">Select an agent to view real policy history.</p></div>}
      </div>
    </div>
  )
}
