# 08 Database And Data Audit

## Findings

### High: Two migration histories can drift

- Evidence: Alembic versions stop at `packages/sardis-api/alembic/versions/030_facility_gate.py`, while raw SQL migrations continue to `packages/sardis-api/migrations/106_agent_registry.sql`.
- Impact: New environments may initialize different schemas depending on the path used.
- Recommended action: Choose canonical raw SQL or Alembic path, then create a reconciliation test.
- Action type: Migration.
- Estimated risk: High.
- Validation method: apply canonical migrations to empty Postgres and run API repository smoke tests.

### Medium: Placeholder migration exists

- Evidence: `packages/sardis-api/migrations/049_placeholder.sql` inserts version 49 only to preserve numbering.
- Impact: Placeholder is acceptable historically but signals manual migration management.
- Recommended action: Keep it, but document migration numbering policy.
- Action type: Documentation.
- Estimated risk: Low.
- Validation method: migration runner handles placeholder idempotently.

### Medium: Local data files exist in package folders

- Evidence: `packages/sardis-api/data/mandates.db` and `packages/sardis-api/data/replay_cache.db` are present locally but ignored by `.gitignore`.
- Impact: Local data can affect manual tests if scripts discover it accidentally.
- Recommended action: Keep ignored; ensure validation scripts do not inspect local data.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: clean inventory script.
