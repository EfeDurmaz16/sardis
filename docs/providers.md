# Provider Layer — Environment Variables & Status

Every external money/identity service is reached through a typed **capability
port** (`apps/api/server/providers/ports`) resolved by `ProviderRegistry`. Each
provider is **env-gated**: it activates only when its keys below are set;
otherwise a `SIMULATED` sandbox impl backs the capability so dev/test run green
without live keys. Required capabilities (`CUSTODY`, `KYT`) **fail closed** in
production when unconfigured.

- Adapters **execute** only what the orchestrator already authorized — they
  never authorize, initiate, or settle money on their own.
- Runtime capability matrix: `GET /api/v2/providers/matrix`.
- All keys are **server-only secrets** unless marked `(config/public)`.
- See `.env.example` for a copy-paste block; the canonical env names live in
  `ProviderRegistry.from_settings` (`apps/api/server/providers/registry.py`).

## Live-capable vs sandbox-only today

"Live-capable" = an adapter that talks to the real provider when its keys are
set. "Sandbox-only today" = no real adapter yet (only the `SIMULATED` impl). The
column reflects code in this branch, not whether *we* have a contract/keys.

| Capability    | Provider          | Status        | custody_model       | Where to get keys |
|---------------|-------------------|---------------|---------------------|-------------------|
| custody       | Turnkey (MPC)     | live-capable  | NON_CUSTODIAL       | app.turnkey.com → API Keys |
| fiat_account  | Dakota            | live-capable  | PARTNER_CUSTODIED   | dakota.xyz dashboard |
| fiat_account  | Increase          | live-capable  | PARTNER_CUSTODIED   | dashboard.increase.com |
| fiat_account  | Lithic            | live-capable  | PARTNER_CUSTODIED   | dashboard.lithic.com |
| onramp        | Conduit           | live-capable  | PARTNER_CUSTODIED   | conduit.financial |
| onramp        | Turnkey native    | live-capable  | NON_CUSTODIAL       | app.turnkey.com (widget providers pre-uploaded) |
| onramp        | Onramper          | live-capable  | PARTNER_CUSTODIED   | onramper.com dashboard |
| onramp        | Transak           | live-capable  | PARTNER_CUSTODIED   | dashboard.transak.com |
| onramp        | Daimo Pay         | live-capable  | PARTNER_CUSTODIED   | pay.daimo.com |
| offramp       | Circle CPN        | live-capable  | PARTNER_CUSTODIED   | Circle CPN program (SardisSettings.circle_cpn) |
| offramp       | Increase          | live-capable  | PARTNER_CUSTODIED   | dashboard.increase.com |
| offramp       | Onramper          | live-capable  | PARTNER_CUSTODIED   | onramper.com dashboard |
| offramp       | Transak Stream    | live-capable  | PARTNER_CUSTODIED   | dashboard.transak.com |
| offramp       | Coinbase Offramp  | live-capable  | PARTNER_CUSTODIED   | portal.cdp.coinbase.com |
| swap          | LI.FI             | live-capable  | NON_CUSTODIAL       | li.fi portal (keyless-capable) |
| swap          | 0x v2             | live-capable  | NON_CUSTODIAL       | dashboard.0x.org |
| swap          | Jupiter           | live-capable  | NON_CUSTODIAL       | station.jup.ag (keyless-capable) |
| bridge        | Squid             | live-capable  | NON_CUSTODIAL       | app.squidrouter.com (integrator id) |
| bridge        | CCTP v2           | live-capable  | NON_CUSTODIAL       | keyless (public Circle Iris); opt-in via flag |
| card          | Crossmint         | live-capable  | PARTNER_CUSTODIED   | crossmint.com console (+ Rain key) |
| card          | Lithic            | live-capable  | PARTNER_CUSTODIED   | dashboard.lithic.com |
| card          | Stripe Issuing    | live-capable  | PARTNER_CUSTODIED   | dashboard.stripe.com |
| kyc           | Didit             | live-capable  | PARTNER_CUSTODIED   | business.didit.me |
| kyt           | OpenSanctions     | live-capable  | PARTNER_CUSTODIED   | opensanctions.org/api |
| kyt           | Didit (fallback)  | live-capable  | PARTNER_CUSTODIED   | business.didit.me |
| notification  | Twilio            | live-capable  | NON_CUSTODIAL       | console.twilio.com (Verify + Messaging) |
| notification  | Photon/Spectrum   | live-capable* | NON_CUSTODIAL       | photon.codes (needs Node sidecar — see below) |

