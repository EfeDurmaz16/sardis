# Reconciliation Engine Load And Chaos SLOs

Owner: Sardis backend + reliability  
Scope: Canonical ledger state machine and operator workflows

## SLO Targets
1. Event ingest success: `>= 99.95%` (5m window)
2. Duplicate event suppression accuracy: `>= 99.99%`
3. Out-of-order handling correctness: no terminal-state downgrade (out-of-order events never downgrade settled state)
4. Drift detection lag: under 2 minutes from settling event
5. Manual review queue availability: `>= 99.9%`

## Load Test Coverage
1. Concurrent ingestion of 200+ mixed events.
2. Replay storm with repeated provider event IDs.
3. Out-of-order sequence injection:
   - settled before processing
   - returned after settled
4. Multi-rail mix:
   - ACH events
   - card transaction events
   - stablecoin tx/userop status events

## Chaos Scenarios
1. Redis lock delay and duplicate webhook retries.
2. Temporary provider API failures during retry orchestration.
3. Clock skew between event timestamps.
4. Partial scheduler failure for reconciliation guard jobs.

## Validation Commands
1. `pytest -q tests/test_canonical_ledger_repository.py`
2. `pytest -q tests/test_reconciliation_engine_load.py`
3. `pytest -q tests/test_treasury_ops_api.py`
4. `bash scripts/release/reconciliation_chaos_check.sh`

## Pass Criteria
1. No data corruption in `canonical_ledger_journeys`.
2. No duplicate inserts for same provider event id.
3. Open drift breaks and manual reviews are visible in operator APIs.
4. Export endpoint returns complete evidence bundle.
