# Sardis Design Partner Staging Readiness (Start-to-End)

This document defines the minimum, operator-ready flow for running Sardis with paid design partners in **testnet/pre-prod only**.

## 1) Scope and Guardrails

- Environment: `staging` / `testnet` only
- Funds: no real money
- Support model: supervised onboarding with explicit weekly checkpoints
- Contracting: no production SLA, no custody claims, no mainnet commitments

## 2) Start-to-End Flow

### A. Platform bootstrap (internal)

1. Deploy Sardis API to staging with isolated credentials.
2. Configure KYC/sanctions services in non-production mode.
3. Ensure durable audit store is enabled (no in-memory-only mode).
4. Validate health endpoints and error monitoring.

### B. Developer integration (partner side)

1. Install MCP server in the partner's agent runtime.
2. Run bootstrap:
   - `npx @sardis/mcp-server init --mode simulated`
   - For connected staging API: `npx @sardis/mcp-server init --mode live --api-url <staging-url> --api-key <partner-key>`
3. Confirm generated `.env.sardis` values:
   - `SARDIS_API_URL`
   - `SARDIS_MODE`
   - `SARDIS_AGENT_ID`
   - `SARDIS_WALLET_ID`
4. Start MCP server:
   - `npx @sardis/mcp-server start`
   - If dependencies are missing locally, CLI now returns a clear install hint.
5. Run one happy-path payment and one deny-path payment (limit/merchant rule).
6. Run one above-threshold transaction and verify API returns `approval_required` with an `approval_id`.

### C. Finance/policy onboarding (Sardis side)

1. Create an initial policy from natural language.
2. Compile and review machine rule output before activation.
3. Enable at least one approval threshold (for example >$500 equivalent).
4. Validate reason codes in blocked/pending events.

### D. Observability and audit validation

1. Verify each decision emits:
   - timestamp
   - agent id
   - policy version or rule id
   - decision reason code
2. Verify ledger and audit endpoints can reconstruct one full transaction chain.
3. Export logs for a 24h window and confirm analyst readability.

## 3) Mandatory Go/No-Go Gates (Design Partner Program)

1. `MCP Bootstrap Gate`:
   - `init` command works for simulated + live staging setup.
2. `Policy Enforcement Gate`:
   - limit exceeded and merchant denied scenarios are deterministically blocked.
3. `Approval Gate`:
   - above-threshold transactions return deterministic `approval_required` and create an approval record.
4. `Audit Gate`:
   - no payment execution without traceable decision logs.
5. `Isolation Gate`:
   - cross-agent wallet/card access attempts fail.

If any gate fails, keep partner in sandbox-only exploratory mode and do not advertise operational readiness.

## 4) Current Known Constraint

- Local Node execution is currently blocked in this environment due DNS/network (`ENOTFOUND registry.npmjs.org`), so local npm-based MCP/TS SDK verification may be incomplete on this machine.
- Mitigation: rely on CI workflow gates for Node packages until local network is fixed.

## 5) Recommended Operating Cadence (first 30 days)

1. Week 1: integration + first transactions
2. Week 2: policy tuning + approval workflow
3. Week 3: stress/edge-case replay tests
4. Week 4: readiness review and production gap decision

## 6) Exit Criteria for Expanding Program

- At least 2 partners complete full staging flow without manual DB fixes.
- 0 unresolved critical compliance/logging defects for two consecutive weeks.
- Protocol tests (AP2/UCP/TAP/x402 paths used by partners) are green in CI.

## 7) Decision Checklist Reference

Use `docs/release/design-partner-go-no-go-checklist.md` for formal weekly Go/No-Go decisions.
Use `docs/release/design-partner-t0-review-template.md` to record the kickoff decision meeting.
