# SQL Query Composition Review

Date: 2026-02-13

## Scope

Manual review of dynamic SQL construction patterns flagged by static grep in:

- `packages/sardis-api/src/sardis_api/repositories/card_repository.py`
- `packages/sardis-api/src/sardis_api/routers/invoices.py`
- `packages/sardis-api/src/sardis_api/routers/mandates.py`

## Findings

- `card_repository.py` dynamic `SET` clause is built only from a fixed internal tuple of allowed column names (`limit_per_tx`, `limit_daily`, `limit_monthly`) and still uses positional bind parameters for values.
- `invoices.py` dynamic `WHERE` clause is composed from fixed field names and `$n` placeholders; user-provided values are appended as bound arguments.
- `mandates.py` dynamic `WHERE` clause follows the same placeholder pattern; user-provided values are never string-concatenated directly into SQL.

## Conclusion

No direct SQL injection vector was identified in the reviewed dynamic query builders. Dynamic segments are restricted to trusted field fragments, while user inputs are parameterized.

## Recommended Follow-up

- Keep dynamic SQL limited to allowlisted field names.
- Preserve positional/bound parameters for all user-controlled values.
- Re-run this review when adding new f-string SQL query builders.