Selection within a capability is **first-configured-wins**, in the precedence
order the registry tries them (see `_build_*` methods). Sandbox (`SIMULATED`)
backs any capability whose providers are all unconfigured.

## Env vars by capability

### CUSTODY (required-in-production)
- `TURNKEY_API_PUBLIC_KEY`, `TURNKEY_API_PRIVATE_KEY`, `TURNKEY_ORGANIZATION_ID`

### FIAT ACCOUNTS
- Dakota: `DAKOTA_API_KEY`, `DAKOTA_ENVIRONMENT` (config), `DAKOTA_WEBHOOK_PUBLIC_KEY`
- Increase: `INCREASE_API_KEY`, `INCREASE_ENVIRONMENT` (config), `INCREASE_WEBHOOK_SECRET`
- Lithic: `LITHIC_API_KEY`, `LITHIC_WEBHOOK_SECRET`, `LITHIC_ENVIRONMENT` (config)

### ONRAMP
- Conduit: `CONDUIT_API_KEY`, `CONDUIT_API_SECRET`, `CONDUIT_SANDBOX` (config)
- Turnkey native: reuses the CUSTODY Turnkey keys
- Onramper: `ONRAMPER_API_KEY`, `ONRAMPER_SIGNING_SECRET`, `ONRAMPER_ENVIRONMENT` (config)
- Transak: `TRANSAK_API_KEY`, `TRANSAK_API_SECRET`, `TRANSAK_ENVIRONMENT` (config), `TRANSAK_REFERRER_DOMAIN` (config/public)
- Daimo: `DAIMO_PAY_API_KEY` (or `DAIMO_API_KEY`), `DAIMO_ENVIRONMENT` (config)

### OFFRAMP
- Circle CPN: via `SardisSettings.circle_cpn` (`CIRCLE_CPN_*`)
- Onramper: reuses `ONRAMPER_API_KEY`
- Transak Stream: `TRANSAK_STREAM_API_KEY` (or `TRANSAK_API_KEY`), `TRANSAK_PARTNER_ID` (config)
- Coinbase Offramp: `COINBASE_CDP_API_KEY_NAME`, `COINBASE_CDP_API_KEY_PRIVATE`, `COINBASE_OFFRAMP_ENVIRONMENT` (config)
- Increase: reuses `INCREASE_API_KEY`

### SWAP
- LI.FI: `LIFI_API_KEY` (optional), `LIFI_ENABLED` (config), `LIFI_INTEGRATOR` (config), `LIFI_FEE` (config), `LIFI_ENVIRONMENT` (config)
- 0x: `ZEROX_API_KEY` (or `ZERO_EX_API_KEY`), `ZEROX_SWAP_FEE_BPS` (config), `ZEROX_SWAP_FEE_RECIPIENT` (config), `ZEROX_ENVIRONMENT` (config)
- Jupiter: `JUPITER_API_KEY` (optional), `JUPITER_ENABLED` (config), `JUPITER_PLATFORM_FEE_BPS` (config), `JUPITER_FEE_ACCOUNT` (config)

### BRIDGE
- Squid: `SQUID_INTEGRATOR_ID`, `SQUID_ENVIRONMENT` (config), `SQUID_SLIPPAGE_PERCENT` (config)
- CCTP v2: `CCTP_ENABLED` (config, opt-in), `CCTP_FAST` (config), `CCTP_ENVIRONMENT` (config) — keyless

### CARDS
- Crossmint: `CROSSMINT_API_KEY`, `CROSSMINT_RAIN_API_KEY` (or `RAIN_API_KEY`), `CROSSMINT_ENVIRONMENT` (config)
- Lithic: reuses `LITHIC_API_KEY`, `LITHIC_ENVIRONMENT` (config)
- Stripe Issuing: `STRIPE_ISSUING_API_KEY` (or `STRIPE_SECRET_KEY`), `STRIPE_ISSUING_ENVIRONMENT` (config)

