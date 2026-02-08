# Demo Launch Readiness (Landing + Docs + /demo)

Use this checklist before sharing Sardis publicly on X/Reddit or sending demo links to VCs/design partners.

## 1) Mandatory Technical Gates

1. Landing build passes:
   - `pnpm --dir landing build`
2. `/demo` simulated mode works:
   - blocked and approved flows both run
3. `/demo` live mode is protected:
   - requires operator password
   - no API key is exposed to browser
4. Server-side demo routes are available:
   - `/api/demo-auth`
   - `/api/demo-proxy`
   - `/api/demo-events`

## 2) Environment Variables (Landing Deployment)

Required:

- `SARDIS_API_URL`
- `SARDIS_API_KEY`
- `DEMO_OPERATOR_PASSWORD`

Optional:

- `DEMO_LIVE_AGENT_ID`
- `DEMO_LIVE_CARD_ID`
- `DATABASE_URL` (Neon for demo event telemetry)

## 3) One-Command Post-Deploy Smoke Test

```bash
LANDING_BASE_URL="https://sardis.sh" \
DEMO_OPERATOR_PASSWORD="<shared-password>" \
bash ./scripts/check_demo_deploy_readiness.sh
```

If you require demo telemetry storage to be active:

```bash
LANDING_BASE_URL="https://sardis.sh" \
DEMO_OPERATOR_PASSWORD="<shared-password>" \
EXPECT_DEMO_EVENTS=1 \
bash ./scripts/check_demo_deploy_readiness.sh
```

## 4) Public Sharing Safety Checks

1. `/demo` page does not show internal credentials or operator-only instructions.
2. Live mode is locked by default for public visitors.
3. Investor/operator details are kept only in:
   - `docs/release/investor-demo-operator-kit.md`
4. All screenshots/videos use either:
   - simulated mode, or
   - live mode with sanitized values.

## 5) Go / No-Go

Go when all are true:

- Build passes.
- Smoke script passes.
- Live mode gate confirmed.
- No sensitive content in public demo/docs.

No-Go when any of these fail:

- `/api/demo-auth` or `/api/demo-proxy` unavailable.
- Live mode unlocked without password.
- Public page contains operational secrets or internal playbooks.
