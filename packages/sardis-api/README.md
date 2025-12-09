# sardis-api

FastAPI service exposing Sardis execution surfaces:
- mandate ingestion + verification (AP2 Intent/Cart/Payment)
- wallet orchestration and approvals
- ledger queries and compliance feeds
- SDK + CLI friendly JSON APIs

`/api/v2` endpoints only depend on published interfaces from `sardis-core`, `sardis-wallet`, `sardis-ledger`, `sardis-protocol`, and `sardis-chain`.
