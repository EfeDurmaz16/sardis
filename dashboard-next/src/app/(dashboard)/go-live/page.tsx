"use client";

import { useMemo } from 'react'
import Link from 'next/link'
import { CheckCircle2, Circle, Lock, ArrowRight, Rocket, FlaskConical, Zap, ExternalLink } from 'lucide-react'
import clsx from 'clsx'
import { useAgents, useWebhooks, useBillingAccount, useTransactions } from '@/hooks/useApi'
import { useQuery } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

async function fetchKycStatus(): Promise<{ status: string } | null> {
  try { const res = await fetch(`${API_BASE}/api/v2/kyc/status`, { credentials: 'include' }); if (!res.ok) return null; return res.json() } catch { return null }
}

async function fetchApiKeys(): Promise<{ keys: Array<{ is_active: boolean; last_used_at: string | null }> } | null> {
  try { const res = await fetch(`${API_BASE}/api/v2/auth/api-keys`, { credentials: 'include' }); if (!res.ok) return null; return res.json() } catch { return null }
}

function useKycStatus() { return useQuery({ queryKey: ['kyc-status'], queryFn: fetchKycStatus, retry: false }) }
function useApiKeys() { return useQuery({ queryKey: ['api-keys-live-lane'], queryFn: fetchApiKeys, retry: false }) }

type CheckStatus = 'complete' | 'incomplete' | 'locked' | 'info'
interface ReadinessCheck { id: string; label: string; status: CheckStatus; actionLabel?: string; actionHref?: string; actionExternal?: boolean }
interface Stage { id: string; title: string; icon: React.ReactNode; checks: ReadinessCheck[]; locked: boolean }

