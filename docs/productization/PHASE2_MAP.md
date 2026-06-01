# Phase 2 — Persistence Consolidation MAP (READ-ONLY survey)

**Branch:** `feat/persistence-rebuild` · **Worktree:** `/Users/efebarandurmaz/sardis-phase2`
**Date:** 2026-06-01 · **Author:** MAP engineer (no code changes this phase)
**Test baseline:** `uv run pytest apps/api/tests packages/sardis/tests -q` → **3032 passed, 15 skipped, 0 failed** (106s). The 15 skips are the pre-existing ledger / Facility-Gate Postgres-DSN-gated tests (`SARDIS_TEST_POSTGRES_DSN` / `POSTGRES_TEST_DSN` unset) — unrelated to this work. This is the green bar to hold at every step.

---

## 0. Executive summary

There is **not** a 60-table "shadow data layer" megaclass. The reality is more nuanced and the dossier framing should be corrected:

- `packages/sardis/src/sardis/core/database.py` (1240 LOC) is a **shared connection/query primitive** — `Database.fetch/execute/fetchrow/transaction`, read/write pool split, `LazyPool`. It is imported by **120 sites** (SDK core, SDK subpackages, AND apps/api routes/repositories). It is the de-facto single DB connection seam and is **not** dead and **not** a repository. Keep it. It is the one thing already consolidated.
- What is *actually* fragmented is **hand-written raw SQL with no shared typed model**, scattered across:
  - **43** SDK-core files under `packages/sardis/src/sardis/core/*` containing raw SQL,
  - **9** repository files under `apps/api/server/repositories/*`,
  - **653 inline Pydantic models** across **109** route files under `apps/api/server/routes/*`,
  - plus writes embedded directly in route handlers (not in repositories).
- Two parallel **model** layers exist: `packages/sardis/src/sardis/models/*` (public-SDK DTOs, `SardisModel`) and `packages/sardis/src/sardis/core/*` (engine domain types, `BaseModel`/`@dataclass`). They serve **different consumers** (SDK client vs orchestrator engine), so the Agent/Wallet duplication is a DTO-vs-domain split, **not** dead duplication. Consolidating them is medium-risk, not a quick win.
- **Real dual-persistence overlap** (same table written from BOTH SDK-core AND apps/api): a short, concrete list (Section 2). The money-path-critical ones — `spending_mandates`, `payment_objects`, `payment_state_transitions`, `wallets` — are written from both layers at **different lifecycle phases** with no single owner. These are the risky items; **defer / stage carefully**, do not rewrite.
- **Migration situation:** the `apps/api/migrations/*.sql` chain (113 files, head **111**) is **authoritative** (applied by `scripts/run_migrations.sh` via a `schema_migrations` version table). The `apps/api/alembic/` tree (30 versions, head **030**, diverged naming) is **stale/dead** — it stops at 030, diverges from the SQL chain, and is not wired into CI or the runtime path. `scripts/release/migration_alignment_check.sh` would **FAIL today** (head mismatch sql=111 vs alembic=030; missing alembic revs 031–111) but is **not invoked by CI** (no reference in `.github/`).
- **102 collision is a real latent bug** (Section 5): `102_idempotency_request_hash.sql` and `102_stripe_connect.sql` both parse to version `102` in the runner; alphabetical glob applies `idempotency` first, marks version `102` applied, and **silently SKIPS `stripe_connect`**. Repo-level fix (renumber) is a clearly-safe quick win.

---

## 1. Persistence-site inventory

### 1.1 The shared primitive (keep as-is)
| File | Role |
|---|---|
| `packages/sardis/src/sardis/core/database.py` (1240 LOC) | `Database` class: pooled `execute/fetch/fetchrow/fetchval/transaction` + read-pool split; `LazyPool`, `init_database`, `get_db_pool`, `get_database`. 120 importers. **The one shared seam.** |

