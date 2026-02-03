import { useState, useCallback, useRef } from 'react'

const STATES = {
  IDLE: 'IDLE',
  INITIALIZING: 'INITIALIZING',
  PLANNING: 'PLANNING',
  SIGNING: 'SIGNING',
  CONFIRMING: 'CONFIRMING',
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
  PLANNING: [
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
}

export function useSardisDemo() {
  const [state, setState] = useState(STATES.IDLE)
  const [logs, setLogs] = useState([])
  const [transaction, setTransaction] = useState(null)
  const [cardBalance, setCardBalance] = useState(500)
  const [policyUsed, setPolicyUsed] = useState(120)
  const timeoutsRef = useRef([])

  const clearTimeouts = () => {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []
  }

  const addLogs = useCallback((sequence, onDone) => {
    sequence.forEach(({ text, delay }) => {
      const id = setTimeout(() => {
        setLogs(prev => [...prev, { text, ts: Date.now() }])
      }, delay)
      timeoutsRef.current.push(id)
    })
    const lastDelay = sequence[sequence.length - 1].delay
    const id = setTimeout(onDone, lastDelay + 600)
    timeoutsRef.current.push(id)
  }, [])

  const runDemo = useCallback(() => {
    clearTimeouts()
    setLogs([])
    setTransaction(null)
    setCardBalance(500)
    setPolicyUsed(120)

    // INITIALIZING
    setState(STATES.INITIALIZING)
    addLogs(LOG_SEQUENCES.INITIALIZING, () => {
      // PLANNING
      setState(STATES.PLANNING)
      addLogs(LOG_SEQUENCES.PLANNING, () => {
        // SIGNING
        setState(STATES.SIGNING)
        addLogs(LOG_SEQUENCES.SIGNING, () => {
          // CONFIRMING
          setState(STATES.CONFIRMING)
          addLogs(LOG_SEQUENCES.CONFIRMING, () => {
            // SUCCESS
            setState(STATES.SUCCESS)
            setCardBalance(475)
            setPolicyUsed(145)
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
            addLogs(LOG_SEQUENCES.SUCCESS, () => {})
          })
        })
      })
    })
  }, [addLogs])

  const reset = useCallback(() => {
    clearTimeouts()
    setState(STATES.IDLE)
    setLogs([])
    setTransaction(null)
    setCardBalance(500)
    setPolicyUsed(120)
  }, [])

  const isRunning = state !== STATES.IDLE && state !== STATES.SUCCESS

  return {
    state,
    logs,
    transaction,
    cardBalance,
    policyUsed,
    isRunning,
    runDemo,
    reset,
  }
}
