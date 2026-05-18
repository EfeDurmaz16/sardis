# Reconciliation Load Chaos SLOs

Reconciliation must remain correct under duplicate, delayed, and out-of-order
provider events.

## SLOs

- **Duplicate event suppression:** duplicate provider events for the same
  settlement or treasury movement must not create duplicate ledger entries.
- **Out-of-order event handling:** later lifecycle events may arrive before
  earlier ones, but replay must converge to the same canonical ledger state.
- **Load tolerance:** reconciliation load tests should complete without
  unbounded queue growth, dropped events, or tenant-crossing ledger writes.
- **Operator visibility:** failed reconciliation attempts must retain enough
  context for replay, root-cause analysis, and partner-facing incident notes.

## Validation

Run:

```bash
bash scripts/release/reconciliation_chaos_check.sh
```

The gate checks this runbook and runs the canonical ledger repository,
reconciliation engine load, and treasury operations API tests.

## Response

If load or ordering tests fail, pause the affected provider ingest path, replay
from the last known-good cursor, and compare the canonical ledger repository
against provider source records before reopening automation.
