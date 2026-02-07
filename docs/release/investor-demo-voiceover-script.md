# Sardis Investor Demo Voiceover (2-3 Minutes)

This script is aligned to `scripts/investor_demo_flow.py` and the JSON/Markdown artifacts produced in `artifacts/investor-demo/`.

## Timing + Track

### 0:00-0:20 - Problem framing
- "AI agents can execute workflows, but they still cannot spend safely by default."
- "Sardis is the payment OS that gives each agent controlled money access with policy enforcement and auditability."

### 0:20-0:45 - One-click identity bootstrap
- Show API call / UI action creating a Payment Identity.
- "In one click, Sardis issues a signed payment identity for this agent and binds a wallet."
- "This identity is what developers pass to MCP initialization."

### 0:45-1:05 - MCP integration
- Show command:
  - `npx @sardis/mcp-server init --mode live --payment-identity <id>`
- "No custom payment wiring. The MCP server resolves wallet, agent, and chain context automatically."

### 1:05-1:35 - Blocked flow (policy rejection)
- Trigger a payment request that violates policy.
- "The agent asks to spend out of policy. Sardis blocks it before execution."
- "Notice deterministic reason code and decision envelope in the response."

### 1:35-2:05 - Approved flow (execution)
- Trigger in-policy payment.
- "Now the same agent pays within policy using a prefunded rail."
- "We get transaction hash, ledger entry, and audit anchor for compliance traceability."

### 2:05-2:25 - Card lifecycle controls
- Show card control action (unfreeze/freeze/cancel).
- "Agent cards are lifecycle-managed. We can freeze, unfreeze, or cancel instantly."

### 2:25-2:45 - Wallet/card bridge narrative
- "When card usage ends, treasury can rotate balances and continue from stablecoin wallet rails."
- "The key is policy-first execution with full trace."

### 2:45-3:00 - Close
- "Sardis turns agent payments from risky improvisation into deterministic infrastructure."
- "Design partners can start in testnet/staging today with production-shaped controls."

## Demo Operator Checklist

1. Run: `python3 scripts/investor_demo_flow.py --base-url <url> --admin-email <email> --admin-password <password> --hybrid-live`
2. Open generated markdown artifact in `artifacts/investor-demo/`.
3. Keep terminal output visible for timestamps and step status.
4. If chain action fails in sandbox, use the fallback result section from the artifact.
