import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSardisDemo } from '@/components/demo/useSardisDemo'
import TerminalView from '@/components/demo/TerminalView'

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

      {/* ── TOP BAR ── */}
      <header className="flex items-center justify-between border-b px-4 py-2" style={{ borderColor: '#1a1a1e', background: '#0d0d0f' }}>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-xs opacity-50 hover:opacity-100 transition-opacity" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
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

          {/* Spending Policy */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Active Policy
            </div>
            {/* Natural language rule */}
            <div className="mb-2 px-2 py-1.5" style={{ background: '#111113', border: '1px solid #1a1a1e' }}>
              <div className="text-[9px] italic" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#808080' }}>
                "Max $100/tx, $1,000/day. SaaS, API, and compute only. Require approval above $500. Block gambling and crypto exchanges."
              </div>
            </div>
            {/* Parsed rules */}
            <div className="space-y-1">
              {[
                ['Per-tx limit', '$100.00'],
                ['Daily limit', '$1,000.00'],
                ['Auto-approve below', '$50.00'],
                ['Used today', `$${demo.policyUsed.toFixed(2)}`],
                ['Allowed', 'SaaS, API, Compute'],
                ['Blocked', 'Gambling, Crypto Ex.'],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{label}</span>
                  <span className="text-[10px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: label === 'Blocked' ? '#f87171' : '#e5e5e5' }}>{value}</span>
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

          {/* 12-Check Policy Firewall */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] uppercase tracking-[0.2em]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
                Policy Firewall
              </span>
              {demo.state !== 'IDLE' && (
                <span className="text-[9px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: demo.state === 'POLICY_BLOCKED' ? '#f87171' : demo.state === 'SUCCESS' ? '#34d399' : '#60a5fa' }}>
                  {demo.state === 'POLICY_BLOCKED' ? 'DENIED' : demo.state === 'SUCCESS' ? '12/12 PASS' : demo.state === 'PENDING_APPROVAL' ? 'ESCALATED' : 'CHECKING...'}
                </span>
              )}
            </div>
            <div className="space-y-0.5">
              {[
                { name: 'Kill Switch', desc: 'Global/agent/wallet freeze check', failAt: -1 },
                { name: 'Amount Validation', desc: 'amount > 0, within tx limit', failAt: -1 },
                { name: 'Scope Check', desc: 'Spending category allowed', failAt: -1 },
                { name: 'MCC Verification', desc: 'Merchant category code check', failAt: 3 },
                { name: 'Per-TX Limit', desc: `$100.00 max per transaction`, failAt: 4 },
                { name: 'Daily Budget', desc: '$1,000/day rolling window', failAt: -1 },
                { name: 'Monthly Budget', desc: '$10,000/month cap', failAt: -1 },
                { name: 'Merchant Rules', desc: 'Allow/deny list + per-merchant caps', failAt: -1 },
                { name: 'First-Seen Check', desc: 'New merchant → lower threshold', failAt: -1 },
                { name: 'Anomaly Score', desc: '6-signal risk scoring', failAt: -1 },
                { name: 'Approval Gate', desc: '4-eyes quorum above $500', failAt: 10 },
                { name: 'KYA Attestation', desc: 'Agent identity verification', failAt: -1 },
              ].map((check, i) => {
                const isIdle = demo.state === 'IDLE'
                const isBlocked = demo.state === 'POLICY_BLOCKED'
                const isApproval = demo.state === 'PENDING_APPROVAL'
                const blockedScenario = demo.scenario
                // For blocked: fail at check 4 (per-tx limit)
                const failIndex = blockedScenario === 'blocked' ? 4 : blockedScenario === 'approval' ? 10 : -1
                const isPassed = !isIdle && (
                  demo.state === 'SUCCESS' ||
                  (isBlocked && i < failIndex) ||
                  (isApproval && i < failIndex) ||
                  (!isBlocked && !isApproval && !isIdle)
                )
                const isFailed = !isIdle && isBlocked && i === failIndex
                const isEscalated = !isIdle && isApproval && i === failIndex
                const isSkipped = !isIdle && ((isBlocked && i > failIndex) || (isApproval && i > failIndex))

                return (
                  <div key={check.name} className="flex items-center gap-1.5 py-px">
                    <span className="inline-block h-1.5 w-1.5 rounded-sm flex-shrink-0" style={{
                      background: isIdle ? '#1a1a1e'
                        : isFailed ? '#ef4444'
                        : isEscalated ? '#f59e0b'
                        : isPassed ? '#22c55e'
                        : isSkipped ? '#1a1a1e'
                        : '#3b82f6',
                    }} />
                    <span className="text-[9px] flex-shrink-0 w-[80px]" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: isIdle ? '#333'
                        : isFailed ? '#f87171'
                        : isEscalated ? '#fbbf24'
                        : isPassed ? '#6b7280'
                        : isSkipped ? '#222'
                        : '#60a5fa',
                    }}>
                      {check.name}
                    </span>
                    <span className="text-[8px] truncate" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: isIdle ? '#222'
                        : isFailed ? '#f87171'
                        : isEscalated ? '#fbbf24'
                        : isPassed ? '#333'
                        : '#222',
                    }}>
                      {isFailed ? 'FAILED' : isEscalated ? 'ESCALATED' : isPassed ? (i < 3 ? '' : check.desc) : ''}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Trust Layers */}
          <div className="p-3 border-b" style={{ borderColor: '#1a1a1e' }}>
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Trust Layers
            </div>
            <div className="space-y-1.5">
              {[
                { name: 'Policy Engine', desc: 'Natural language → deterministic rules', status: 'active', color: '#34d399' },
                { name: 'Approval Workflow', desc: '4-eyes quorum for high-value tx', status: demo.state === 'PENDING_APPROVAL' ? 'engaged' : 'standby', color: demo.state === 'PENDING_APPROVAL' ? '#fbbf24' : '#333' },
                { name: 'Kill Switch', desc: '5 scopes: agent/wallet/rail/chain/global', status: demo.cardStatus === 'FROZEN' ? 'ACTIVE' : 'clear', color: demo.cardStatus === 'FROZEN' ? '#ef4444' : '#333' },
                { name: 'Audit Trail', desc: 'HMAC receipts + Merkle proofs', status: demo.state === 'SUCCESS' ? 'sealed' : 'recording', color: demo.state === 'SUCCESS' ? '#34d399' : '#555' },
                { name: 'Compliance', desc: 'KYC + sanctions + PEP screening', status: 'active', color: '#34d399' },
              ].map((layer) => (
                <div key={layer.name} className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-[9px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#808080' }}>{layer.name}</div>
                    <div className="text-[8px] truncate" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#333' }}>{layer.desc}</div>
                  </div>
                  <span className="text-[8px] uppercase ml-1 flex-shrink-0" style={{ fontFamily: "'JetBrains Mono', monospace", color: layer.color }}>
                    {layer.status}
                  </span>
                </div>
              ))}
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

          {/* Cryptographic Audit Evidence */}
          <div className="flex-1 p-3">
            <div className="text-[9px] uppercase tracking-[0.2em] mb-2" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>
              Attestation Envelope
            </div>
            {demo.state === 'IDLE' ? (
              <div className="text-[10px] opacity-20" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Run a scenario to generate cryptographic evidence
              </div>
            ) : (
              <div className="space-y-1">
                {[
                  { label: 'Policy version', value: demo.state !== 'IDLE' ? 'pol_v2.1.0_a3f8' : null, done: demo.state !== 'IDLE' },
                  { label: 'Pipeline result', value: demo.state === 'SUCCESS' ? 'PASS (12/12)' : demo.state === 'POLICY_BLOCKED' ? 'DENY (check #5)' : demo.state === 'PENDING_APPROVAL' ? 'ESCALATE (check #11)' : 'Running...', done: demo.state !== 'IDLE' },
                  { label: 'Agent DID', value: 'did:sardis:agent_demo_001', done: demo.state !== 'IDLE' },
                  { label: 'HMAC-SHA256', value: demo.state === 'SUCCESS' ? '0xa3f8...c291 (signed)' : 'Pending execution', done: demo.state === 'SUCCESS' },
                  { label: 'Merkle root', value: demo.state === 'SUCCESS' ? '0x7b2d...e891' : 'Pending', done: demo.state === 'SUCCESS' },
                  { label: 'Block anchor', value: demo.state === 'SUCCESS' ? '#19284721 (Base)' : 'Pending', done: demo.state === 'SUCCESS' },
                  { label: 'Tamper-evident', value: demo.state === 'SUCCESS' ? 'SEALED' : demo.state === 'POLICY_BLOCKED' ? 'SEALED (denial)' : 'Pending', done: demo.state === 'SUCCESS' || demo.state === 'POLICY_BLOCKED' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between">
                    <span className="text-[9px]" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#555' }}>{item.label}</span>
                    <span className="text-[9px] text-right max-w-[120px] truncate" style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      color: !item.done ? '#333' : item.value?.includes('PASS') || item.value?.includes('signed') || item.value?.includes('SEALED') ? '#34d399' : item.value?.includes('DENY') ? '#f87171' : item.value?.includes('ESCALATE') ? '#fbbf24' : '#808080',
                    }}>{item.value || 'Pending'}</span>
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