### 1.2 apps/api/server/repositories/* (9 raw-SQL repos)
| File | LOC | Tables read/written |
|---|---|---|
| `a2a_trust_repository.py` | 195 | `a2a_trust_relations` (+ `information_schema` introspection) |
| `canonical_ledger_repository.py` | 894 | `canonical_ledger_events`, `canonical_ledger_journeys`, `manual_review_queue`, `reconciliation_breaks` |
| `card_repository.py` | 443 | `virtual_cards`, `card_transactions`, `agents`, `wallets`, `organizations` |
| `enterprise_support_repository.py` | 417 | `enterprise_support_tickets` |
| `facility_gate_repository.py` | 915 | `facility_records`, `facility_request_states`, `facility_mandate_records`, `facility_policy_records`, `facility_events` |
| `mpp_session_repository.py` | 204 | `mpp_sessions`, `mpp_payments` |
| `secure_checkout_job_repository.py` | 211 | `secure_checkout_jobs` |
| `subscriptions_repository.py` | 424 | `subscriptions`, `billing_events` |
| `treasury_repository.py` | 1330 | `treasury_balance_snapshots`, `treasury_reservations`, `treasury_webhook_events`, `ach_payments`, `ach_payment_events`, `external_bank_accounts`, `issuer_funding_attempts`, `issuer_funding_audit`, `lithic_financial_accounts` |

**Observation:** these 9 repos own **disjoint** table sets (facility_*, treasury_*/ach_*, mpp_*, canonical_ledger_*, enterprise_support_*, secure_checkout_jobs) EXCEPT `card_repository.py` and `subscriptions_repository.py`, which touch tables (`agents`, `wallets`, `organizations`, `subscriptions`, `billing_events`) also written elsewhere — see Section 2.

### 1.3 packages/sardis/src/sardis/core/* (43 raw-SQL sites — tables they touch)
*(SQL-string scan; obvious importer/comment noise filtered. Bold = money-path.)*

| File | Tables written/read |
|---|---|
| `a2a_escrow.py` | `escrows` |
| `a2a_settlement.py` | **`settlements`**, **`ledger_entries_v2`**, `escrow` |
| `agent_repository_postgres.py` | `agents`, `organizations`, `wallets` |
| `approval_repository.py` | `approvals` |
| `approval_request_repository.py` | `approval_requests` |
| `cell_claim.py` | `funding_cells` |
| `credential_store.py` | `delegated_credentials` |
| `data_retention.py` | `access_audit_log`, `data_classification`, `data_retention_log`, `tenant_data_deletions`, `tenant_data_exports` |
| `delegation_consent.py` | `delegation_consents` |
| `delegation_repository.py` | `delegations` |
| `dispute.py` | `disputes`, `dispute_evidence`, `dispute_resolutions` |
| `erc8183_job.py` | `erc8183_jobs`, `erc8183_evaluations` |
| `escrow.py` | **`escrow_holds`** |
| `execution_queue.py` | `execution_side_effects` |
| `holds.py` | **`holds`** |
| `hooks/mandate_hook.py` | **`spending_mandates`** (spend accumulation: `spent_total += $1`) |
| `identity.py` | `identity_records` |
| `inbound_payment_service.py` | **`deposits`, `invoices`, `payment_requests`, `ledger_entries_v2`**, `agents`, `wallets` |
| `jobs/approval_expiry.py` | `approvals` |
| `jobs/hold_expiry.py` | **`holds`** |
| `jobs/payment_expiry.py` | **`payment_objects`, `payment_state_transitions`, `spending_mandates`, `escrow_holds`, `disputes`** |
| `jobs/spending_reset.py` | **`wallets`** (spending counter reset) |
| `marketplace.py` | `marketplace_services`, `marketplace_offers`, `marketplace_reviews` |
| `merchant.py` | `merchants`, `merchant_checkout_sessions`, `merchant_checkout_links`, `merchant_webhook_deliveries`, `organizations` |
| `merchant_capability.py` | `merchant_capabilities` |
| `merchant_trust.py` | `merchant_trust_profiles` |
| `notification_service.py` | `notification_configs`, `notification_delivery_log` |
| `organizations.py` | `organizations`, `org_members`, `teams`, `team_tree`, `user_orgs`, `spending_policy_state`, `ledger_entries` |
| `policy_store_postgres.py` | **`spending_policies`, `spending_velocity`**, `agents` |
| `policy_version_store.py` | `policy_versions` |
| `rbac.py` | `custom_roles`, `resource_permissions` |
| `receipt_store.py` | `execution_receipts` |
| `reconciliation_queue_postgres.py` | `reconciliation_queue` |
| `recourse_hold_repository.py` | **`recourse_holds`** |
| `refund.py` | **`refunds`, `payments`** |
| `revocation_ports.py` | **`spending_mandates`, `mandate_state_transitions`, `payment_objects`** |
| `revocation_repository.py` | `revocations` |
| `settlement.py` | **`settlement_records`** |
| `spending_mandate_lookup.py` | **`spending_mandates`** |
| `spending_policy_store.py` | **`spending_policies`, `spending_velocity`, `time_window_limits`** |
| `wallet_repository_postgres.py` | **`wallets`**, `agents`, `organizations` |
| `webhooks.py` | `webhook_subscriptions`, `webhook_deliveries`, `webhook_outbox`, `payments`, `subscription` |
| `workflows/scheduled_jobs.py` | **`holds`, `replay_cache`, `time_window_limits`** |

