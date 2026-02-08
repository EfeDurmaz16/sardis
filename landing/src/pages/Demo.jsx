import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useSardisDemo } from '@/components/demo/useSardisDemo'
import TerminalView from '@/components/demo/TerminalView'
import DashboardView from '@/components/demo/DashboardView'

const TOUR_STEPS = [
  {
    selector: '[data-tour="controls"]',
    title: 'Run the Demo Scenarios',
    body: 'Start with blocked flow, then run approved flow to demonstrate fail-closed policy enforcement and successful execution.',
  },
  {
    selector: '[data-tour="terminal"]',
    title: 'Protocol + Runtime Logs',
    body: 'Terminal output demonstrates AP2-style mandate checks, policy reason codes, and deterministic system behavior.',
  },
  {
    selector: '[data-tour="dashboard"]',
    title: 'Finance Operator View',
    body: 'Track card impact, policy usage, and transaction outcomes in one operator view.',
  },
]

export default function Demo() {
  const demo = useSardisDemo()
  const [tourIndex, setTourIndex] = useState(-1)
  const [tourRect, setTourRect] = useState(null)
  const [showTerminalMobile, setShowTerminalMobile] = useState(true)
  const [executionMode, setExecutionMode] = useState('simulated')
  const [authState, setAuthState] = useState({
    loading: true,
    authenticated: false,
    liveConfigured: false,
    passwordConfigured: false,
    error: null,
  })
  const [password, setPassword] = useState('')
  const [authBusy, setAuthBusy] = useState(false)

  const tourStep = tourIndex >= 0 ? TOUR_STEPS[tourIndex] : null
  const liveUnlocked = authState.authenticated && authState.liveConfigured

  const refreshAuth = useCallback(async () => {
    try {
      const response = await fetch('/api/demo-auth')
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data?.error || `auth_status_http_${response.status}`)
      }
      setAuthState({
        loading: false,
        authenticated: Boolean(data.authenticated),
        liveConfigured: Boolean(data.liveConfigured),
        passwordConfigured: Boolean(data.passwordConfigured),
        error: null,
      })
    } catch (error) {
      const raw = String(error?.message || 'auth_status_failed')
      const friendly =
        raw.includes('expected pattern')
          ? 'Demo API route is unreachable. Run under Vercel/serverless runtime.'
          : raw
      setAuthState((prev) => ({
        ...prev,
        loading: false,
        error: friendly,
      }))
    }
  }, [])

  useEffect(() => {
    void refreshAuth()
  }, [refreshAuth])

  useEffect(() => {
    if (tourIndex < 0) return undefined
    const updateRect = () => {
      const step = TOUR_STEPS[tourIndex]
      const element = document.querySelector(step.selector)
      if (!element) {
        setTourRect(null)
        return
      }
      setTourRect(element.getBoundingClientRect())
    }
    updateRect()
    window.addEventListener('resize', updateRect)
    window.addEventListener('scroll', updateRect, true)
    return () => {
      window.removeEventListener('resize', updateRect)
      window.removeEventListener('scroll', updateRect, true)
    }
  }, [tourIndex])

  const tooltipStyle = useMemo(() => {
    if (!tourRect) {
      return {
        top: '22%',
        left: '50%',
        transform: 'translateX(-50%)',
      }
    }
    const top = Math.min(tourRect.bottom + 14, window.innerHeight - 240)
    const left = Math.min(Math.max(tourRect.left, 16), window.innerWidth - 380)
    return { top: `${top}px`, left: `${left}px` }
  }, [tourRect])

  const runBlocked = useCallback(() => {
    if (executionMode === 'live') {
      if (!liveUnlocked) return
      void demo.runLiveDemo('blocked')
      return
    }
    demo.runBlockedDemo()
  }, [demo, executionMode, liveUnlocked])

  const runApproved = useCallback(() => {
    if (executionMode === 'live') {
      if (!liveUnlocked) return
      void demo.runLiveDemo('approved')
      return
    }
    demo.runApprovedDemo()
  }, [demo, executionMode, liveUnlocked])

  const runNarrative = () => {
    demo.reset()
    if (executionMode === 'live') {
      if (!liveUnlocked) return
      void demo.runLiveDemo('blocked')
      window.setTimeout(() => {
        void demo.runLiveDemo('approved')
        window.setTimeout(() => {
          demo.topUpCard(50)
        }, 1800)
      }, 9000)
      return
    }
    demo.runBlockedDemo()
    window.setTimeout(() => {
      demo.runApprovedDemo()
      window.setTimeout(() => {
        demo.topUpCard(50)
      }, 1800)
    }, 9000)
  }

  const loginOperator = async () => {
    setAuthBusy(true)
    try {
      const response = await fetch('/api/demo-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.error || 'auth_failed')
      }
      setPassword('')
      await refreshAuth()
    } catch (error) {
      setAuthState((prev) => ({
        ...prev,
        error: String(error?.message || 'auth_failed'),
      }))
    } finally {
      setAuthBusy(false)
    }
  }

  const logoutOperator = async () => {
    setAuthBusy(true)
    try {
      await fetch('/api/demo-auth', { method: 'DELETE' })
      await refreshAuth()
    } finally {
      setAuthBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border bg-background/95 px-4 py-3 backdrop-blur lg:px-8">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between">
          <Link to="/" className="font-mono text-sm font-semibold text-foreground transition-colors hover:text-[var(--sardis-orange)]">
            ← sardis.sh
          </Link>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setTourIndex(0)}
              className="border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest text-foreground hover:border-[var(--sardis-orange)]"
            >
              Start guided tour
            </button>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              /demo live walkthrough
            </span>
            <span className="block h-1.5 w-1.5 bg-emerald-400" />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-6 lg:px-8">
        <section className="space-y-5">
          <motion.div
            data-tour="controls"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="border border-border bg-card p-4"
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h1 className="text-xl text-foreground" style={{ fontFamily: 'var(--font-display)' }}>
                  Sardis End-to-End Demo
                </h1>
                <p className="font-mono text-xs text-muted-foreground">Flow with blocked + approved scenarios</p>
              </div>
              <span className="border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-foreground">
                Scenario: {demo.scenario}
              </span>
            </div>

            <div className="mb-3 flex flex-wrap items-center gap-2">
              <button
                onClick={() => setExecutionMode('simulated')}
                className={`border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest ${
                  executionMode === 'simulated'
                    ? 'border-[var(--sardis-orange)] bg-[var(--sardis-orange)] text-[var(--sardis-ink)]'
                    : 'border-border text-muted-foreground'
                }`}
              >
                Simulated (Public)
              </button>
              <button
                onClick={() => setExecutionMode('live')}
                className={`border px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest ${
                  executionMode === 'live'
                    ? 'border-[var(--sardis-orange)] bg-[var(--sardis-orange)] text-[var(--sardis-ink)]'
                    : 'border-border text-muted-foreground'
                }`}
              >
                Live (Private)
              </button>
              <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {executionMode === 'live' ? (liveUnlocked ? 'Live unlocked' : 'Live locked') : 'No API keys exposed'}
              </span>
            </div>

            {executionMode === 'live' && (
              <div className="mb-3 border border-border p-3">
                {authState.loading ? (
                  <p className="font-mono text-xs text-muted-foreground">Loading operator auth status...</p>
                ) : !authState.passwordConfigured ? (
                  <div className="space-y-2">
                    <p className="font-mono text-xs text-red-600">
                      Set <code>DEMO_OPERATOR_PASSWORD</code> on the server to enable private live mode.
                    </p>
                    <p className="font-mono text-xs text-muted-foreground">
                      Example:
                      {' '}
                      <code>export DEMO_OPERATOR_PASSWORD=&quot;&lt;shared-password&gt;&quot;</code>
                    </p>
                  </div>
                ) : authState.authenticated ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-emerald-600">Operator session active</span>
                    <button
                      onClick={logoutOperator}
                      disabled={authBusy}
                      className="border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-widest"
                    >
                      Logout
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {!authState.liveConfigured && (
                      <p className="font-mono text-xs text-red-600">Set `SARDIS_API_URL` + `SARDIS_API_KEY` to enable live calls.</p>
                    )}
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Operator password"
                        className="border border-border bg-background px-2 py-1.5 font-mono text-xs"
                      />
                      <button
                        onClick={loginOperator}
                        disabled={authBusy || !password}
                        className="border border-[var(--sardis-orange)] px-2 py-1.5 font-mono text-[10px] uppercase tracking-widest text-[var(--sardis-orange)] disabled:opacity-50"
                      >
                        Unlock live mode
                      </button>
                    </div>
                  </div>
                )}
                {authState.error && (
                  <p className="mt-2 font-mono text-xs text-red-600">{authState.error}</p>
                )}
              </div>
            )}

            {demo.liveStatus.lastError && (
              <div className="mb-3 border border-red-500 bg-red-50 p-3">
                <p className="font-mono text-xs text-red-700">Live mode error: {demo.liveStatus.lastError}</p>
                {demo.liveStatus.fallbackRecommended && (
                  <button
                    onClick={() => setExecutionMode('simulated')}
                    className="mt-2 border border-red-600 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-red-700"
                  >
                    Switch to simulated fallback
                  </button>
                )}
              </div>
            )}

            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
              <button
                onClick={runBlocked}
                disabled={demo.isRunning || (executionMode === 'live' && !liveUnlocked)}
                className="border border-red-600 px-3 py-2 font-mono text-xs text-red-700 transition hover:bg-red-600 hover:text-white disabled:opacity-60"
              >
                Run blocked path
              </button>
              <button
                onClick={runApproved}
                disabled={demo.isRunning || (executionMode === 'live' && !liveUnlocked)}
                className="border border-emerald-600 px-3 py-2 font-mono text-xs text-emerald-700 transition hover:bg-emerald-600 hover:text-white disabled:opacity-60"
              >
                Run approved path
              </button>
              <button
                onClick={runNarrative}
                disabled={demo.isRunning || (executionMode === 'live' && !liveUnlocked)}
                className="border border-[var(--sardis-orange)] px-3 py-2 font-mono text-xs text-[var(--sardis-orange)] transition hover:bg-[var(--sardis-orange)] hover:text-[var(--sardis-ink)] disabled:opacity-60"
              >
                Run full narrative
              </button>
              <button
                onClick={() => demo.runRecordMode(executionMode)}
                disabled={demo.isRunning || (executionMode === 'live' && !liveUnlocked)}
                className="border border-border px-3 py-2 font-mono text-xs text-foreground transition hover:border-[var(--sardis-orange)] disabled:opacity-60"
              >
                Record mode
              </button>
              <button
                onClick={demo.reset}
                className="border border-border px-3 py-2 font-mono text-xs text-foreground transition hover:border-[var(--sardis-orange)]"
              >
                Reset
              </button>
              <button
                onClick={demo.clearHistory}
                className="border border-border px-3 py-2 font-mono text-xs text-foreground transition hover:border-[var(--sardis-orange)]"
              >
                Clear history
              </button>
            </div>
          </motion.div>

          <div className="grid gap-4 lg:hidden">
            <div className="flex border border-border">
              <button
                onClick={() => setShowTerminalMobile(true)}
                className={`flex-1 px-3 py-2 font-mono text-xs uppercase tracking-widest ${showTerminalMobile ? 'bg-[var(--sardis-orange)] text-[var(--sardis-ink)]' : 'text-muted-foreground'}`}
              >
                Terminal
              </button>
              <button
                onClick={() => setShowTerminalMobile(false)}
                className={`flex-1 border-l border-border px-3 py-2 font-mono text-xs uppercase tracking-widest ${!showTerminalMobile ? 'bg-[var(--sardis-orange)] text-[var(--sardis-ink)]' : 'text-muted-foreground'}`}
              >
                Dashboard
              </button>
            </div>
            {showTerminalMobile ? (
              <div data-tour="terminal" className="h-[500px] overflow-hidden border border-border bg-card">
                <TerminalView logs={demo.logs} state={demo.state} />
              </div>
            ) : (
              <div data-tour="dashboard" className="h-[680px] overflow-hidden border border-border bg-card">
                <DashboardView
                  state={demo.state}
                  transaction={demo.transaction}
                  cardBalance={demo.cardBalance}
                  walletBalance={demo.walletBalance}
                  cardStatus={demo.cardStatus}
                  blockedAttempt={demo.blockedAttempt}
                  fundingEvent={demo.fundingEvent}
                  policyUsed={demo.policyUsed}
                  history={demo.history}
                  isRunning={demo.isRunning}
                  onTopUp={demo.topUpCard}
                  onStart={runApproved}
                  onReset={demo.reset}
                />
              </div>
            )}
          </div>

          <div className="hidden gap-4 lg:grid lg:grid-cols-[1fr_1.2fr]">
            <motion.div
              data-tour="terminal"
              className="h-[760px] overflow-hidden border border-border bg-card"
              initial={{ opacity: 0, x: -14 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <TerminalView logs={demo.logs} state={demo.state} />
            </motion.div>
            <motion.div
              data-tour="dashboard"
              className="h-[760px] overflow-hidden border border-border bg-card"
              initial={{ opacity: 0, x: 14 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <DashboardView
                state={demo.state}
                transaction={demo.transaction}
                cardBalance={demo.cardBalance}
                walletBalance={demo.walletBalance}
                cardStatus={demo.cardStatus}
                blockedAttempt={demo.blockedAttempt}
                fundingEvent={demo.fundingEvent}
                policyUsed={demo.policyUsed}
                history={demo.history}
                isRunning={demo.isRunning}
                onTopUp={demo.topUpCard}
                onStart={runApproved}
                onReset={demo.reset}
              />
            </motion.div>
          </div>
        </section>
      </main>

      {tourStep && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/55" />
          {tourRect && (
            <div
              className="pointer-events-none fixed border-2 border-[var(--sardis-orange)]"
              style={{
                top: `${tourRect.top - 6}px`,
                left: `${tourRect.left - 6}px`,
                width: `${tourRect.width + 12}px`,
                height: `${tourRect.height + 12}px`,
                boxShadow: '0 0 0 9999px rgba(0,0,0,0.55)',
              }}
            />
          )}
          <div
            className="fixed w-[min(360px,calc(100vw-24px))] border border-[var(--sardis-orange)] bg-background p-4"
            style={tooltipStyle}
          >
            <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-[var(--sardis-orange)]">
              Guided Tour {tourIndex + 1}/{TOUR_STEPS.length}
            </div>
            <h3 className="mb-2 text-sm text-foreground" style={{ fontFamily: 'var(--font-display)' }}>
              {tourStep.title}
            </h3>
            <p className="mb-3 font-mono text-xs text-muted-foreground">{tourStep.body}</p>
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={() => setTourIndex((prev) => Math.max(0, prev - 1))}
                disabled={tourIndex === 0}
                className="border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-widest disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onClick={() => setTourIndex(-1)}
                className="border border-border px-2 py-1 font-mono text-[10px] uppercase tracking-widest"
              >
                Close
              </button>
              <button
                onClick={() => setTourIndex((prev) => (prev >= TOUR_STEPS.length - 1 ? -1 : prev + 1))}
                className="border border-[var(--sardis-orange)] bg-[var(--sardis-orange)] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-[var(--sardis-ink)]"
              >
                {tourIndex >= TOUR_STEPS.length - 1 ? 'Finish' : 'Next'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
