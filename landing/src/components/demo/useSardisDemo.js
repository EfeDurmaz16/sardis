import { useState, useCallback, useRef, useEffect } from 'react'

const STATES = {
  IDLE: 'IDLE',
  INITIALIZING: 'INITIALIZING',
  PLANNING: 'PLANNING',
  SIGNING: 'SIGNING',
  CONFIRMING: 'CONFIRMING',
  POLICY_BLOCKED: 'POLICY_BLOCKED',
  SUCCESS: 'SUCCESS',
}

const DEMO_TX_HASH = '0x8a3f...e7b2d41c'
const DEMO_TX_HASH_FULL = '0x8a3f7c91d2e4b056a1f38c9d7e2b4a61c8f3d09e7b2d41c'
const DEMO_WALLET = '0xA91c...3fE8'
const DEMO_AGENT_ID = 'agent_procurement_01'
const DEMO_BLOCK = '19284721'

const LOG_SEQUENCES = {
  INITIALIZING: [
    { text: `[Sardis-Core]: Initializing payment session...`, delay: 0 },
    { text: `[Sardis-Wallet]: Connecting to Turnkey MPC signer`, delay: 400 },
    { text: `[Sardis-Chain]: RPC handshake with Base Sepolia (chainId: 84532)`, delay: 800 },
    { text: `[Sardis-Chain]: ✓ Connected — latency 42ms`, delay: 1200 },
    { text: `[Sardis-Core]: Session ready. Agent: ${DEMO_AGENT_ID}`, delay: 1600 },
  ],
  PLANNING_APPROVED: [
    { text: `[AI-Agent]: Evaluating procurement request...`, delay: 0 },
    { text: `[AI-Agent]: Intent: Purchase 500 API credits from DataCorp`, delay: 500 },
    { text: `[Sardis-Protocol]: Constructing AP2 mandate chain`, delay: 900 },
    { text: `[Sardis-Protocol]:   → Intent verified (schema v2.1)`, delay: 1200 },
    { text: `[Sardis-Protocol]:   → Cart: 1 item, total 25.00 USDC`, delay: 1500 },
    { text: `[Sardis-Core]: Checking spending policy...`, delay: 1800 },
    { text: `[Sardis-Core]:   → Daily limit: $500.00 | Used: $120.00`, delay: 2100 },
    { text: `[Sardis-Core]:   → Category: SaaS/API — ✓ Allowed`, delay: 2400 },
    { text: `[Sardis-Core]: ✓ Policy check passed`, delay: 2700 },
  ],
  PLANNING_BLOCKED: [
    { text: `[AI-Agent]: Evaluating procurement request...`, delay: 0 },
    { text: `[AI-Agent]: Intent: Purchase 5,000 API credits from DataCorp`, delay: 500 },
    { text: `[Sardis-Protocol]: Constructing AP2 mandate chain`, delay: 900 },
    { text: `[Sardis-Protocol]:   → Intent verified (schema v2.1)`, delay: 1200 },
    { text: `[Sardis-Core]: Checking spending policy...`, delay: 1600 },
    { text: `[Sardis-Core]:   → Max per transaction: $100.00`, delay: 2000 },
    { text: `[Sardis-Core]:   → Requested amount: $5000.00`, delay: 2300 },
    { text: `[Sardis-Core]: ✗ Policy check failed (LIMIT_EXCEEDED)`, delay: 2700 },
  ],
  SIGNING: [
    { text: `[Sardis-Wallet]: Requesting MPC signature from Turnkey`, delay: 0 },
    { text: `[Sardis-Wallet]: Signer: ${DEMO_WALLET}`, delay: 400 },
    { text: `[Sardis-Wallet]: Signing EIP-1559 tx (maxFee: 0.12 gwei)`, delay: 800 },
    { text: `[Sardis-Wallet]: ✓ Signature obtained (2 of 3 shares)`, delay: 1500 },
  ],
  CONFIRMING: [
    { text: `[Sardis-Chain]: Broadcasting tx to Base Sepolia...`, delay: 0 },
    { text: `[Sardis-Chain]: tx: ${DEMO_TX_HASH}`, delay: 500 },
    { text: `[Sardis-Chain]: Waiting for confirmation (1/1 blocks)`, delay: 1000 },
    { text: `[Sardis-Chain]: ✓ Confirmed in block #${DEMO_BLOCK}`, delay: 2000 },
    { text: `[Sardis-Ledger]: Audit entry written (immutable)`, delay: 2400 },
  ],
  SUCCESS: [
    { text: `[Sardis-Core]: ✓ Payment complete — 25.00 USDC → DataCorp`, delay: 0 },
    { text: `[Sardis-Core]: Agent ${DEMO_AGENT_ID} session closed`, delay: 400 },
  ],
  POLICY_BLOCKED: [
    { text: `[Sardis-Core]: Payment blocked before execution`, delay: 0 },
    { text: `[Sardis-Core]: reason_code=SARDIS.POLICY.LIMIT_EXCEEDED`, delay: 400 },
    { text: `[Sardis-Core]: Financial Hallucination PREVENTED`, delay: 800 },
  ],
}