### 1.4 Writes embedded directly in route handlers (not in repositories)
`apps/api/server/routes/*` issue raw SQL writes directly (not via a repo), e.g. `money_movement/payment_objects.py`, `*/spending_mandates.py`, `wallets/lifecycle.py`, `wallets/emergency.py`, `accounts/auth.py`, `accounts/organizations.py`, `commerce/merchants.py`, `commerce/merchant_checkout.py`, `identity/agent_auth.py`, `authority/mandate_delegation.py`. These are the source of most of the Section-2 overlap.

### 1.5 The two model layers
| Layer | Base | Consumer | Importers (non-self) |
|---|---|---|---|
| `packages/sardis/src/sardis/models/*` (agent, wallet, payment, card, group, hold, marketplace, policy, treasury, webhook, base, errors) | `SardisModel` | **Public SDK client** (`sardis/resources/*`, `sardis/cards/*`, `sardis/ledger/*`) | 0 from core, ~19 from SDK subpackages |
| `packages/sardis/src/sardis/core/*` (agents, wallets, mandates, transactions, spending_mandate, payment_object, …) | `BaseModel` / `@dataclass` | **Engine / orchestrator / apps-api routes** | high |

---

## 2. Dual-persistence overlap table (tables written by BOTH layers)

Method: stricter INSERT/UPDATE/DELETE scan over `core/*` vs `apps/api/{repositories,services,routes}/*`; fragments resolved against source. Verified entries only:

