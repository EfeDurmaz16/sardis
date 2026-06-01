# Phase 2 — Dual-Persistence Consolidation: outcome + DONE_WITH_CONCERNS

**Branch:** `feat/persistence-rebuild` · **Worktree:** `/Users/efebarandurmaz/sardis-phase2`
**Date:** 2026-06-01 · Consolidation engineer (conservative pass)
**Test bar held:** `uv run pytest apps/api/tests packages/sardis/tests -q` → **3037 passed, 15 skipped, 0 failed** (the 15 skips are the pre-existing Postgres-DSN-gated ledger/Facility-Gate tests, `SARDIS_TEST_POSTGRES_DSN`/`POSTGRES_TEST_DSN` unset — matches base).

This document records the result of the dual-persistence consolidation phase described in MAP §6. The mandate was: collapse a flagged dual-persistence overlap **only when it is clearly a genuine redundant duplicate, clearly safe (no money-path/behaviour change), and stays test-green** — otherwise DEFER + document. Money-correctness over tidiness.

---

## Headline: nothing was collapsed this pass. Here is exactly why — verified against code, not the MAP doc.

I re-verified every overlap in MAP §2 against the source. The MAP's per-row verdicts hold up: **none of the flagged overlaps is simultaneously (a) a genuine redundant duplicate, (b) clearly safe, and (c) test-green-trivial.** Each is one of:
- **money-path-critical** (collapsing risks a money behaviour change — forbidden by rule 1), or
- a **distinct-lifecycle write with a distinct column-set / distinct upsert semantics** (the two "writers" do *different things* to the same table — collapsing them is a behaviour change, not deduplication), or
- backed by a **test-load-bearing in-memory branch that cannot be deleted**.

Two decisive facts drove this:

1. **`apps/api/tests/conftest.py:34` sets `DATABASE_URL = "memory://"` for the ENTIRE apps/api suite.** Therefore the `self._use_postgres == False` / in-memory branches in `organizations.py`, `marketplace.py`, etc. are **the code path the whole test suite exercises.** Deleting any in-memory dual-mode branch breaks the suite wholesale. The MAP's "delete dead/confusing in-memory branches" item does not apply: these branches are not dead — they are the test backbone.

2. The "single-owner" SDK-core repos the MAP nominated for a unified seam (MAP §6 item 8: `revocation_repository`, `delegation_repository`, `receipt_store`, `approval_repository`, `policy_version_store`, `notification_service`) **already follow a clean `Protocol` + `InMemory*` + `Postgres*` pattern over the shared `Database` primitive.** There is no redundant raw-SQL path to delete; the InMemory variants are used by 10 test files. This item is effectively already satisfied — there is nothing to consolidate, only to NOT break.

Forcing a collapse anywhere in this set would have traded money-path correctness (or test-green) for cosmetic tidiness, which the hard rules forbid. The honest, correct outcome of a conservative pass is therefore: **defer all, document precisely.**

---

## Per-overlap dispositions (every MAP §2 row, verified)

### Money-path-critical → DEFER (rule 1: never risk a money behaviour change)

| Table(s) | Writers (verified) | Why deferred |
|---|---|---|
| **`spending_mandates`** | `core/hooks/mandate_hook.py` (`spent_total += $1` spend accrual), `core/revocation_ports.py` (revoke), `core/spending_mandate_lookup.py` (status), `core/jobs/payment_expiry.py` (expiry); route `accounts/.../spending_mandates.py`, `agent_auth.py`, `mandate_delegation.py`, `merchant_checkout.py` (create/revoke/status) | The spend-accrual is **authority over money**. The four writers act at different lifecycle phases with no single owner; concurrent-decrement / idempotency semantics must not change. Requires a characterization test of the exact `FOR UPDATE`/idempotency behaviour *before* any move. |
| **`payment_objects` + `payment_state_transitions`** | route `money_movement/payment_objects.py` (create + expire + transition append); `core/jobs/payment_expiry.py` (expire), `core/revocation_ports.py` (revoke) | Append-only transition tables; ordering/trigger semantics are money-state-machine invariants. Two triggers fire from different sources by design. |
| **`mandate_state_transitions`** | `core/revocation_ports.py`; route `spending_mandates.py` | Append-only revocation audit, dual-triggered. Same reasoning. |
| **`wallets`** | `core/wallet_repository_postgres.py` (CRUD), `core/jobs/spending_reset.py` (counter reset); route `wallets/emergency.py` (freeze), `wallets/lifecycle.py` | Freeze and spend-counter reset are money-safety controls. Repo owns CRUD; emergency/reset are deliberate side-writes. Do not unify the safety writes. |
| **`agents.spending_policy` via `core/policy_store_postgres.py`** | `record_spend()` does atomic spend accumulation in the `spending_policy` JSONB under `SELECT … FOR UPDATE` with lost-update protection (`policy_store_postgres.py:101-150`) | Direct money-path; the minimal `INSERT INTO agents (external_id,name) … ON CONFLICT DO NOTHING` is a defensive ensure-exists stub *inside the spend transaction*. Untouchable this phase. |
| **`funding_cells`** | route `wallets/funding.py` (provision/merge); `core/cell_claim.py` (atomic claim + merge, concurrency-sensitive) | Wallet funding cell claim/merge is money-path with subtle concurrency. Heavy dual-write, entangled. |
| **`settlements` / `settlement_records` / `ledger_entries_v2`** | `core/a2a_settlement.py`, `core/inbound_payment_service.py`, `core/settlement.py` | Ledger writes. Single-layer today (no cross-layer overlap) but money-critical — left untouched per MAP §6c-13. |
| **`erc8183_jobs` / `erc8183_evaluations`** | route `protocol/erc8183.py` (create + 5 state UPDATEs); `core/erc8183_job.py` (create + 6 state UPDATEs) | Borderline money-path (ERC-8183 payment jobs). Extensive dual state-machine writes across both layers; collapsing risks state-transition divergence. |