function CheckItem({ check }: { check: ReadinessCheck }) {
  const iconEl = useMemo(() => { if (check.status === 'complete') return <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />; if (check.status === 'locked') return <Lock className="w-4 h-4 text-gray-600 flex-shrink-0 mt-0.5" />; if (check.status === 'info') return <Circle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />; return <Circle className="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" /> }, [check.status])
  const labelColor = clsx('text-sm leading-snug', check.status === 'complete' && 'text-white', check.status === 'locked' && 'text-gray-600', check.status === 'info' && 'text-gray-300', check.status === 'incomplete' && 'text-gray-300')
  return (
    <div className="flex items-start gap-3 py-2.5">{iconEl}<div className="flex-1 min-w-0"><span className={labelColor}>{check.label}</span></div>
      {check.actionHref && check.status !== 'complete' && check.status !== 'locked' && (check.actionExternal ? <a href={check.actionHref} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-sardis-400 hover:text-sardis-300 transition-colors flex-shrink-0 ml-2">{check.actionLabel ?? 'Open'}<ExternalLink className="w-3 h-3" /></a> : <Link href={check.actionHref} className="flex items-center gap-1 text-xs text-sardis-400 hover:text-sardis-300 transition-colors flex-shrink-0 ml-2">{check.actionLabel ?? 'Configure'}<ArrowRight className="w-3 h-3" /></Link>)}
    </div>
  )
}

function stageSummary(checks: ReadinessCheck[]): { done: number; total: number; allComplete: boolean } { const total = checks.length; const done = checks.filter(c => c.status === 'complete' || c.status === 'info').length; return { done, total, allComplete: done === total } }

function StageStatusBadge({ checks, locked }: { checks: ReadinessCheck[]; locked: boolean }) {
  if (locked) return <span className="flex items-center gap-1.5 text-xs text-gray-600 border border-gray-700 px-2.5 py-1"><Lock className="w-3 h-3" />Locked</span>;
  const { done, total, allComplete } = stageSummary(checks);
  if (allComplete) return <span className="flex items-center gap-1.5 text-xs text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1"><CheckCircle2 className="w-3 h-3" />Complete</span>;
  return <span className="flex items-center gap-1.5 text-xs text-amber-400 border border-amber-500/30 bg-amber-500/10 px-2.5 py-1"><Zap className="w-3 h-3" />{done} of {total} complete</span>;
}

function StageCard({ stage, index }: { stage: Stage; index: number }) {
  const { allComplete } = stageSummary(stage.checks)
  return (
    <div className={clsx('card overflow-hidden transition-all duration-200', stage.locked && 'opacity-50')}>
      <div className={clsx('flex items-center justify-between px-6 py-4 border-b border-dark-100 border-l-2', stage.locked && 'border-gray-700', !stage.locked && allComplete && 'border-emerald-500', !stage.locked && !allComplete && 'border-amber-500')}>
        <div className="flex items-center gap-3"><div className={clsx('w-8 h-8 flex items-center justify-center text-sm font-bold font-display', stage.locked && 'bg-gray-800 text-gray-600', !stage.locked && allComplete && 'bg-emerald-500/10 text-emerald-400', !stage.locked && !allComplete && 'bg-amber-500/10 text-amber-400')}>{index + 1}</div><div className="flex items-center gap-2"><span className={clsx('w-4 h-4', stage.locked ? 'text-gray-600' : allComplete ? 'text-emerald-400' : 'text-amber-400')}>{stage.icon}</span><h2 className={clsx('text-base font-semibold font-display', stage.locked ? 'text-gray-600' : 'text-white')}>{stage.title}</h2></div></div>
        <StageStatusBadge checks={stage.checks} locked={stage.locked} />
      </div>
      <div className="px-6 divide-y divide-dark-100/60">{stage.checks.map(check => <CheckItem key={check.id} check={check} />)}</div>
    </div>
  )
}

export default function LiveLaneOnboarding() {
  const { data: agents = [] } = useAgents(); const { data: webhooks = [] } = useWebhooks(); const { data: billing } = useBillingAccount(); const { data: transactions = [] } = useTransactions(50); const { data: kycStatus } = useKycStatus(); const { data: apiKeysData } = useApiKeys();
  const hasAgent = (agents as any[]).length > 0; const hasSandboxPayment = (transactions as any[]).length > 0; const hasPolicyConfigured = (agents as any[]).some((a: any) => a.spending_limits != null);
  const apiKeys = apiKeysData?.keys ?? []; const hasApiKey = apiKeys.length > 0; const hasApiCallFromExternal = apiKeys.some(k => k.last_used_at != null); const hasWebhook = (webhooks as any[]).length > 0;
  const kycVerified = kycStatus?.status === 'approved'; const billingActive = billing != null && (billing as any).status === 'active' && (billing as any).plan !== 'free'; const hasProdKey = apiKeys.some(k => k.is_active && k.last_used_at != null);

  const sandboxChecks: ReadinessCheck[] = [{ id: 'account', label: 'Account created', status: 'complete' }, { id: 'agent', label: 'At least 1 agent created', status: hasAgent ? 'complete' : 'incomplete', actionLabel: 'Create agent', actionHref: '/agents' }, { id: 'sandbox-payment', label: 'At least 1 sandbox payment made', status: hasSandboxPayment ? 'complete' : 'incomplete', actionLabel: 'Run demo', actionHref: '/demo' }, { id: 'policy', label: 'Spending policy configured', status: hasPolicyConfigured ? 'complete' : 'incomplete', actionLabel: 'Configure policy', actionHref: '/policy-manager' }]
  const sandboxAllComplete = sandboxChecks.every(c => c.status === 'complete' || c.status === 'info')
  const testIntegrationChecks: ReadinessCheck[] = [{ id: 'api-key', label: 'API key generated', status: hasApiKey ? 'complete' : 'incomplete', actionLabel: 'Generate key', actionHref: '/api-keys' }, { id: 'sdk-installed', label: 'SDK installed (informational)', status: 'info', actionLabel: 'Install guide', actionHref: 'https://sardis.sh/docs/sdk', actionExternal: true }, { id: 'first-api-call', label: 'At least 1 API call from external client', status: hasApiCallFromExternal ? 'complete' : 'incomplete', actionLabel: 'View API docs', actionHref: 'https://sardis.sh/docs/api', actionExternal: true }, { id: 'webhook', label: 'Webhook endpoint configured', status: hasWebhook ? 'complete' : 'incomplete', actionLabel: 'Configure', actionHref: '/webhooks' }]
  const testIntegrationAllComplete = testIntegrationChecks.every(c => c.status === 'complete' || c.status === 'info')
  const controlledLiveLocked = !sandboxAllComplete || !testIntegrationAllComplete
  const controlledLiveChecks: ReadinessCheck[] = [{ id: 'kyc', label: 'KYC identity verified', status: controlledLiveLocked ? 'locked' : kycVerified ? 'complete' : 'incomplete', actionLabel: 'Start KYC', actionHref: '/settings' }, { id: 'billing', label: 'Billing plan active (Starter or above)', status: controlledLiveLocked ? 'locked' : billingActive ? 'complete' : 'incomplete', actionLabel: 'Choose plan', actionHref: '/billing' }, { id: 'prod-key', label: 'Production API key in use', status: controlledLiveLocked ? 'locked' : hasProdKey ? 'complete' : 'incomplete', actionLabel: 'Manage keys', actionHref: '/api-keys' }, { id: 'wallet-funded', label: 'Wallet funded with real USDC', status: controlledLiveLocked ? 'locked' : 'incomplete', actionLabel: 'Fund wallet', actionHref: 'https://sardis.sh/docs/funding', actionExternal: true }, { id: 'emergency-contact', label: 'Emergency contact configured', status: controlledLiveLocked ? 'locked' : 'incomplete', actionLabel: 'Configure', actionHref: '/settings' }]

  const stages: Stage[] = [{ id: 'sandbox', title: 'Sandbox', icon: <FlaskConical className="w-4 h-4" />, checks: sandboxChecks, locked: false }, { id: 'test-integration', title: 'Test Integration', icon: <Zap className="w-4 h-4" />, checks: testIntegrationChecks, locked: !sandboxAllComplete }, { id: 'controlled-live', title: 'Controlled Live', icon: <Rocket className="w-4 h-4" />, checks: controlledLiveChecks, locked: controlledLiveLocked }]

  const allChecks = [...sandboxChecks, ...testIntegrationChecks, ...controlledLiveChecks]; const totalChecks = allChecks.length; const completedChecks = allChecks.filter(c => c.status === 'complete' || c.status === 'info').length; const overallPct = Math.round((completedChecks / totalChecks) * 100)
  const overallLabel = stages[2].checks.every(c => c.status === 'complete' || c.status === 'info') ? 'Live ready' : testIntegrationAllComplete ? 'Almost there' : sandboxAllComplete ? 'Integration in progress' : 'Getting started'

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <div><h1 className="text-3xl font-bold text-white font-display">Go Live</h1><p className="text-gray-400 mt-1">Complete each stage to unlock production access.</p></div>
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3"><span className="text-sm font-medium text-white">Overall readiness</span><div className="flex items-center gap-3"><span className="text-sm text-gray-400">{overallLabel}</span><span className="text-sm font-bold text-sardis-400 mono-numbers">{overallPct}%</span></div></div>
        <div className="h-2 bg-dark-100 overflow-hidden"><div className={clsx('h-full transition-all duration-700', overallPct === 100 ? 'bg-emerald-500' : overallPct >= 50 ? 'bg-amber-500' : 'bg-sardis-500')} style={{ width: `${overallPct}%` }} /></div>
        <div className="flex items-center justify-between mt-2"><span className="text-xs text-gray-500">{completedChecks} of {totalChecks} checks complete</span>{overallPct === 100 && <span className="text-xs text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" />Ready to go live</span>}</div>
      </div>
      <div className="space-y-4">{stages.map((stage, i) => <StageCard key={stage.id} stage={stage} index={i} />)}</div>
      <div className="card p-5 border-sardis-500/20"><div className="flex items-start gap-4"><div className="w-8 h-8 bg-sardis-500/10 flex items-center justify-center flex-shrink-0"><Rocket className="w-4 h-4 text-sardis-400" /></div><div><h3 className="text-sm font-semibold text-white mb-1">Need help going live?</h3><p className="text-sm text-gray-400 mb-3">Our team reviews design-partner applications within 24 hours.</p><div className="flex flex-wrap gap-3"><a href="https://sardis.sh/docs" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-sardis-400 hover:text-sardis-300 border border-sardis-500/30 hover:border-sardis-400 px-3 py-1.5 transition-colors">Documentation<ExternalLink className="w-3 h-3" /></a><Link href="/enterprise-support" className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white border border-dark-100 hover:border-dark-100/80 px-3 py-1.5 transition-colors">Contact support<ArrowRight className="w-3 h-3" /></Link></div></div></div></div>
    </div>
  )
}