| Table | SDK-core writers | apps/api writers | Same op? | Money-path? | Verdict |
|---|---|---|---|---|---|
| **`spending_mandates`** | `hooks/mandate_hook.py` (spend accrual `spent_total+=`), `revocation_ports.py` (revoke), `spending_mandate_lookup.py` (status), `jobs/payment_expiry.py` (expiry) | route `spending_mandates.py` (INSERT/create + revoke/status), `agent_auth.py`, `mandate_delegation.py`, `merchant_checkout.py` | **No — different lifecycle phases, no single owner** | **YES (authority over money)** | **RISKY — defer / careful staged** |
| **`payment_objects`** | `jobs/payment_expiry.py` (expire), `revocation_ports.py` (revoke) | route `payment_objects.py` (INSERT/create + expire + transitions) | No — create in route, expire/revoke in core jobs | **YES** | **RISKY — defer / careful staged** |
| **`payment_state_transitions`** | `jobs/payment_expiry.py` | route `payment_objects.py` | No — both append transition rows from different triggers | **YES** | **RISKY — defer** |
| **`mandate_state_transitions`** | `revocation_ports.py` | route `spending_mandates.py` | No — append-only audit of transitions, dual triggers | **YES** | **RISKY — defer** |
| **`wallets`** | `wallet_repository_postgres.py` (create/update), `jobs/spending_reset.py` (counter reset) | route `wallets/emergency.py` (freeze), `wallets/lifecycle.py` | No — repo owns CRUD; emergency/reset are side writes | **YES (freeze/funds)** | **RISKY — defer** |
| **`organizations`** | `organizations.py` (full schema: slug/plan/billing_email), `agent_repository_postgres.py` (thin `external_id,name,settings`) | route `accounts/auth.py` (thin `external_id,name,settings`), `accounts/organizations.py` | No — **three different insert shapes** for one table | No (control-plane) | **MEDIUM — consolidate org provisioning** |
| `org_members` / `teams` / `team_tree` | `organizations.py` | route `accounts/organizations.py` | Overlapping membership ops | No | MEDIUM |
| `agents` | `agent_repository_postgres.py`, `policy_store_postgres.py` | route `agents/lifecycle.py`, `agent_events.py`, `agent_heartbeat.py` | No — repo CRUD vs event/heartbeat side writes | No (identity, not money) | MEDIUM |
| `invoices` / `payment_requests` | `inbound_payment_service.py` | route `invoices.py`, `lifecycle.py` | Partial | borderline | MEDIUM |
| `funding_cells` | `cell_claim.py` | route `funding.py` | No — claim (core) vs provision (route) | borderline | MEDIUM |
| `notification_configs` | `notification_service.py` | route `notifications.py` | Overlapping config CRUD | No | LOW |
| `delegated_credentials` | `credential_store.py` | route `visa_tap_webhooks.py` | No — store vs webhook update | No | LOW |
| `erc8183_jobs` / `erc8183_evaluations` | `erc8183_job.py` | route `erc8183.py` | Overlapping | borderline | LOW |
| `merchants` | `merchant.py`, `outcome_tracker.py`, `policy_explainer.py` | route `merchants.py` | merchant CRUD vs trust-profile reads/writes | No | LOW |
| `subscriptions` / `billing_events` | `webhooks.py` (subscription), core | repo `subscriptions_repository.py`, service `stripe_billing.py` | No — repo is canonical; webhook updates status | borderline | MEDIUM |
| `counters` | `analytics.py`, `dispute.py` | route `control.py` | Metrics counters | No | LOW |
| `approvals` / `approval_requests` | `approval_repository.py`, `jobs/approval_expiry.py` | route `metrics.py` (read) | Read vs write | No | LOW |

**Tables owned by exactly one layer (no overlap, no action):** all `facility_*`, all `treasury_*`/`ach_*`/`issuer_funding_*`/`lithic_*`, `mpp_*`, `canonical_ledger_*`/`reconciliation_breaks`/`manual_review_queue`, `enterprise_support_tickets`, `secure_checkout_jobs`, `a2a_trust_relations` (apps/api-only); `escrow_holds`/`holds`, `disputes`/`dispute_*`, `marketplace_*`, `identity_records`, `revocations`, `delegations`/`delegation_consents`, `recourse_holds`, `settlement_records`/`settlements`, `data_*`/`tenant_data_*`, `rbac`/`custom_roles`/`resource_permissions`, `policy_versions`, `execution_receipts`/`execution_side_effects`, `reconciliation_queue`, `webhook_*`, `spending_policies`/`spending_velocity`/`time_window_limits` (SDK-core-only).

---

## 3. Duplicate domain models

| Model | Public-SDK def (`models/`) | Engine def (`core/`) | Canonical | Notes |
|---|---|---|---|---|
| **Agent** | `models/agent.py` `Agent(SardisModel)` + `CreateAgentRequest`/`AgentCreate`/`AgentUpdate` | `core/agents.py` `Agent(BaseModel)` + `SpendingLimits`, `AgentPolicy` | **Two canonicals by consumer.** `core` is canonical for engine/apps-api; `models` is canonical for SDK client. | Not dead. Different shapes (engine has spending policy embedded). |
| **Wallet** | `models/wallet.py` `Wallet(SardisModel)`, `TokenLimit`, `WalletBalance`, transfer req/resp, `CreateWalletRequest` | `core/wallets.py` `Wallet(BaseModel)`, `TokenLimit(BaseModel)`, + `@dataclass(slots=True)` variant | core for engine; models for SDK | `TokenLimit` defined twice. |
| **Payment** | `models/payment.py` `Payment(SardisModel)`, `PaymentStatus`, execute req/resp, `PayResult`, `FXDetails`, `RouteDetails` | `core/payment_object.py` (`PaymentObject` + status enums), `core/payment_result.py`, `core/transactions.py`, `core/unified_payment.py` | core/payment_object for engine; models/payment for SDK | The SDK `Payment` DTO ≠ engine `PaymentObject`; do NOT naively merge. |
| **Group** | `models/group.py` `AgentGroup`, `GroupBudget`, req/resp | `core/agent_groups.py` | split | medium |
| **Card / Hold / Policy / Treasury / Webhook / Marketplace** | `models/{card,hold,policy,treasury,webhook,marketplace}.py` | `core/{virtual_card,holds,spending_policy,stripe_treasury,webhooks,marketplace}.py` | split | each is a DTO-vs-domain pair |

