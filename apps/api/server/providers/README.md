# Provider Layer

Every external money/identity service in Sardis sits behind a **typed capability
port**. The orchestrator and execution routes talk only to these ports — never
to a vendor SDK directly — so the authority core (the "moat" from #396) is never
bypassed. Adapters **execute** what the orchestrator already authorized; they do
not authorize, initiate, or settle money on their own.

## Port taxonomy

`ports/capabilities.py` defines one `Protocol` per class of provider. Each port
exposes `provider`, `capability`, `custody_model`, and `sandbox`.

| Capability    | Port              | What it does                                         |
|---------------|-------------------|------------------------------------------------------|
| `custody`     | `CustodyPort`     | Derive address / sign an already-authorized payload  |
| `fiat_account`| `FiatAccountPort` | Bank-rail USD account + ACH/wire/RTP/FedNow payout   |
| `onramp`      | `OnrampPort`      | Fiat -> crypto session (user funds it)               |
| `offramp`     | `OfframpPort`     | Crypto -> fiat payout to a bank                       |
| `swap`        | `SwapPort`        | Same-chain / cross-token quote + executable tx       |
| `bridge`      | `BridgePort`      | Cross-chain quote + executable messages              |
| `card`        | `CardPort`        | Virtual card issue + state/limit controls            |
| `kyc`         | `KycPort`         | KYC/KYB identity verification session                |
| `kyt`         | `KytPort`         | AML / address screening — **reports** a verdict only |
| `notification`| `NotificationPort`| Human-in-the-loop approval delivery — delivery only  |
| `fraud_signal`| `FraudSignalPort` | External fraud signal — **contributes a score** only |

Money crosses every port boundary as integer **minor units** (`MinorUnits`) or
`Decimal` — never `float`. Use `to_minor_units` / `from_minor_units` in
`ports/types.py`.

## custody_model per adapter

Every adapter declares an explicit `CustodyModel` so the audit trail can answer
"who held funds at this hop?".

| Capability    | Provider(s)                              | custody_model        |
|---------------|------------------------------------------|----------------------|
| custody       | Turnkey (MPC)                            | `NON_CUSTODIAL`      |
| fiat_account  | Lithic / Dakota / Increase              | `PARTNER_CUSTODIED`  |
| onramp        | Conduit / Onramper / Transak / Daimo    | `PARTNER_CUSTODIED`  |
| onramp        | Turnkey native widget                    | `NON_CUSTODIAL`      |
| offramp       | Circle CPN / Increase / Onramper / Transak Stream / Coinbase | `PARTNER_CUSTODIED` |
| swap          | LI.FI / 0x / Jupiter                     | `NON_CUSTODIAL`      |
| bridge        | Squid / CCTP v2                          | `NON_CUSTODIAL`      |
| card          | Crossmint / Lithic / Stripe Issuing     | `PARTNER_CUSTODIED`  |
| kyc           | Didit                                    | `PARTNER_CUSTODIED`  |
| kyt           | OpenSanctions / Didit                    | `PARTNER_CUSTODIED`  |
| notification  | Twilio / Photon-Spectrum                 | `SIMULATED`          |
| fraud_signal  | SEON / Stripe Radar                      | `SIMULATED`          |
| *sandbox*     | every capability                         | `SIMULATED`          |

## Env-gated + sandbox-fallback model

`ProviderRegistry.from_settings()` is the single place that decides which impl
backs each port:

1. **Env-gated** — a real provider activates only when its keys are set (see
   `docs/providers.md` / `.env.example` for the full list).
2. **Sandbox fallback (dev/test only)** — when a capability's real provider is
   not configured, the registry returns a `SIMULATED` sandbox impl so the suite
   and local dev run green without live keys. Sandbox results always carry
   `sandbox=True` and `custody_model=SIMULATED`.
3. **Fail-closed in production** — in production, asking for a *required*
   capability (`CUSTODY`, `KYT`) with no configured provider raises
   `ProviderNotConfigured` rather than silently handing back a simulated impl on
   a money path.

The registry owns the httpx lifecycle of the clients it builds; `aclose()`
closes them (wired into the app lifespan shutdown).

## How to add a new provider

1. **Research first** (mandatory): pull the current API (auth, endpoints,
   sandbox, webhooks) via WebSearch + context7. Do not code from memory.
2. Create `<capability>/client.py` (thin httpx client, no behavior change) and
   `<capability>/adapter.py` implementing the capability `Protocol`. Set
   `custody_model` explicitly. Money in minor units / `Decimal`.
3. Export the client + adapter + config from `<capability>/__init__.py`.
4. Wire it into `ProviderRegistry._build_<capability>(...)`: env-gate on its key,
   `owned.append(client)`, fill the capability slot (respect precedence — first
   configured wins, higher-priority providers keep the slot).
5. Add its env vars to `.env.example` and `docs/providers.md`.
6. Add a registry test (real-when-keyed, sandbox-when-absent) and an adapter
   normalization test. Run the gate (`pytest apps/api/tests packages/sardis/tests`
   + `ruff check`).

## Reachability

- Routes resolve a port via the FastAPI dependencies in `server.dependencies`
  (`get_custody_port`, `get_onramp_port`, … `get_kyt_port`), all backed by the
  one `ProviderRegistry` instance on the container.
- Introspect at runtime: `GET /api/v2/providers/matrix`.

## Guard — risk decision vs. signal feeds

The `fraud_signal` capability is special: unlike a money-moving port, a
`FraudSignalPort` only **contributes a score** — it never decides. The in-house
`RiskEngine` (`sardis.guardrails.risk_engine`) owns the decision (the moat):

- **Signals.** The engine reuses the behavioral `AnomalyEngine` (amount-vs-budget
  deviation, velocity spikes, new-counterparty, off-pattern time/geo,
  compromised/rogue-agent alerts) for the internal 0-100 score, and folds in
  **every** configured external feed via `registry.fraud_signal_feeds()` — SEON
  (device/email/IP/phone intelligence) and Stripe Radar (network risk on
  Stripe-processed card legs). Both are combined when both are keyed; the
  external contribution is the **max** across feeds (a confident decline is not
  diluted by an abstaining feed).
- **Assessment.** Internal + external blend into one `combined_score` (internal
  leads at weight 0.6; floored at the internal score and at the block threshold
  when an external feed is near-certain).
- **Action.** The orchestrator consults the engine pre-dispatch on every
  money-moving execution and acts on the binding `GuardAction`:
  `< 30` ALLOW · `30-59` FLAG (allow + record) · `60-84` REQUIRE_APPROVAL (route
  to the `ApprovalGate` / step-up) · `>= 85` BLOCK (deny, fail-closed — no
  dispatch). A feed that errors on a high-value tx (`>= 1000`) escalates to
  REQUIRE_APPROVAL rather than failing open.
- **Read surface.** `GET /api/v2/agents/{agent_id}/risk-signals` returns the
  recent decisions (newest first) for the dashboard / Guard view.
- **Needs live keys.** `SEON_API_KEY` and/or `STRIPE_RADAR_API_KEY`
  (or `STRIPE_SECRET_KEY`) — see `.env.example`. With no keys the engine runs
  internal-only (dev/tests never fail open).
