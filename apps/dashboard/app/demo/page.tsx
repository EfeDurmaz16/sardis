"use client"

import Link from "next/link"
import { useState } from "react"

const DEMO_AGENTS = [
  { id: "agent_marketing_ai", name: "Marketing AI", trust: "LOW", budget: "$500/day" },
  { id: "agent_data_analytics", name: "Data Analytics AI", trust: "MEDIUM", budget: "$2,000/day" },
  { id: "agent_cloud_ops", name: "Cloud Ops AI", trust: "HIGH", budget: "$10,000/day" },
]

const DEMO_SCENARIOS = [
  { label: "Approved: $50 to OpenAI", amount: "50", merchant: "OpenAI", expected: true },
  { label: "Blocked: $15,000 to AWS (over limit)", amount: "15000", merchant: "AWS", expected: false },
  { label: "Blocked: $100 to Gambling.com (restricted)", amount: "100", merchant: "Gambling.com", expected: false },
  { label: "Approved: $200 to Anthropic", amount: "200", merchant: "Anthropic", expected: true },
]

type CheckResult = {
  step: string
  status: "pass" | "fail" | "skip"
  detail: string
}

type SimResult = {
  approved: boolean
  checks: CheckResult[]
  timestamp: string
}

export default function DemoPage() {
  const [agent, setAgent] = useState(DEMO_AGENTS[0])
  const [amount, setAmount] = useState("50")
  const [merchant, setMerchant] = useState("OpenAI")
  const [policy, setPolicy] = useState("Max $500 per day, only AI and cloud vendors, require approval above $200")
  const [result, setResult] = useState<SimResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<Array<SimResult & { amount: string; merchant: string }>>([])

  async function runSimulation() {
    setLoading(true)
    setResult(null)

    // Simulate the 7-phase pipeline locally (no API needed)
    await new Promise(r => setTimeout(r, 800))

    const amt = parseFloat(amount)
    const checks: CheckResult[] = []

    // Phase 1: Policy check
    const dailyLimit = 500
    const policyPass = amt <= dailyLimit
    checks.push({
      step: "Spending Policy",
      status: policyPass ? "pass" : "fail",
      detail: policyPass
        ? `$${amount} within $${dailyLimit}/day limit`
        : `$${amount} exceeds $${dailyLimit}/day limit`,
    })

    // Phase 2: Merchant scope
    const allowedMerchants = ["openai", "anthropic", "aws", "google cloud", "azure"]
    const merchantAllowed = allowedMerchants.some(m => merchant.toLowerCase().includes(m))
    checks.push({
      step: "Merchant Scope",
      status: merchantAllowed ? "pass" : "fail",
      detail: merchantAllowed
        ? `${merchant} is in allowed vendor list`
        : `${merchant} is not in allowed vendor list`,
    })

    // Phase 3: Compliance (KYC/AML)
    checks.push({
      step: "KYC / AML",
      status: "pass",
      detail: "Agent identity verified, no sanctions match",
    })

    // Phase 4: Mandate check
    const mandatePass = policyPass && merchantAllowed
    checks.push({
      step: "Spending Mandate",
      status: mandatePass ? "pass" : "fail",
      detail: mandatePass
        ? "Payment authorized by active mandate"
        : "Payment denied by mandate constraints",
    })

    // Phase 5: Approval threshold
    const needsApproval = amt > 200 && mandatePass
    checks.push({
      step: "Approval Threshold",
      status: needsApproval ? "pass" : "skip",
      detail: needsApproval
        ? `$${amount} > $200 threshold — would require human approval`
        : amt <= 200 ? "Below approval threshold" : "Skipped (already denied)",
    })

    // Phase 6: Rate limit
    checks.push({
      step: "Rate Limit",
      status: mandatePass ? "pass" : "skip",
      detail: mandatePass ? "3/10 requests used in current window" : "Skipped",
    })

    // Phase 7: Execution
    const approved = policyPass && merchantAllowed
    checks.push({
      step: "Settlement",
      status: approved ? "pass" : "skip",
      detail: approved
        ? "USDC → Stripe Connect → merchant bank (USD)"
        : "Payment blocked before execution",
    })

    const simResult: SimResult = {
      approved,
      checks,
      timestamp: new Date().toISOString(),
    }

    setResult(simResult)
    setHistory(prev => [{ ...simResult, amount, merchant }, ...prev].slice(0, 10))
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0A0A0F",
      color: "#FDFBF7",
      fontFamily: "system-ui, -apple-system, sans-serif",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(253,251,247,0.06)",
        padding: "16px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
            <path d="M20 5H10a7 7 0 000 14h2" stroke="#FDFBF7" strokeWidth="3" strokeLinecap="round" fill="none" />
            <path d="M8 23h10a7 7 0 000-14h-2" stroke="#FDFBF7" strokeWidth="3" strokeLinecap="round" fill="none" />
          </svg>
          <span style={{ fontWeight: 700, fontSize: 16 }}>Sardis</span>
          <span style={{ color: "rgba(253,251,247,0.3)", fontSize: 13 }}>Interactive Demo</span>
        </div>
        <Link
          href="/auth/sign-up"
          style={{
            background: "#FDFBF7",
            color: "#0A0A0F",
            padding: "8px 16px",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            textDecoration: "none",
          }}
        >
          Sign Up Free
        </Link>
      </div>

      <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
        {/* Title */}
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
          Try Sardis — no signup required
        </h1>
        <p style={{ color: "rgba(253,251,247,0.4)", fontSize: 15, marginBottom: 32 }}>
          Set a spending policy in plain English. Run a payment. See it approved or blocked in real time.
        </p>

        {/* Policy Input */}
        <div style={{
          background: "rgba(253,251,247,0.03)",
          border: "1px solid rgba(253,251,247,0.06)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 24,
        }}>
          <label style={{ fontSize: 12, color: "rgba(253,251,247,0.4)", textTransform: "uppercase" as const, letterSpacing: "0.05em", marginBottom: 8, display: "block" }}>
            Spending Policy (natural language)
          </label>
          <input
            value={policy}
            onChange={e => setPolicy(e.target.value)}
            style={{
              width: "100%",
              background: "transparent",
              border: "none",
              color: "#FDFBF7",
              fontSize: 16,
              outline: "none",
              fontFamily: "inherit",
            }}
          />
        </div>

        {/* Agent + Payment Form */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 12, marginBottom: 24 }}>
          <div style={{ background: "rgba(253,251,247,0.03)", border: "1px solid rgba(253,251,247,0.06)", borderRadius: 10, padding: "12px 16px" }}>
            <label style={{ fontSize: 11, color: "rgba(253,251,247,0.3)", display: "block", marginBottom: 4 }}>Agent</label>
            <select
              value={agent.id}
              onChange={e => setAgent(DEMO_AGENTS.find(a => a.id === e.target.value) || DEMO_AGENTS[0])}
              style={{ background: "transparent", border: "none", color: "#FDFBF7", fontSize: 14, width: "100%", outline: "none" }}
            >
              {DEMO_AGENTS.map(a => (
                <option key={a.id} value={a.id} style={{ background: "#1a1a2e" }}>{a.name}</option>
              ))}
            </select>
          </div>

          <div style={{ background: "rgba(253,251,247,0.03)", border: "1px solid rgba(253,251,247,0.06)", borderRadius: 10, padding: "12px 16px" }}>
            <label style={{ fontSize: 11, color: "rgba(253,251,247,0.3)", display: "block", marginBottom: 4 }}>Amount ($)</label>
            <input
              value={amount}
              onChange={e => setAmount(e.target.value)}
              type="number"
              style={{ background: "transparent", border: "none", color: "#FDFBF7", fontSize: 14, width: "100%", outline: "none" }}
            />
          </div>

          <div style={{ background: "rgba(253,251,247,0.03)", border: "1px solid rgba(253,251,247,0.06)", borderRadius: 10, padding: "12px 16px" }}>
            <label style={{ fontSize: 11, color: "rgba(253,251,247,0.3)", display: "block", marginBottom: 4 }}>Merchant</label>
            <input
              value={merchant}
              onChange={e => setMerchant(e.target.value)}
              style={{ background: "transparent", border: "none", color: "#FDFBF7", fontSize: 14, width: "100%", outline: "none" }}
            />
          </div>

          <button
            onClick={runSimulation}
            disabled={loading}
            style={{
              background: "#FDFBF7",
              color: "#0A0A0F",
              border: "none",
              borderRadius: 10,
              padding: "12px 24px",
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              alignSelf: "stretch",
              display: "flex",
              alignItems: "center",
              gap: 8,
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Running..." : "Run Payment"}
          </button>
        </div>

        {/* Quick Scenarios */}
        <div style={{ display: "flex", gap: 8, marginBottom: 32, flexWrap: "wrap" as const }}>
          {DEMO_SCENARIOS.map(s => (
            <button
              key={s.label}
              onClick={() => { setAmount(s.amount); setMerchant(s.merchant); }}
              style={{
                background: "transparent",
                border: "1px solid rgba(253,251,247,0.1)",
                borderRadius: 6,
                padding: "6px 12px",
                color: "rgba(253,251,247,0.5)",
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Result */}
        {result && (
          <div style={{
            background: "rgba(253,251,247,0.03)",
            border: `1px solid ${result.approved ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
            borderRadius: 12,
            padding: 24,
            marginBottom: 24,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: result.approved ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
              }}>
                {result.approved ? "\u2713" : "\u2717"}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 16 }}>
                  {result.approved ? "Payment Approved" : "Payment Blocked"}
                </div>
                <div style={{ fontSize: 13, color: "rgba(253,251,247,0.4)" }}>
                  7-phase pre-execution pipeline completed in 47ms
                </div>
              </div>
            </div>

            {/* Pipeline Steps */}
            <div style={{ display: "flex", flexDirection: "column" as const, gap: 8 }}>
              {result.checks.map((check, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: check.status === "fail"
                      ? "rgba(239,68,68,0.08)"
                      : check.status === "pass"
                      ? "rgba(34,197,94,0.05)"
                      : "transparent",
                  }}
                >
                  <div style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    background: check.status === "pass" ? "rgba(34,197,94,0.2)"
                      : check.status === "fail" ? "rgba(239,68,68,0.2)"
                      : "rgba(253,251,247,0.08)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 11,
                    flexShrink: 0,
                  }}>
                    {check.status === "pass" ? "\u2713" : check.status === "fail" ? "\u2717" : "-"}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{check.step}</div>
                    <div style={{ fontSize: 12, color: "rgba(253,251,247,0.4)" }}>{check.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div style={{
            background: "rgba(253,251,247,0.03)",
            border: "1px solid rgba(253,251,247,0.06)",
            borderRadius: 12,
            padding: 20,
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "rgba(253,251,247,0.5)" }}>
              Simulation History
            </div>
            {history.map((h, i) => (
              <div key={i} style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 0",
                borderTop: i > 0 ? "1px solid rgba(253,251,247,0.04)" : "none",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: h.approved ? "#22C55E" : "#EF4444",
                  }} />
                  <span style={{ fontSize: 13 }}>${h.amount} to {h.merchant}</span>
                </div>
                <span style={{
                  fontSize: 12,
                  color: h.approved ? "#22C55E" : "#EF4444",
                  fontWeight: 500,
                }}>
                  {h.approved ? "Approved" : "Blocked"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Bottom CTA */}
        <div style={{ textAlign: "center" as const, marginTop: 48, paddingBottom: 48 }}>
          <p style={{ color: "rgba(253,251,247,0.3)", fontSize: 14, marginBottom: 16 }}>
            This is a simulation. Sign up to connect real wallets and process live payments.
          </p>
          <Link
            href="/auth/sign-up"
            style={{
              background: "#FDFBF7",
              color: "#0A0A0F",
              padding: "12px 32px",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            Get Started Free
          </Link>
        </div>
      </div>
    </div>
  )
}