const LIVE_STEP_TEXT = {
  health: '[Sardis-Live]: API health check',
  policy_check: '[Sardis-Live]: Policy check request',
  card_simulate_purchase: '[Sardis-Live]: Card rail simulation',
}

function createRunId(mode, scenario) {
  return `${mode}_${scenario}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`
}

async function postDemoEvent(payload) {
  try {
    await fetch('/api/demo-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  } catch {
    // Best-effort telemetry; do not block demo flow.
  }
}

function parseJsonSafe(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export function useSardisDemo() {
  const DEFAULT_CARD_BALANCE = 500
  const DEFAULT_WALLET_BALANCE = 220

  const [state, setState] = useState(STATES.IDLE)
  const [scenario, setScenario] = useState('approved')
  const [logs, setLogs] = useState([])
  const [transaction, setTransaction] = useState(null)
  const [cardBalance, setCardBalance] = useState(DEFAULT_CARD_BALANCE)
  const [walletBalance, setWalletBalance] = useState(DEFAULT_WALLET_BALANCE)
  const [cardStatus, setCardStatus] = useState('ACTIVE')
  const [blockedAttempt, setBlockedAttempt] = useState(null)
  const [fundingEvent, setFundingEvent] = useState(null)
  const [policyUsed, setPolicyUsed] = useState(120)
  const [history, setHistory] = useState([])
  const [liveStatus, setLiveStatus] = useState({
    loading: false,
    lastError: null,
    lastOutcome: null,
    fallbackRecommended: false,
    lastRunAt: null,
  })

  const timeoutsRef = useRef([])
  const runContextRef = useRef({ runId: null, mode: 'simulated', scenario: 'approved' })

  const clearTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []
  }, [])

  const appendLog = useCallback((text) => {
    setLogs((prev) => [...prev, { text, ts: Date.now() }])
  }, [])

  const emitEvent = useCallback((eventType, extra = {}) => {
    const ctx = runContextRef.current
    if (!ctx.runId) return
    void postDemoEvent({
      runId: ctx.runId,
      mode: ctx.mode,
      scenario: ctx.scenario,
      eventType,
      ...extra,
    })
  }, [])

  useEffect(() => {
    emitEvent('state_change', { step: state, status: state })
  }, [state, emitEvent])

  const addLogs = useCallback((sequence, onDone) => {
    sequence.forEach(({ text, delay }) => {
      const id = setTimeout(() => {
        setLogs((prev) => [...prev, { text, ts: Date.now() }])
      }, delay)
      timeoutsRef.current.push(id)
    })
    const lastDelay = sequence[sequence.length - 1]?.delay ?? 0
    const id = setTimeout(onDone, lastDelay + 600)
    timeoutsRef.current.push(id)
  }, [])

  const resetState = useCallback(() => {
    clearTimeouts()
    setState(STATES.IDLE)
    setLogs([])
    setTransaction(null)
    setCardBalance(DEFAULT_CARD_BALANCE)
    setWalletBalance(DEFAULT_WALLET_BALANCE)
    setCardStatus('ACTIVE')
    setBlockedAttempt(null)
    setFundingEvent(null)
    setPolicyUsed(120)
  }, [clearTimeouts])

  const appendHistory = useCallback((entry) => {
    setHistory((prev) => [
      {
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        timestamp: new Date().toISOString(),
        ...entry,
      },
      ...prev,
    ])
  }, [])

  const beginRun = useCallback((mode, nextScenario) => {
    const runId = createRunId(mode, nextScenario)
    runContextRef.current = { runId, mode, scenario: nextScenario }
    setScenario(nextScenario)
    emitEvent('run_started', { status: 'start', message: `${mode}:${nextScenario}` })
  }, [emitEvent])

  const runDemo = useCallback((nextScenario = 'approved') => {
    resetState()
    beginRun('simulated', nextScenario)

    setState(STATES.INITIALIZING)
    addLogs(LOG_SEQUENCES.INITIALIZING, () => {
      setState(STATES.PLANNING)
      addLogs(
        nextScenario === 'blocked' ? LOG_SEQUENCES.PLANNING_BLOCKED : LOG_SEQUENCES.PLANNING_APPROVED,
        () => {
          if (nextScenario === 'blocked') {
            setState(STATES.POLICY_BLOCKED)
            setCardStatus('FROZEN')
            setBlockedAttempt({
              vendor: 'DataCorp',
              amount: 5000,
              reasonCode: 'SARDIS.POLICY.LIMIT_EXCEEDED',
              reason: 'Amount exceeds max per transaction ($100.00)',
              timestamp: new Date().toISOString(),
            })
            addLogs(LOG_SEQUENCES.POLICY_BLOCKED, () => {
              emitEvent('run_blocked', { status: 'blocked', message: 'simulated_policy_denied' })
            })
            appendHistory({
              type: 'blocked',
              to: 'DataCorp',
              amount: '5000.00',
              token: 'USD',
              chain: 'Policy',
              hash: 'SARDIS.POLICY.LIMIT_EXCEEDED',
              url: null,
            })
            setLiveStatus((prev) => ({
              ...prev,
              loading: false,
              lastError: null,
              lastOutcome: 'blocked',
              fallbackRecommended: false,
              lastRunAt: new Date().toISOString(),
            }))
            return
          }

          setState(STATES.SIGNING)
          addLogs(LOG_SEQUENCES.SIGNING, () => {
            setState(STATES.CONFIRMING)
            addLogs(LOG_SEQUENCES.CONFIRMING, () => {
              setState(STATES.SUCCESS)
              setCardStatus('ACTIVE')
              setCardBalance((prev) => Number((prev - 25).toFixed(2)))
              setPolicyUsed((prev) => Number((prev + 25).toFixed(2)))
              setTransaction({
                hash: DEMO_TX_HASH,
                hashFull: DEMO_TX_HASH_FULL,
                amount: '25.00',
                token: 'USDC',
                to: 'DataCorp',
                block: DEMO_BLOCK,
                chain: 'Base Sepolia',
                url: `https://sepolia.basescan.org/tx/${DEMO_TX_HASH_FULL}`,
              })
              appendHistory({
                type: 'approved',
                to: 'DataCorp',
                amount: '25.00',
                token: 'USDC',
                chain: 'Base Sepolia',
                hash: DEMO_TX_HASH,
                url: `https://sepolia.basescan.org/tx/${DEMO_TX_HASH_FULL}`,
              })
              addLogs(LOG_SEQUENCES.SUCCESS, () => {
                emitEvent('run_succeeded', { status: 'success', message: 'simulated_ok' })
              })
              setLiveStatus((prev) => ({
                ...prev,
                loading: false,
                lastError: null,
                lastOutcome: 'success',
                fallbackRecommended: false,
                lastRunAt: new Date().toISOString(),
              }))
            })
          })
        }
      )
    })
  }, [addLogs, appendHistory, beginRun, emitEvent, resetState])

  const runLiveDemo = useCallback(async (nextScenario = 'approved') => {
    resetState()
    beginRun('live', nextScenario)

    setLiveStatus({
      loading: true,
      lastError: null,
      lastOutcome: null,
      fallbackRecommended: false,
      lastRunAt: null,
    })

    setState(STATES.INITIALIZING)
    appendLog('[Sardis-Live]: Starting live mode flow through secure demo proxy')

    let payload
    try {
      const response = await fetch('/api/demo-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'run_flow',
          scenario: nextScenario,
        }),
      })
      const text = await response.text()
      payload = parseJsonSafe(text)
      if (!response.ok) {
        throw new Error(payload?.error || `HTTP_${response.status}`)
      }
      if (!payload?.ok) {
        throw new Error(payload?.error?.message || 'live_flow_failed')
      }
    } catch (error) {
      const message = String(error?.message || 'Live flow failed')
      setState(STATES.POLICY_BLOCKED)
      setCardStatus('FROZEN')
      setBlockedAttempt({
        vendor: 'Live API',
        amount: nextScenario === 'blocked' ? 5000 : 25,
        reasonCode: 'SARDIS.LIVE.ERROR',
        reason: message,
        timestamp: new Date().toISOString(),
      })
      appendLog(`[Sardis-Live]: ✗ ${message}`)
      appendLog('[Sardis-Live]: Fallback available: switch to simulated mode')
      emitEvent('run_failed', { status: 'error', message })
      setLiveStatus({
        loading: false,
        lastError: message,
        lastOutcome: 'error',
        fallbackRecommended: true,
        lastRunAt: new Date().toISOString(),
      })
      return
    }

    setState(STATES.PLANNING)
    const steps = Array.isArray(payload.steps) ? payload.steps : []
    steps.forEach((step) => {
      const prefix = LIVE_STEP_TEXT[step.step] || `[Sardis-Live]: ${step.step}`
      if (step.ok) {
        appendLog(`${prefix} ✓ (${step.durationMs || 0}ms)`)
      } else {
        appendLog(`${prefix} ✗ ${step.error || 'failed'} (${step.durationMs || 0}ms)`)
      }
    })

    const result = payload.result || {}
    if (result.outcome === 'blocked') {
      setState(STATES.POLICY_BLOCKED)
      setCardStatus('FROZEN')
      setBlockedAttempt(
        result.blockedAttempt || {
          vendor: 'Policy Engine',
          amount: nextScenario === 'blocked' ? 5000 : 25,
          reasonCode: 'SARDIS.POLICY.DENIED',
          reason: result.policy?.reason || 'Policy denied transaction',
          timestamp: new Date().toISOString(),
        }
      )
      appendHistory({
        type: 'blocked',
        to: 'Policy Engine',
        amount: String(nextScenario === 'blocked' ? 5000 : 25),
        token: 'USD',
        chain: 'Policy',
        hash: result.blockedAttempt?.reasonCode || 'SARDIS.POLICY.DENIED',
        url: null,
      })
      appendLog(`[Sardis-Live]: ✗ Blocked — ${result.policy?.reason || 'policy_denied'}`)
      emitEvent('run_blocked', { status: 'blocked', message: result.policy?.reason || 'policy_denied' })
      setLiveStatus({
        loading: false,
        lastError: null,
        lastOutcome: 'blocked',
        fallbackRecommended: false,
        lastRunAt: new Date().toISOString(),
      })
      return
    }

    setState(STATES.SIGNING)
    addLogs(LOG_SEQUENCES.SIGNING, () => {
      setState(STATES.CONFIRMING)
      addLogs(LOG_SEQUENCES.CONFIRMING, () => {
        setState(STATES.SUCCESS)
        setCardStatus('ACTIVE')
        setCardBalance((prev) => Number((prev - 25).toFixed(2)))
        setPolicyUsed((prev) => Number((prev + 25).toFixed(2)))

        const liveTx = result.transaction || {}
        setTransaction({
          hash: liveTx.hash || 'tx_live_demo',
          hashFull: liveTx.hashFull || liveTx.hash || 'tx_live_demo',
          amount: liveTx.amount || '25.00',
          token: liveTx.token || 'USD',
          to: liveTx.to || 'DataCorp',
          block: liveTx.block || 'live',
          chain: liveTx.chain || 'Card Rail',
          url: liveTx.url || null,
        })
        appendHistory({
          type: 'approved',
          to: liveTx.to || 'DataCorp',
          amount: liveTx.amount || '25.00',
          token: liveTx.token || 'USD',
          chain: liveTx.chain || 'Card Rail',
          hash: liveTx.hash || 'tx_live_demo',
          url: liveTx.url || null,
        })

        appendLog('[Sardis-Live]: ✓ Live payment flow completed')
        emitEvent('run_succeeded', { status: 'success', message: 'live_ok' })
        setLiveStatus({
          loading: false,
          lastError: null,
          lastOutcome: 'success',
          fallbackRecommended: false,
          lastRunAt: new Date().toISOString(),
        })
      })
    })
  }, [addLogs, appendHistory, appendLog, beginRun, emitEvent, resetState])

  const runRecordMode = useCallback((mode = 'simulated') => {
    if (mode === 'live') {
      void runLiveDemo('approved')
      return
    }
    runDemo('approved')
  }, [runDemo, runLiveDemo])

  const reset = useCallback(() => {
    resetState()
    runContextRef.current = { runId: null, mode: 'simulated', scenario: 'approved' }
    setLiveStatus({
      loading: false,
      lastError: null,
      lastOutcome: null,
      fallbackRecommended: false,
      lastRunAt: null,
    })
  }, [resetState])

  const clearHistory = useCallback(() => {
    setHistory([])
  }, [])

  const runApprovedDemo = useCallback(() => runDemo('approved'), [runDemo])
  const runBlockedDemo = useCallback(() => runDemo('blocked'), [runDemo])

  const topUpCard = useCallback((amount = 50) => {
    const normalized = Number(amount)
    if (!Number.isFinite(normalized) || normalized <= 0) return false

    if (walletBalance < normalized) {
      appendLog('[Sardis-Funding]: ✗ Top-up failed — insufficient wallet funds')
      emitEvent('funding_failed', { status: 'error', message: 'insufficient_wallet_funds' })
      return false
    }

    setWalletBalance((prev) => Number((prev - normalized).toFixed(2)))
    setCardBalance((prev) => Number((prev + normalized).toFixed(2)))
    const event = {
      amount: normalized,
      token: 'USDC',
      source: 'Stablecoin Wallet',
      destination: 'Virtual Card',
      timestamp: new Date().toISOString(),
    }
    setFundingEvent(event)
    appendLog(`[Sardis-Funding]: ✓ +$${normalized.toFixed(2)} moved from wallet to card`)
    emitEvent('funding_succeeded', { status: 'success', message: `top_up_${normalized}` })
    return true
  }, [appendLog, emitEvent, walletBalance])

  const isRunning =
    state !== STATES.IDLE &&
    state !== STATES.SUCCESS &&
    state !== STATES.POLICY_BLOCKED

  return {
    STATES,
    state,
    scenario,
    logs,
    transaction,
    cardBalance,
    walletBalance,
    cardStatus,
    blockedAttempt,
    fundingEvent,
    policyUsed,
    history,
    liveStatus,
    isRunning,
    runDemo,
    runApprovedDemo,
    runBlockedDemo,
    runLiveDemo,
    runRecordMode,
    topUpCard,
    reset,
    clearHistory,
  }
}
