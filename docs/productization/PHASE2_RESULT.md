# Phase 2 — Migration / Deploy Reconciliation: GATE result

**Branch:** `feat/persistence-rebuild` · **Worktree:** `/Users/efebarandurmaz/sardis-phase2`
**Date:** 2026-06-01 · GATE engineer

The go-live blocker (PHASE2_MAP.md §7 + the migration-phase report) was twofold:
(a) the SQL migration chain `apps/api/migrations/*.sql` did **not** apply cleanly
to an empty Postgres (7 documented break points); (b) the deploy pipeline ran
`alembic upgrade head` (head **030**), so migrations **031–113** — including all
the new moat/primitive tables — were **never applied by the deploy pipeline**, and
a fresh prod deploy would crash. This phase makes the **SQL migrations the single
source of truth AND the deploy mechanism**, stands a fresh DB up cleanly from
them, switches the deploy pipeline to apply all of them, retires alembic, and adds
a CI guard. This doc is the build/test/lint gate + the final clean-apply proof.

For the persistence survey see `PHASE2_MAP.md`; for the founder's one-time live-Neon
cutover see `MIGRATION_CUTOVER.md` (gitignored, local-only).

---

## GATE result — GREEN

```
uv sync                                                → resolved 421 pkgs; uninstalled alembic/mako/markupsafe (retired)
uv run pytest apps/api/tests packages/sardis/tests -q  → 3037 passed, 15 skipped, 0 failed (104.76s)
uv run ruff check apps/api packages/sardis             → All checks passed!
```

The 15 skips are pre-existing env-/dep-gated tests (missing optional `immudb` /
`sardis_ucp`, `SARDIS_TEST_POSTGRES_DSN` unset, prod-only durability assertions),
not phase-2 regressions — same set as the MAP baseline.

## Final clean ephemeral apply — PROOF

Verified against an **ephemeral local Docker `postgres:16-alpine`** (matching the
prod engine + the CI service container), applying the chain exactly as the deploy
pipeline does, then torn down. The live Neon DB was never touched.

```
Guard 1 (no duplicate ordinals):  OK — every migration ordinal is unique (113 migrations)
Quarantine 083:                    083 seeded into schema_migrations (runner SKIPs it)
Guard 2 (fresh-from-empty apply):  bash scripts/run_migrations.sh → reached [DONE] 113_facility_gate.sql, exit 0
Guard 3 (idempotent re-run):       second run → 0 [APPLYING], 113 [SKIP], exit 0
Guard 4 (moat tables, under bash): OK — spending_mandates, approval_requests, recourse_holds, revocations, delegations all present
Post-apply state:                  171 public tables, 119 schema_migrations rows
```

Per-break-point object verification on the fresh DB:

| Break point | Fix | Fresh-DB proof |
|---|---|---|
| **022** organizations FK UUID-vs-TEXT | Made 022 column types + columns match the 001 schema | `organizations.id` = `uuid`; `teams` has 2 resolved FK constraints |
| **031** `gen_random_bytes` | Enable `pgcrypto` in 001 | `pg_extension` has `pgcrypto` |
| **037** non-IMMUTABLE index predicate | Drop the `now()` predicate from the idempotency index | `idempotency_records` table present, chain applied past 037 |
| **054** missing `x402_settlements` | Create the base `x402_settlements` table in 054 | `x402_settlements` present |
| **062** missing `cards` | Create the base `cards` table in 062 | `cards` present |
| **089** `schema_migrations.name` | Insert via `(version, description)` (runner's real columns) | `schema_migrations` row `089` present; `notification_configs` present |
| **083** missing `org_id` (016 vs 083 `subscriptions` shape conflict) | **Quarantined + documented** — not a DDL fix; data-model decision needing the live schema | row `083` recorded as `[QUARANTINED]`; `charge_intents` correctly absent |
| (102 collision) | Renumber `102_stripe_connect.sql` → `112_*` | both `idempotency_records.request_hash` AND `stripe_connect_payouts` present |

## What changed in the deploy path

1. **Deploy switch (`a8be60d3`).** `.github/workflows/deploy.yml` — BOTH the
   `deploy-api-staging` and `deploy-api-production` jobs now run
   `bash scripts/run_migrations.sh` (against the job's `DATABASE_URL` secret)
   instead of `cd apps/api && alembic upgrade head`. The runner applies the full
   `001 … 113` chain, is idempotent (`schema_migrations` version tracking +
   `IF NOT EXISTS`), and fails loud (`ON_ERROR_STOP=1`) so a broken migration can
   never produce a false "complete". `scripts/release/deployment_config_check.sh`
   was updated to assert `bash scripts/run_migrations.sh` (not `alembic upgrade
   head`).

2. **Alembic retired (`e8e624a8`, `1c4beb7b`).** `apps/api/alembic/` (30 versions)
   + `alembic.ini` deleted; the only DDL alembic still owned that the SQL chain
   lacked — facility-gate (alembic rev 030) — was **ported to SQL migration
   `113_facility_gate.sql`**. `test_facility_gate_migration.py` now drives the SQL
   runner (no alembic import). `alembic` dropped from `pyproject` (uv sync
   uninstalled it). The 3 residual "alembic" mentions in repo config are benign
   comments noting the retirement. The migration runner was hardened
   (fail-loud, version tracking, `--mark-applied` / `--dry-run` modes).

3. **CI guard (`3b8efea0`).** New `.github/workflows/migrations.yml` runs on any
   change to `apps/api/migrations/**`, `scripts/run_migrations.sh`, or itself,
   against an ephemeral `postgres:16` service container (never Neon). Four guards:
   (1) no duplicate ordinals (the 102-style collision), (2) full chain applies
   fresh-from-empty (the real deploy step), (3) re-run is a clean no-op
   (idempotency), (4) the key moat tables exist (`spending_mandates`,
   `approval_requests`, `recourse_holds`, `revocations`, `delegations`). 083 is
   quarantined explicitly and loudly (seeded so the runner SKIPs it) — when 083 is
   fixed, that step is deleted and the chain must go green on its own. This
   replaces the dead `migration_alignment_check.sh` alembic-alignment fiction.

Net: the SQL chain is now the single source of truth for the schema **and** the
deploy mechanism; a fresh DB stands up cleanly (083 quarantined); the deploy
pipeline applies the whole chain; alembic is gone; CI guards it forever.

## The one outstanding item — 083 (deferred by design)

`083_subscriptions.sql` does not apply to an empty DB: migration **016** already
owns a `subscriptions` table with an incompatible shape (`id` PK, `wallet_id`, no
`org_id`), so 083's `CREATE TABLE IF NOT EXISTS subscriptions` (`subscription_id`
PK, `org_id`, …) no-ops and its `org_id` index / `charge_intents` / `usage_meters`
statements fail. Two live code paths expect the two different shapes for the same
table name (`subscriptions_repository.py` + `billing_events` → 016 shape;
`mandate_subscriptions.py` + `billing/usage.py` → 083 shape). Resolving this is a
**data-model decision** (rename one table or merge column sets) that requires
knowledge of the **live Neon `subscriptions` schema** and cannot be settled from
the repo alone — so it is intentionally NOT force-fixed. It is **quarantined** in
both CI and the cutover (on Neon 083's CREATE was a no-op too, so it does not block
deploys today). A brand-new stand-up-from-empty prod deploy must not be attempted
until 083 is resolved in a dedicated, live-validated task; everyday idempotent
re-deploys are unaffected.

## FOUNDER one-time live-Neon cutover (do NOT automate)

The repo + CI + deploy pipeline only ever touch ephemeral/local databases. The
single manual step that touches the live Neon DB is the **founder's**, documented
precisely in **`docs/productization/MIGRATION_CUTOVER.md`** (gitignored, local).
Summary of that procedure (staging first, then production):

1. **Backup** — create a Neon branch of the target DB (instant copy-on-write
   rollback).
2. **Inspect** the mismatch (READ-ONLY): `alembic_version` (single row `030`) vs
   `schema_migrations` (missing rows for 031–112).
3. **Confirm physical presence** — spot-check that the 031–112 objects
   (`spending_mandates`, `approval_requests`, `recourse_holds`, `revocations`,
   `delegations`, `stripe_connect_payouts`) already exist on Neon (they were applied
   out-of-band). If any are absent, STOP.
4. **Seed bookkeeping** — `DATABASE_URL="$NEON_URL" bash scripts/run_migrations.sh
   --mark-applied` records every repo version as applied **without executing any
   SQL** (writes only to `schema_migrations`, no DDL/DML against real tables).
5. **Verify** — `--dry-run` must report **zero pending** (all `[SKIP]`).
6. **Migration 113 caveat** — facility-gate tables were created by the old alembic
   030, so `--mark-applied` correctly records 113. Only on a DB where facility
   tables are absent: delete the 113 row and let the runner apply it.
7. **Rollback** — `schema_migrations` is pure bookkeeping; `TRUNCATE
   schema_migrations` and re-seed, or restore the Neon branch.

After cutover, the deploy pipeline's `bash scripts/run_migrations.sh` is safe and
idempotent on Neon: it applies only genuinely new migrations and skips the rest.