### Distinct-lifecycle / distinct-column writes (NOT redundant duplicates) → DEFER (MEDIUM)

Collapsing these is a **behaviour change**, not deduplication — the "two writers" do different things to the same table.

| Table(s) | Writer A | Writer B | Why they are NOT duplicates |
|---|---|---|---|
| **`organizations`** | `core/organizations.py` full schema insert (`id,name,slug,plan,billing_email,settings,metadata,…`) | thin `(external_id,name,settings)` insert in `core/agent_repository_postgres.py::_ensure_org` (select-then-insert, empty settings, inside caller's txn) **and** `routes/accounts/auth.py:609` (settings = `{email,signup_source}`, `ON CONFLICT (external_id) DO NOTHING`) | **Three different insert shapes / conflict policies / transaction boundaries** for three different flows (org provisioning, agent-create-time ensure, public signup). Unifying changes settings shape + conflict handling. MEDIUM, control-plane. Candidate for a *future* staged `ensure_org` helper — not a one-shot. |
| **`agents`** | `core/agent_repository_postgres.py` (full CRUD: spending_limits/policy/kya metadata) | route `agents/agent_heartbeat.py` (auto-register upsert with `xmax = 0` inserted-detection + SSE side-effect + COALESCE-preserve heartbeat columns), route `agents/agent_events.py` (event-driven UPDATE), `core/policy_store_postgres.py` (policy ensure-exists) | Four genuinely different upsert semantics for four concerns (CRUD vs heartbeat vs event vs policy). The heartbeat `xmax = 0` inserted-detection and COALESCE-preserve are load-bearing. Collapsing risks losing them. Identity-adjacent but `policy_store` write is policy/authority-adjacent. |
| **`invoices` / `payment_requests`** | `core/inbound_payment_service.py` | routes `commerce/invoices.py`, `wallets/lifecycle.py` | Partial overlap; borderline money-path (inbound payments). Distinct creation contexts. |
| **`subscriptions` / `billing_events`** | repo `subscriptions_repository.py` (Stripe billing, PK `id`) + service `stripe_billing.py` | route `authority/mandate_subscriptions.py` (mandate-driven recurring, key `subscription_id`) | **Different PK columns → two distinct subscription domains** (Stripe billing vs payment-mandate recurring). Not one table with two writers in the redundant sense; collapsing is wrong. |

### Low / complementary (no operational overlap) → DEFER (no benefit, only churn)

These are LOW precisely because the two sites do **complementary, non-redundant** ops; there is nothing to dedupe.

| Table | Sites | Note |
|---|---|---|
| `notification_configs` | route `developer/notifications.py` (INSERT create) vs `core/notification_service.py` (UPDATE delivery-state: failures/last_delivery) | create vs delivery-tracking — complementary, not duplicate. |
| `delegated_credentials` | route `providers/visa_tap_webhooks.py` (narrow status-only UPDATE) vs `core/credential_store.py` (full lifecycle) | webhook status flip vs store CRUD — complementary. |
| `org_members` / `teams` / `team_tree` | `core/organizations.py` vs route `accounts/organizations.py` | membership ops; would ride along with any future `organizations` consolidation. |
| `merchants` | `core/merchant.py` / `core/outcome_tracker.py` / `core/policy_explainer.py` vs route `commerce/merchants.py` | merchant CRUD vs trust-profile reads/writes — different columns. |
| `counters`, `approvals`/`approval_requests` | metrics counters; read-vs-write | not a write/write overlap. |

### In-memory dual-mode branches considered for deletion → KEPT (test-load-bearing, NOT dead)

| Location | Why kept |
|---|---|
| `core/organizations.py` `self._use_postgres` + in-memory dicts | Whole apps/api suite runs under `DATABASE_URL=memory://` (`conftest.py:34`). The in-memory branch is the tested path. Comment at `organizations.py:160-164` explicitly documents it as the dev/test path. |
| `core/marketplace.py` `self._use_postgres` branches | Same reasoning; in-memory branch is reachable + relied on. |
| `core/{revocation,delegation}_repository.py`, `core/receipt_store.py` `InMemory*` classes | Clean `Protocol` + `InMemory*` + `Postgres*` design. The `InMemory*` variants are imported by 10 test files (`test_delegation_engine`, `test_revocation`, `test_revocation_wiring`, `test_orchestrator_delegation`, `test_authority_proof`, `test_delegation_revocation`, `test_orchestrator_delegation_execution`, `core/test_receipt_store`, `apps/api/test_revocation_api`, `apps/api/test_delegation_api`). These are good abstractions, not the "dead/confusing dual-mode" the MAP feared. |

---

## What WAS done earlier in this branch (context, not this pass)

- `dd9aa66e` — persistence MAP (read-only survey).
- `7cd33532` — **102_* collision fixed** (`102_stripe_connect.sql` → `112_*`); alembic retained (it IS the live deploy migration step per `.github/workflows/deploy.yml`, correcting MAP §5.2); squashed baseline **STOPPED** because the SQL chain does not apply cleanly to an empty DB at 7 break points (see MAP §7.3) — shipping an unverified baseline is forbidden.
- `3daa8eb5` — **canonical model index** (`sardis.canonical_models`): additive, behaviour-identical re-export of the existing Agent/Wallet/Payment/Group/TokenLimit canonicals + identity/money-safety guard tests. No field/wire/DB change. The field-level DTO↔domain collapse was deliberately deferred (needs an adapter, not a deletion).

---

## Carry-forward backlog (for a dedicated, staged, test+live-DB-validated task — NOT this repo-level phase)

1. **`organizations` provisioning** — introduce one `ensure_org(external_id, name, settings)` helper in `core/organizations.py`, migrate the two thin callers (`agent_repository_postgres._ensure_org`, `accounts/auth.py`) one at a time, preserving each one's conflict policy + settings shape. Control-plane, MEDIUM. Characterize first.
2. **`spending_mandates` single owner** — write a characterization test pinning the concurrent spend-accrual (`spent_total +=`) and idempotency semantics, THEN move the writers behind one mandate repo without changing the SQL. Money-path; do not start without the characterization test.
3. **`payment_objects`/`*_state_transitions`/`mandate_state_transitions`** — document the two triggers per table, add ordering invariant tests, then (only if needed) unify behind one append API. Money-path.
4. **`wallets`** — consolidate only the read/CRUD path; leave freeze (`wallets/emergency.py`) and spend-counter reset (`jobs/spending_reset.py`) writes in place + documented. Money-safety.
5. **`agents` side-writes** — fold `agent_events.py`/`agent_heartbeat.py` behind the agent repo seam **only if** the heartbeat `xmax = 0` inserted-detection, SSE side-effect, and COALESCE-preserve semantics are reproduced exactly. Identity (+ policy-adjacent for `policy_store`).
6. **`subscriptions`** — confirm whether `subscriptions_repository` (PK `id`) and `authority/mandate_subscriptions` (key `subscription_id`) are the same physical table; if so, reconcile the schema; they are different domains and should likely stay separate.
7. **`funding_cells` / `erc8183_jobs`** — money-path state machines with concurrency; only after dedicated characterization tests.
8. **Inline route DTOs (MAP §4, 653 models / 109 files)** — pure DTO extraction into `apps/api/server/schemas/*`, worst-offenders first, per-file, tests green. No SQL change; large diff. Pure tidiness — schedule independently.
9. **Alembic head drift (MAP §7.2)** — alembic head `030` vs SQL chain head `112`; deploy pipeline applies only ≤030, SQL 031..112 applied out-of-band. Real coverage gap, touches live deploy + live DB → dedicated deploy-pipeline task, out of scope here.

---

## Honesty statement

A conservative pass that collapses nothing can look like "no work." It is the correct result here: the dual-persistence in this codebase is overwhelmingly **intentional lifecycle-phase separation over a money-path**, not accidental duplication, and the in-memory branches are the test substrate. The safe, high-value consolidations all require a characterization-test-first staged approach against the live DB — explicitly out of scope for a repo-level, test-green-at-every-step phase. Forcing them here would have risked money-path behaviour for cosmetics. Deferred + documented is the right call; the backlog above is the careful follow-up.