**Conclusion:** the duplication is structural (public DTO vs internal domain), not accidental. Collapsing it requires an adapter/mapping layer, not deletion — **medium-risk**.

---

## 4. Inline route models (the 122 → actually 653)

- **653** classes `(...BaseModel)` defined inline across **109** route files in `apps/api/server/routes/*` (the dossier's "~122" likely counted only request models or one subtree).
- **Worst offenders:**
  | File | inline models |
  |---|---|
  | `wallets/lifecycle.py` | 31 |
  | `wallets/ramp.py` | 20 |
  | `accounts/auth.py` | 19 |
  | `agents/lifecycle.py` | 18 |
  | `operations/analytics.py` | 15 |
  | `protocol/a2a.py` | 14 |
  | `commerce/secure_checkout.py` | 14 |
  | `authority/facility_requests.py` | 14 |
  | `policy/policies.py` | 13 |
  | `developer/sandbox.py` | 13 |
- These are request/response DTOs, not persistence — low money-risk to extract into a shared `schemas/` package, but high churn / large diff. Quick-win candidate only if done file-by-file with tests green.

---

## 5. Migration / Alembic situation

### 5.1 Authoritative chain
- **`apps/api/migrations/*.sql`** — 113 files, contiguous **001 → 111**, applied by `scripts/run_migrations.sh` using a `schema_migrations(version PK)` table. This is what runs against Neon. **Authoritative.**

### 5.2 Dead alembic
- **`apps/api/alembic/`** — 30 `versions/*.py`, head **030** (`030_facility_gate.py`), and naming already **diverges** from the SQL chain at 030 (SQL 030 = `030_merchant_checkout.sql`). Stops 81 versions behind. Only consumer is `apps/api/tests/test_facility_gate_migration.py`, which is **skipped unless `SARDIS_TEST_POSTGRES_DSN` is set** (one of the 15 baseline skips). Not in the runtime path, **not referenced by `.github/` CI.**
- **`scripts/release/migration_alignment_check.sh`** parses both trees and asserts equal heads + contiguous alembic chain. It would **FAIL today** (`head mismatch: sql=111, alembic=030`; `missing Alembic revisions 031..111`). It is **not wired into CI**, so the failure is currently invisible. → The alembic tree is **dead weight that a stale guard pretends is alive.**

### 5.3 The 102_* collision (REAL latent bug)
- Two files parse to version `102`:
  - `102_idempotency_request_hash.sql` — `ALTER TABLE idempotency_records ADD COLUMN request_hash`
  - `102_stripe_connect.sql` — Stripe Connect columns on `merchants` + payout-tracking table
- `run_migrations.sh` extracts `version=$(grep -oE '^[0-9]+')` → both yield `102`. Files apply in **alphabetical glob order**: `idempotency` first → inserts `102` into `schema_migrations` → `stripe_connect` then matches `^102$` in APPLIED and is **`[SKIP]`-ped forever**. On a fresh DB, **Stripe Connect migration never runs** unless applied manually. On any DB where stripe ran first, idempotency is the silent victim.
- **Repo-level fix:** renumber one file (e.g. `102_stripe_connect.sql` → `112_stripe_connect.sql`, or insert at an unused slot) + matching rollback if present. Pure file rename, no live DB touched. **Clearly-safe quick win.**

---

## 6. Consolidation plan (ranked by safety)

### (a) Clearly-safe quick wins — do first, each test-green
1. **Fix the 102 collision** — renumber `102_stripe_connect.sql` to the next free integer (`112_*`). Update any `*_rollback.sql` counterpart. No live DB cutover; repo file only. Verify `run_migrations.sh --dry-run` lists both. **(money-relevant correctness fix — highest value-to-risk.)**
2. **Quarantine dead alembic** — either delete `apps/api/alembic/` + `alembic.ini` and the skipped `test_facility_gate_migration.py`, OR (more conservative) move under `docs/legacy/` and update `migration_alignment_check.sh` to stop asserting on it. Decide via a one-line ADR. Confirm no runtime importer (only the skipped test imports it). **DONE_WITH_CONCERNS acceptable if any doubt — just document it's dead.**
3. **Produce the clean squashed schema baseline file** (repo-level only): generate one `000_baseline.sql` equivalent to the current 001→111 applied state, kept alongside (not replacing) the chain, so future work has one canonical DDL to diff against. **No live Neon cutover here** — that's a separate deploy step.
4. **Decommission `migration_alignment_check.sh`** or repoint it at the SQL chain only (it currently guards a fiction). Quick.

### (b) Medium — staged, each behind tests, no money-path behavior change
5. **Consolidate `organizations` provisioning** — three insert shapes (`organizations.py` full vs `agent_repository_postgres.py`/`auth.py` thin `external_id,name,settings`) → route the thin path through the core `organizations.py` create function. Control-plane, not money. Stage: introduce one helper, migrate callers one at a time.
6. **Extract inline route DTOs** into a shared `apps/api/server/schemas/*` package, worst-offenders first (`wallets/lifecycle.py`, `wallets/ramp.py`, `accounts/auth.py`, `agents/lifecycle.py`). Pure DTO move, no SQL change. Large diff → do per-file, keep green.
7. **`agents` side-writes** — fold `agent_events.py`/`agent_heartbeat.py` writes behind a single agent repo seam (engine `agent_repository_postgres.py`). Identity, not money.
8. **Introduce ONE repo seam interface** (typed) over the existing `Database` primitive, and migrate the clearly-single-owner SDK-core repos (`approval_repository`, `revocation_repository`, `delegation_repository`, `receipt_store`, `policy_version_store`, `notification_service`) to it. These tables have no cross-layer overlap → low risk.

### (c) Money-path-critical / risky — DEFER or carefully staged, do NOT one-shot
9. **`spending_mandates`** dual-writer (spend-accrual in `mandate_hook.py` vs create/revoke in route vs status in `spending_mandate_lookup.py`/`revocation_ports.py`). The spend-accrual `spent_total += $1` is authority-over-money. **Defer.** If touched: first write a characterization test capturing exact concurrent-decrement semantics (`FOR UPDATE`, idempotency), then move behind a single mandate repo without changing the SQL.
10. **`payment_objects` + `payment_state_transitions`** dual-writer (create/expire/revoke split across route + core jobs). **Defer.** Append-only transition tables must keep ordering/trigger semantics; document the two triggers, don't merge blindly.
11. **`mandate_state_transitions`** (revocation audit) — same: append-only, dual-triggered. **Defer.**
12. **`wallets`** writers (`wallet_repository_postgres.py` CRUD + `jobs/spending_reset.py` counter reset + `wallets/emergency.py` freeze). Freeze and spend-counter reset are money-safety. **Defer** unification; if needed, only consolidate the read/CRUD path, leave freeze/reset writes in place + documented.
13. **`settlements`/`settlement_records`/`ledger_entries_v2`** (a2a_settlement, inbound_payment) — ledger writes. Single-layer today (no overlap) but money-critical; **leave untouched** this phase.

### Rules carried forward
- Hold `3032 passed / 15 skipped` at every commit.
- Any (c) item that resists a clean, test-green collapse → leave + record **DONE_WITH_CONCERNS** with the exact reason. Never trade money-path correctness for tidiness.
- All migration work is **repo-level only**; the live Neon cutover is a separate deploy step, not this workflow.
