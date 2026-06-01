# Phase 2 — Persistence Rebuild: GATE result

**Branch:** `feat/persistence-rebuild` · **Worktree:** `/Users/efebarandurmaz/sardis-phase2`
**Date:** 2026-06-01 · GATE engineer

This is the build/test/lint gate summary for the persistence-consolidation phase.
For the full per-overlap analysis see `PHASE2_MAP.md` (survey) and
`PHASE2_CONSOLIDATION_DONE_WITH_CONCERNS.md` (dispositions + backlog). This doc
does not repeat them; it records that the gate is green and what is deferred.

## GATE result — GREEN

```
uv sync                                                   → resolved 423 pkgs, OK
uv run pytest apps/api/tests packages/sardis/tests -q     → 3037 passed, 15 skipped, 0 failed (85s)
uv run ruff check apps/api packages/sardis                → All checks passed!
```

### The 15 skips are pre-existing and NOT phase-2 regressions

Verified by `git blame`/`git log` on the skip-annotated files: every skip is
either an unconditional import/env guard or was introduced on `main` by
`342da6d6` ("fix(ci): unblock 3 main CI gates (#395)"), **not** by any of the
four phase-2 commits (`dd9aa66e`, `7cd33532`, `3daa8eb5`, `196eead4`). They fall
into three buckets:

- **Missing optional deps / packages:** `immudb` not installed (2 ledger tests),
  `sardis_ucp not installed`, `db_engine.py`/`records.py`/`sardis-ledger`
  not-found (3 ledger-precision tests).
- **Env-gated (need a real Postgres / prod env):** `SARDIS_TEST_POSTGRES_DSN`
  unset (facility-gate migration), prod/staging-only durability assertions,
  admin-login-unavailable email verification, concurrency holds-unavailable.
- **Explicitly pre-existing, tracked separately (annotated on main):**
  facility-gate pilot-readiness `blocked` vs `passed`, two partner-card webhook
  mocks not wired post-consolidation.

This matches the dossier's note that the pre-existing ledger DB-connection
skips are unrelated to this work.

## What was consolidated (committed, repo-level only)

1. **`102_*` migration collision — FIXED** (`7cd33532`). Two files parsed to
   ordinal `102` in `scripts/run_migrations.sh`; the alphabetical glob applied
   `102_idempotency_request_hash.sql` and then **silently skipped**
   `102_stripe_connect.sql` forever. Renamed `102_stripe_connect.sql →
   112_stripe_connect.sql` (next free slot after head 111; disjoint tables, keeps
   alphabetical-last position → schema-safe reorder). Verified: zero duplicate
   forward ordinals remain (`001` only appears via its `_rollback` companion,
   which the runner skips at line 47).

2. **Canonical model index — ADDED** (`3daa8eb5`). New `sardis.canonical_models`:
   an additive, behaviour-identical re-export index giving ONE source-of-truth
   pointer for the entities the MAP flagged as "defined twice" (Agent, Wallet,
   Payment, Group, TokenLimit). `Engine*`/`Sdk*` names resolve to the existing
   canonical classes; bare names resolve to the engine (money-path) domain. No
   new types, no field/wire/DB change. Locked by identity tests (re-exports are
   the SAME class objects) + a money-safety guard (`Wallet.is_frozen/freeze()`
   stays on the engine model, never leaks into the public DTO).

3. **Dual-persistence collapse — NONE this pass, by design** (`196eead4`). Every
   MAP §2 overlap was re-verified against source; none is simultaneously a
   genuine redundant duplicate, clearly money-safe, AND test-green-trivial. Two
   decisive facts: (a) `apps/api/tests/conftest.py` runs the whole apps/api suite
   under `DATABASE_URL=memory://`, so the in-memory dual-mode branches are the
   *tested* path (not dead code) — deleting any breaks the suite; (b) the
   single-owner SDK-core repos already use a clean `Protocol` + `InMemory*` +
   `Postgres*` design over the shared `Database` primitive, with `InMemory*`
   used by 10 test files — nothing redundant to remove. Per hard-rule 1
   (money-correctness over tidiness), all overlaps are DEFERRED + documented
   rather than force-collapsed.