### KYC / KYB
- Didit: `DIDIT_API_KEY`, `DIDIT_KYC_WORKFLOW_ID` (or `DIDIT_WORKFLOW_ID`), `DIDIT_KYB_WORKFLOW_ID`, `DIDIT_WEBHOOK_SECRET`, `DIDIT_CALLBACK_URL` (config/public), `DIDIT_ENVIRONMENT` (config)

### KYT / AML (required-in-production)
- OpenSanctions: `OPENSANCTIONS_API_KEY`, `OPENSANCTIONS_SCOPE` (config), `OPENSANCTIONS_ALGORITHM` (config), `OPENSANCTIONS_THRESHOLD` (config), `OPENSANCTIONS_ENVIRONMENT` (config)
- Didit KYT (fallback): reuses `DIDIT_API_KEY`

### NOTIFICATION (human-in-the-loop approval delivery — delivery only, never decides)
First-configured-wins: Twilio, then Photon/Spectrum. Unconfigured ⇒ `SIMULATED`
sandbox impl (logs the approval, auto-resolvable in tests). **Not**
required-in-production — a missing notifier degrades to dashboard-only approval,
not a blocked money path.
- Twilio: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (or `TWILIO_MESSAGING_SERVICE_SID`), `TWILIO_VERIFY_SERVICE_SID` (OTP step-up for high-value approvals)
- Photon/Spectrum: `PHOTON_RELAY_URL` (or `SPECTRUM_RELAY_URL`), `PHOTON_RELAY_SECRET` (or `SPECTRUM_RELAY_SECRET`), and optionally `PHOTON_PROJECT_ID` / `PHOTON_PROJECT_SECRET` (Spectrum Cloud control-plane creds the sidecar forwards). `RELAY_URL`+`RELAY_SECRET` are required to wire it.

#### Photon/Spectrum integration path (researched May 2026)
Spectrum's **message-send** surface — including the `poll()` interactive builder
that renders the **Approve / Deny** choice — exists **only in the TypeScript SDK**
`spectrum-ts` (`Spectrum({ projectId, projectSecret })` → `space.send(poll(…))`;
github.com/photon-hq/spectrum-ts, photon.codes/docs/spectrum-ts/content). The
hosted **Spectrum Cloud REST API** (`spectrum.photon.codes/openapi/json`, Basic
`base64(projectId:projectSecret)`) is a **control plane only** (projects / lines /
platforms / users / webhooks) — it has **no message-send endpoint**. Inbound
human decisions arrive as **webhooks** (HTTP POST, HMAC-SHA256-signed); a button
press is a `poll_option` content event (photon.codes/docs/webhooks/events).

Therefore the lowest-friction correct path from Python is a **thin Node sidecar**
(or the existing sardis-cloud TS surface) that owns `spectrum-ts`. Sardis builds
the agent-native interactive payload in Python (`PhotonRelayNotificationAdapter.
build_interactive_payload` → `{text, interactive:{kind:"poll", options:["Approve",
"Deny"], callback_id}}`), HMAC-signs it, and POSTs it to the sidecar; the sidecar
runs `space.send(poll(…))`. The press returns as a `poll_option` webhook → the
sidecar (or Spectrum) forwards it HMAC-signed → Sardis verifies the signature and
calls `record_decision`. Sardis owns the decision/policy/evidence; Spectrum is
swappable delivery. **`*live-capable` is gated on the Node sidecar** — the Python
adapter is complete and tested against a mock sidecar; the sidecar itself is a
documented follow-up (scaffold below), not half-built.

Minimal sidecar contract (follow-up to scaffold):
- `POST {PHOTON_RELAY_URL}/approvals/send` — body is the adapter's signed JSON
  (`approval_id`, `message.interactive` poll, `channels`, `project_id`); headers
  `x-sardis-signature` (HMAC-SHA256 of the raw body) and `x-spectrum-authorization`
  (Basic creds to forward). Sidecar verifies the HMAC, then
  `space.send(poll(question, "Approve", "Deny"))`. Returns `{job_id}`.
- Inbound: sidecar receives the Spectrum `poll_option` webhook, re-signs the
  decision (`{callback_id, option, from}`) with the shared secret, and POSTs it to
  Sardis's inbound approval-decision route. Sardis verifies via
  `verify_relay_signature`, maps the option with `decision_from_poll_option`, and
  calls `record_decision(proof={"relay_verified": True, …})`. An unsigned/forged
  decision fails closed.
