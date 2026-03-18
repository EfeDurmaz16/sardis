import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSardisDemo } from '@/components/demo/useSardisDemo'
import TerminalView from '@/components/demo/TerminalView'
import SEO from '@/components/SEO'

export default function Demo() {
  const demo = useSardisDemo()
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

  const liveUnlocked = authState.authenticated && authState.liveConfigured

  const refreshAuth = useCallback(async () => {
    try {
      const response = await fetch('/api/demo-auth')
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data?.error || `auth_status_http_${response.status}`)
      setAuthState({
        loading: false,
        authenticated: Boolean(data.authenticated),
        liveConfigured: Boolean(data.liveConfigured),
        passwordConfigured: Boolean(data.passwordConfigured),
        error: null,
      })
    } catch (error) {
      setAuthState((prev) => ({ ...prev, loading: false, error: String(error?.message || 'auth_failed') }))
    }
  }, [])

  useEffect(() => { void refreshAuth() }, [refreshAuth])

  const loginOperator = async () => {
    setAuthBusy(true)
    try {
      const response = await fetch('/api/demo-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data?.error || 'auth_failed')
      setPassword('')
      await refreshAuth()
    } catch (error) {
      setAuthState((prev) => ({ ...prev, error: String(error?.message || 'auth_failed') }))
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

  const runScenario = useCallback((scenario) => {
    if (executionMode === 'live') {
      if (!liveUnlocked) return
      void demo.runLiveDemo(scenario)
    } else {
      demo.runDemo(scenario)
    }
  }, [demo, executionMode, liveUnlocked])

  const isLive = executionMode === 'live' && liveUnlocked
  const canRun = !demo.isRunning && (executionMode !== 'live' || liveUnlocked)

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: '#0a0a0b', color: '#e5e5e5' }}>
      <SEO
        title="Agent Payment Demo"
        description="Interactive Sardis demo: live AI agent payment flows with policy enforcement on Base Sepolia testnet."
        path="/demo"
        noindex
      />

      {/* ── TOP BAR ── */}
      <header className="flex items-center justify-between border-b px-4 py-2" style={{ borderColor: '#1a1a1e', background: '#0d0d0f' }}>
        <div className="flex items-center gap-4">
          <Link to="/" className="text-xs opacity-50 hover:opacity-100 transition-opacity" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            ← sardis.sh
          </Link>
          <div className="h-3 w-px" style={{ background: '#1a1a1e' }} />
          <span className="text-[11px] font-semibold tracking-[0.15em] uppercase" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#808080' }}>
            Agent Payment Demo
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Mode Toggle */}
          <div className="flex" style={{ border: '1px solid #1a1a1e' }}>
            <button
              onClick={() => setExecutionMode('simulated')}
              className="px-3 py-1 text-[10px] uppercase tracking-wider transition-colors"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                background: executionMode === 'simulated' ? '#1a1a1e' : 'transparent',
                color: executionMode === 'simulated' ? '#e5e5e5' : '#555',
              }}
            >
              Simulated
            </button>
            <button
              onClick={() => setExecutionMode('live')}
              className="px-3 py-1 text-[10px] uppercase tracking-wider transition-colors"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                background: executionMode === 'live' ? (liveUnlocked ? '#0a2e1a' : '#1a1a1e') : 'transparent',
                color: executionMode === 'live' ? (liveUnlocked ? '#34d399' : '#e5e5e5') : '#555',
              }}
            >
              Live Testnet
            </button>
          </div>

          {/* Live Status Indicator */}
          {isLive && (
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: '#34d399' }} />
              <span className="text-[10px] uppercase tracking-wider" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#34d399' }}>
                Connected
              </span>
            </div>
          )}

          {/* Reset */}
          <button
            onClick={demo.reset}
            className="px-2 py-1 text-[10px] uppercase tracking-wider opacity-40 hover:opacity-100 transition-opacity"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            Reset
          </button>
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      <div className="flex-1 grid grid-cols-[240px_1fr_280px] gap-0 overflow-hidden">

        {/* ── LEFT PANEL: Controls + Network ── */}
        <div className="flex flex-col border-r overflow-y-auto" style={{ borderColor: '#1a1a1e', background: '#0d0d0f' }}>

          {/* Auth (only when live mode selected and not authenticated) */}
          {executionMode === 'live' && !authState.authenticated && (
            <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
              <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
                Operator Auth
              </div>
              <div className="flex gap-1">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loginOperator()}
                  placeholder="Password"
                  className="flex-1 px-2 py-1.5 text-[11px] outline-none"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background: '#111113',
                    border: '1px solid #1a1a1e',
                    color: '#e5e5e5',
                  }}
                />
                <button
                  onClick={loginOperator}
                  disabled={authBusy || !password}
                  className="px-2 py-1.5 text-[10px] uppercase tracking-wider disabled:opacity-30"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background: '#1a1a1e',
                    color: '#e5e5e5',
                  }}
                >
                  Go
                </button>
              </div>
              {authState.error && (
                <div className="mt-1 text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#ef4444' }}>
                  {authState.error}
                </div>
              )}
            </div>
          )}

          {/* Auth active indicator */}
          {executionMode === 'live' && authState.authenticated && (
            <div className="flex items-center justify-between p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
              <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#34d399' }}>
                Operator active
              </span>
              <button
                onClick={logoutOperator}
                className="text-[9px] uppercase tracking-wider opacity-40 hover:opacity-100"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                Logout
              </button>
            </div>
          )}

          {/* Scenarios */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-3" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Scenarios
            </div>
            <div className="flex flex-col gap-1.5">
              <button
                onClick={() => runScenario('approved')}
                disabled={!canRun}
                className="w-full text-left px-3 py-2 text-[11px] transition-all disabled:opacity-30"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  background: '#0a2e1a',
                  border: '1px solid #134e2a',
                  color: '#34d399',
                }}
              >
                <span className="opacity-60 mr-1">▶</span> Approved Payment
              </button>
              <button
                onClick={() => runScenario('blocked')}
                disabled={!canRun}
                className="w-full text-left px-3 py-2 text-[11px] transition-all disabled:opacity-30"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  background: '#2e0a0a',
                  border: '1px solid #4e1313',
                  color: '#f87171',
                }}
              >
                <span className="opacity-60 mr-1">▶</span> Blocked by Policy
              </button>
              <button
                onClick={() => runScenario('approval')}
                disabled={!canRun}
                className="w-full text-left px-3 py-2 text-[11px] transition-all disabled:opacity-30"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  background: '#2e2a0a',
                  border: '1px solid #4e4413',
                  color: '#fbbf24',
                }}
              >
                <span className="opacity-60 mr-1">▶</span> Human Approval
              </button>
            </div>
          </div>

          {/* Network Info */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Network
            </div>
            <div className="space-y-1.5">
              {[
                ['Chain', isLive ? 'Base Sepolia' : 'Simulated'],
                ['Chain ID', isLive ? '84532' : 'N/A'],
                ['Custody', isLive ? 'Turnkey MPC' : 'Simulated'],
                ['RPC', isLive ? 'sepolia.base.org' : 'Local'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</span>
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: isLive ? '#34d399' : '#808080' }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Wallet */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Agent Wallet
            </div>
            <div className="text-xl font-semibold tracking-tight" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              ${demo.cardBalance.toFixed(2)}
            </div>
            <div className="text-[10px] mt-0.5" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              USDC {isLive ? '(Base Sepolia)' : '(Simulated)'}
            </div>
          </div>

          {/* Policy */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Spending Policy
            </div>
            <div className="space-y-1">
              {[
                ['Per-tx limit', '$100.00'],
                ['Daily limit', '$1,000.00'],
                ['Used today', `$${demo.policyUsed.toFixed(2)}`],
                ['Categories', 'SaaS, API, Compute'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</span>
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#e5e5e5' }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Kill Switch */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Kill Switch
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: demo.cardStatus === 'FROZEN' ? '#f87171' : '#34d399' }}>
                {demo.cardStatus === 'FROZEN' ? 'ACTIVE (Frozen)' : 'CLEAR'}
              </span>
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: demo.cardStatus === 'FROZEN' ? '#ef4444' : '#22c55e' }} />
            </div>
          </div>

          {/* History */}
          <div className="flex-1 p-3 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] uppercase tracking-[0.2em]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
                History
              </span>
              {demo.history.length > 0 && (
                <button
                  onClick={demo.clearHistory}
                  className="text-[9px] uppercase tracking-wider opacity-30 hover:opacity-100"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  Clear
                </button>
              )}
            </div>
            <div className="space-y-1">
              {demo.history.length === 0 && (
                <div className="text-[10px] opacity-20" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  No transactions yet
                </div>
              )}
              {demo.history.slice(0, 10).map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between py-1 border-b"
                  style={{ borderColor: '#111113' }}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="inline-block h-1.5 w-1.5 rounded-full" style={{
                      background: entry.type === 'approved' ? '#22c55e' : entry.type === 'blocked' ? '#ef4444' : '#f59e0b',
                    }} />
                    <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#808080' }}>
                      {entry.to}
                    </span>
                  </div>
                  <span className="text-[10px]" style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: entry.type === 'approved' ? '#34d399' : entry.type === 'blocked' ? '#f87171' : '#fbbf24',
                  }}>
                    {entry.type === 'blocked' ? '✗' : entry.type === 'approved' ? '✓' : '⏸'} ${entry.amount}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CENTER: Terminal ── */}
        <div className="overflow-hidden">
          <TerminalView logs={demo.logs} state={demo.state} />
        </div>

        {/* ── RIGHT PANEL: Transaction Details + Dashboard ── */}
        <div className="flex flex-col border-l overflow-y-auto" style={{ borderColor: '#1a1a1e', background: '#0d0d0f' }}>

          {/* Current State */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Execution State
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full" style={{
                background: demo.state === 'SUCCESS' ? '#22c55e'
                  : demo.state === 'POLICY_BLOCKED' ? '#ef4444'
                  : demo.state === 'PENDING_APPROVAL' ? '#f59e0b'
                  : demo.state === 'IDLE' ? '#333'
                  : '#3b82f6',
                animation: demo.isRunning ? 'pulse 1.5s infinite' : 'none',
              }} />
              <span className="text-[11px]" style={{
                fontFamily: "'JetBrains Mono', monospace",
                color: demo.state === 'SUCCESS' ? '#34d399'
                  : demo.state === 'POLICY_BLOCKED' ? '#f87171'
                  : demo.state === 'PENDING_APPROVAL' ? '#fbbf24'
                  : demo.state === 'IDLE' ? '#555'
                  : '#60a5fa',
              }}>
                {demo.state.replace(/_/g, ' ')}
              </span>
            </div>
          </div>

          {/* Live Error */}
          {demo.liveStatus.lastError && (
            <div className="p-3 border-b" style={{ borderColor: '#4e1313', background: '#1a0808' }}>
              <div className="text-[9px] uppercase tracking-[0.2em] mb-1" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#f87171' }}>
                Error
              </div>
              <div className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#fca5a5' }}>
                {demo.liveStatus.lastError}
              </div>
              {demo.liveStatus.fallbackRecommended && (
                <button
                  onClick={() => setExecutionMode('simulated')}
                  className="mt-2 px-2 py-1 text-[9px] uppercase tracking-wider"
                  style={{ fontFamily: "'JetBrains Mono', monospace", background: '#2e0a0a', border: '1px solid #4e1313', color: '#f87171' }}
                >
                  Switch to simulated
                </button>
              )}
            </div>
          )}

          {/* Transaction Result */}
          {demo.transaction && (
            <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
              <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#34d399' }}>
                Transaction
              </div>
              <div className="space-y-1.5">
                {[
                  ['Amount', `$${demo.transaction.amount} ${demo.transaction.token}`],
                  ['To', demo.transaction.to],
                  ['Chain', demo.transaction.chain],
                  ['Block', demo.transaction.block],
                  ['TX Hash', demo.transaction.hash],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="text-[9px] uppercase" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</div>
                    <div className="text-[10px] break-all" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#e5e5e5' }}>{value}</div>
                  </div>
                ))}
                {demo.transaction.url && (
                  <a
                    href={demo.transaction.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-1 text-[10px] hover:underline"
                    style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--sardis-orange)' }}
                  >
                    View on Explorer →
                  </a>
                )}
                {isLive && demo.transaction.hash?.startsWith('0x') && (
                  <a
                    href={`https://sepolia.basescan.org/tx/${demo.transaction.hashFull || demo.transaction.hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-1 text-[10px] hover:underline"
                    style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--sardis-orange)' }}
                  >
                    Verify on BaseScan →
                  </a>
                )}
              </div>
            </div>
          )}

          {/* Blocked Attempt */}
          {demo.blockedAttempt && !demo.transaction && (
            <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
              <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{
                fontFamily: "'JetBrains Mono', monospace",
                color: demo.state === 'PENDING_APPROVAL' ? '#fbbf24' : '#f87171',
              }}>
                {demo.state === 'PENDING_APPROVAL' ? 'Awaiting Approval' : 'Blocked Transaction'}
              </div>
              <div className="space-y-1.5">
                {[
                  ['Vendor', demo.blockedAttempt.vendor],
                  ['Amount', `$${demo.blockedAttempt.amount.toLocaleString()}`],
                  ['Reason', demo.blockedAttempt.reason],
                  ['Code', demo.blockedAttempt.reasonCode],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="text-[9px] uppercase" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</div>
                    <div className="text-[10px] break-all" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: label === 'Reason' || label === 'Code'
                        ? (demo.state === 'PENDING_APPROVAL' ? '#fbbf24' : '#f87171')
                        : '#e5e5e5',
                    }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Approve / Reject buttons */}
              {demo.state === 'PENDING_APPROVAL' && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={demo.approveTransaction}
                    className="flex-1 py-2 text-[11px] uppercase tracking-wider font-semibold transition-colors"
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      background: '#0a2e1a',
                      border: '1px solid #134e2a',
                      color: '#34d399',
                    }}
                  >
                    Approve
                  </button>
                  <button
                    onClick={demo.rejectTransaction}
                    className="flex-1 py-2 text-[11px] uppercase tracking-wider font-semibold transition-colors"
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      background: '#2e0a0a',
                      border: '1px solid #4e1313',
                      color: '#f87171',
                    }}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          )}

          {/* 12-Check Pipeline */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              12-Check Pipeline
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5">
              {[
                'Kill Switch', 'Amount', 'Daily Cap', 'Monthly Cap',
                'Merchant', 'Category', 'Time Window', 'First-Seen',
                'Anomaly', 'Approval', 'Compliance', 'KYA',
              ].map((check, i) => {
                const isActive = demo.state !== 'IDLE'
                const isPassed = demo.state === 'SUCCESS' || (demo.state === 'POLICY_BLOCKED' && i < 3)
                const isFailed = demo.state === 'POLICY_BLOCKED' && i === 3
                return (
                  <div key={check} className="flex items-center gap-1">
                    <span className="inline-block h-1 w-1 rounded-full" style={{
                      background: !isActive ? '#222' : isFailed ? '#ef4444' : isPassed ? '#22c55e' : '#333',
                    }} />
                    <span className="text-[9px]" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: !isActive ? '#333' : isFailed ? '#f87171' : isPassed ? '#555' : '#333',
                    }}>
                      {check}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Funding */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Treasury
            </div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>Wallet Reserve</span>
              <span className="text-[11px]" style={{ fontFamily: "'JetBrains Mono', monospace" }}>${demo.walletBalance.toFixed(2)}</span>
            </div>
            <button
              onClick={() => demo.topUpCard(50)}
              className="w-full px-2 py-1.5 text-[10px] uppercase tracking-wider transition-colors"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                background: '#111113',
                border: '1px solid #1a1a1e',
                color: '#808080',
              }}
            >
              Top Up +$50
            </button>
          </div>

          {/* Audit Trail */}
          <div className="flex-1 p-3">
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Audit Evidence
            </div>
            {demo.state === 'IDLE' ? (
              <div className="text-[10px] opacity-20" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Run a scenario to generate audit trail
              </div>
            ) : (
              <div className="space-y-1">
                {[
                  ['Policy snapshot', demo.state !== 'IDLE' ? 'Captured' : 'Pending'],
                  ['Evaluation log', demo.state !== 'IDLE' ? '12/12 checks' : 'Pending'],
                  ['HMAC signature', demo.state === 'SUCCESS' ? 'Signed' : 'Pending'],
                  ['Merkle proof', demo.state === 'SUCCESS' ? 'Anchored' : 'Pending'],
                  ['Attestation', demo.state === 'SUCCESS' ? 'Sealed' : 'Pending'],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-[9px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</span>
                    <span className="text-[9px]" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: value === 'Pending' ? '#333' : value === 'Signed' || value === 'Anchored' || value === 'Sealed' ? '#34d399' : '#808080',
                    }}>{value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── BOTTOM BAR ── */}
      <footer className="flex items-center justify-between border-t px-4 py-1.5" style={{ borderColor: '#1a1a1e', background: '#0d0d0f' }}>
        <div className="flex items-center gap-4">
          <span className="text-[9px] uppercase tracking-wider" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#333' }}>
            Sardis v2.0.0
          </span>
          <span className="text-[9px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#333' }}>
            {isLive ? 'Base Sepolia (84532) | Turnkey MPC | Non-Custodial' : 'Simulated Mode | No Real Funds'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {isLive && (
            <a
              href="https://sepolia.basescan.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[9px] uppercase tracking-wider hover:underline"
              style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}
            >
              BaseScan Explorer
            </a>
          )}
          <a
            href="/docs/quickstart"
            className="text-[9px] uppercase tracking-wider hover:underline"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}
          >
            Docs
          </a>
        </div>
      </footer>
    </div>
  )
}