## Schema baseline approach

A squashed single-file baseline was **intentionally NOT shipped** (`7cd33532`).
The `001 → 112` SQL chain does not apply cleanly to a fresh empty Postgres —
7 pre-existing break points (022 UUID/TEXT FK, 031 `gen_random_bytes`, 037
non-IMMUTABLE index predicate, 054/062 missing relations, 083 missing column,
089 `schema_migrations.name`), documented in `PHASE2_MAP.md §7`. Because no
deterministic "current schema" is reproducible from the chain on an empty DB,
schema-equivalence cannot be cleanly proven, and hand-assembling a baseline
would be an unverified guess at the live Neon schema — which the task forbids.
The honest outcome: collision fixed, break points documented, baseline stopped
pending a live-schema dump.

**Alembic is NOT dead** (correcting MAP §5.2): `.github/workflows/deploy.yml`
runs `alembic upgrade head` as the live staging+production DB-migration step.
It is retained. There is a real drift (alembic head `030` vs SQL chain head
`112`) — deferred, see below.

## DEFERRED follow-ups (careful, staged, out of scope for this repo-level phase)

Money-path consolidations — each needs a **characterization test first**, then a
behaviour-preserving move, validated against a real DB:

- **`spending_mandates`** — single-owner repo; pin concurrent `spent_total +=`
  spend-accrual + idempotency (`FOR UPDATE`) semantics before moving writers.
- **`payment_objects` / `*_state_transitions` / `mandate_state_transitions`** —
  append-only money-state-machine tables; document the two triggers per table +
  ordering invariants before any unification.
- **`wallets`** — consolidate read/CRUD only; leave freeze (`wallets/emergency.py`)
  and spend-counter reset (`jobs/spending_reset.py`) writes in place.
- **`agents` side-writes** — fold heartbeat/event writes behind the repo seam
  only if the heartbeat `xmax = 0` inserted-detection, SSE side-effect, and
  COALESCE-preserve semantics are reproduced exactly.
- **`funding_cells` / `erc8183_jobs`** — concurrency-sensitive state machines;
  characterization tests required.
- **`organizations` provisioning** (control-plane, MEDIUM) — introduce one
  `ensure_org(...)` helper, migrate the two thin callers one at a time,
  preserving each conflict policy + settings shape.
- **`subscriptions`** — confirm whether `subscriptions_repository` (PK `id`) and
  `authority/mandate_subscriptions` (key `subscription_id`) are the same physical
  table; likely distinct domains that should stay separate.

Tidiness long tail (no SQL change, large diff, schedule independently):

- **Inline route DTOs** — MAP §4 flags ~653 inline models across ~109 files;
  pure DTO extraction into `apps/api/server/schemas/*`, worst-offenders first,
  per-file, tests green.
- **Field-level DTO↔domain collapse** of the canonical entities — needs an
  adapter layer, not a deletion (merging would leak engine/money-safety state
  into the public wire DTO, or strip it from the engine model).

Deploy-pipeline / live-DB tasks (explicitly NOT this workflow):

- **Live-DB baseline cutover** — dumping the live Neon schema to produce a
  verified squashed baseline is a **separate deploy step**, not this repo-level
  phase.
- **Alembic head drift** — alembic head `030` vs SQL chain head `112`; the
  deploy pipeline applies ≤030 via alembic, 031..112 applied out-of-band. Real
  coverage gap; touches the live deploy path + live DB → dedicated task.

## Honesty statement

The conservative pass collapses no dual-persistence and ships no squashed
baseline. That is the correct result, not skipped work: the dual-persistence
here is overwhelmingly intentional lifecycle-phase separation over a money-path
(not accidental duplication), the in-memory branches are the test substrate, and
the SQL chain is not clean-appliable to an empty DB. The real latent bug (the
`102_*` silent-skip collision) is fixed, the duplicate-model situation has a
canonical index, and every safe-but-staged consolidation is documented with a
verified reason and a characterization-test-first plan. Money-correctness over
tidiness, tests green at every step.
