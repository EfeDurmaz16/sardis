import { useEffect, useMemo, useState } from 'react'

const CANONICAL_DASHBOARD_URL = 'https://app.sardis.sh'
const REDIRECT_DELAY_SECONDS = 6

const DASHBOARD_ROUTE_MAP: Record<string, string> = {
  '/': '/',
  '/agents': '/agents',
  '/cards': '/virtual-cards',
  '/analytics': '/analytics',
  '/reconciliation': '/reconciliation',
  '/policies': '/policy-manager',
  '/approvals': '/approvals',
  '/events': '/live-events',
  '/guardrails': '/guardrails',
  '/enterprise-support': '/support',
  '/stripe-issuing': '/virtual-cards',
  '/kill-switch': '/kill-switch',
  '/evidence': '/evidence',
  '/policy-management': '/policy-manager',
  '/merchants': '/merchants',
  '/simulation': '/simulation',
  '/anomaly': '/anomaly-detection',
  '/billing': '/billing',
  '/api-keys': '/api-keys',
  '/webhooks': '/webhooks',
  '/settings': '/settings',
  '/go-live': '/go-live',
  '/control-center': '/control-center',
  '/templates': '/workflows',
  '/counterparties': '/counterparties',
  '/approval-config': '/approval-config',
  '/provider-health': '/provider-health',
  '/checkout-controls': '/checkout-controls',
  '/fallback-rules': '/fallback-rules',
  '/environment-templates': '/environments',
  '/agent-observability': '/observability',
  '/transactions': '/transactions',
  '/mandates': '/mandates',
  '/mpp-sessions': '/mpp-sessions',
}

function resolveDashboardTarget(location: Window['location']) {
  const normalizedPath = location.pathname.replace(/\/+$/, '') || '/'
  const mappedPath = DASHBOARD_ROUTE_MAP[normalizedPath] || '/'
  return `${CANONICAL_DASHBOARD_URL}${mappedPath}${location.search}${location.hash}`
}

function App() {
  const targetUrl = useMemo(() => resolveDashboardTarget(window.location), [])
  const [secondsRemaining, setSecondsRemaining] = useState(REDIRECT_DELAY_SECONDS)

  useEffect(() => {
    document.title = 'Sardis Legacy Dashboard Deprecated'

    const countdown = window.setInterval(() => {
      setSecondsRemaining((current) => {
        if (current <= 1) {
          window.clearInterval(countdown)
          return 0
        }
        return current - 1
      })
    }, 1000)

    const redirect = window.setTimeout(() => {
      window.location.replace(targetUrl)
    }, REDIRECT_DELAY_SECONDS * 1000)

    return () => {
      window.clearInterval(countdown)
      window.clearTimeout(redirect)
    }
  }, [targetUrl])

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
          Legacy Surface Deprecated
        </p>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          This dashboard has moved to the canonical Next.js app.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          This Vite dashboard remains only as a compatibility shell. Continue in the canonical dashboard at
          {' '}
          <a className="underline underline-offset-4" href={CANONICAL_DASHBOARD_URL}>
            app.sardis.sh
          </a>
          .
        </p>

        <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/30">
          <p className="text-sm font-medium text-slate-100">Redirect target</p>
          <p className="mt-2 break-all text-sm text-slate-400">{targetUrl}</p>
          <p className="mt-4 text-sm text-slate-400">
            Automatic redirect in {secondsRemaining}s.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a
              className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-medium text-slate-950"
              href={targetUrl}
            >
              Continue to canonical dashboard
            </a>
            <a
              className="inline-flex items-center justify-center rounded-full border border-slate-700 px-5 py-3 text-sm font-medium text-slate-100"
              href={CANONICAL_DASHBOARD_URL}
            >
              Open dashboard home
            </a>
          </div>
        </div>

        <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-950/60 p-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
            Developer Note
          </h2>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            New app work should move to
            {' '}
            <code>apps/dashboard</code>
            {' '}
            instead of this directory. Marketing and public entry flows now live in
            {' '}
            <code>apps/landing</code>
            .
          </p>
        </section>
      </div>
    </main>
  )
}

export default App
