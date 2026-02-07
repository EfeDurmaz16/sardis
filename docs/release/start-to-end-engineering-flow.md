# Sardis Start-to-End Engineering Flow (Staging/Testnet)

This flow is the engineering reference for design partners using Sardis in pre-prod.

## 1) Platform Setup (Internal)

1. Deploy API in staging with isolated credentials (`DATABASE_URL`, chain mode, API keys).
2. Ensure approvals router is enabled and reachable (`/api/v2/approvals`).
3. Ensure policy store is persistent (not in-memory for shared staging).
4. Run:
   - `pnpm run bootstrap:js` (network/registry preflight)
   - `pnpm run check:release-readiness` (local degraded mode allowed)
   - `pnpm run check:release-readiness:strict` in CI before release tags
   - `pnpm run check:live-chain` (optional local; requires Turnkey + testnet credentials)

## 2) Developer Setup (Partner Side)

1. Bootstrap MCP:
   - Recommended one-click identity:
     - `POST /api/v2/agents/{agent_id}/payment-identity`
     - then:
       `npx @sardis/mcp-server init --mode live --api-url <staging-url> --api-key <partner-key> --payment-identity <identity-id>`
   - `npx @sardis/mcp-server init --mode simulated`
   - or live staging:
     `npx @sardis/mcp-server init --mode live --api-url <staging-url> --api-key <partner-key>`
2. Verify generated `.env.sardis`:
   - `SARDIS_API_URL`
   - `SARDIS_MODE`
   - `SARDIS_AGENT_ID`
   - `SARDIS_WALLET_ID`
3. Start MCP server:
   - `npx @sardis/mcp-server start`
4. Run smoke calls:
   - allowed payment (within limits)
   - blocked payment (merchant/category/limit deny)
   - above-threshold payment (must return approval-required path)
   - verify deterministic `reason_code` + `decision` envelope in MCP JSON response

## 3) CFO / FinOps Policy Flow

1. Parse policy from natural language (`/api/v2/policies/parse`).
2. Preview compiled result (`/api/v2/policies/preview`).
3. Apply policy with confirmation (`/api/v2/policies/apply`).
4. Validate behavior with dry checks (`/api/v2/policies/check`).
5. Above-threshold amounts should produce `approval_required` semantics and create approval requests.

## 4) Approval Workflow

1. AP2 execute path may return `approval_required`.
2. Retrieve pending approval (`/api/v2/approvals`).
3. Approver resolves via:
   - `POST /api/v2/approvals/{id}/approve`, or
   - `POST /api/v2/approvals/{id}/deny`
4. Agent retries payment after approval.

## 5) Release Packaging

1. Python SDK:
   - version sync in `pyproject.toml` + `src/sardis_sdk/__init__.py`
   - tests: `packages/sardis-sdk-python/tests`
   - build and twine check when tools available
2. NPM packages:
   - `@sardis/mcp-server`
   - `@sardis/sdk`
   - `@sardis/ai-sdk`
   - validate with `npm pack --dry-run` after build
3. GitHub release workflows:
   - `.github/workflows/release-npm.yml`
   - `.github/workflows/release-python-sdk.yml`

## 6) Minimum Engineering Exit Gates

1. Policy parsing + enforcement deterministic for limit/merchant/approval.
2. MCP payment + policy outputs include deterministic `reason_code` and decision envelope fields.
3. AP2 approval-required path creates approval records.
4. Python SDK tests are green.
5. Protocol smoke negatives are green:
   - AP2 malformed payload rejection
   - AP2 merchant-domain binding checks
   - TAP signature-input/tag/timestamp/nonce checks
   - payment method parsing (stablecoin/card/x402/bank)
6. MCP `init` flow works even in constrained local environments.
7. Protocol source mapping is updated against canonical links:
   - `docs/release/protocol-source-map.md`
