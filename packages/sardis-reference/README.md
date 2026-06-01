# @sardis/reference

**How Sardis decides if an agent may spend** — a pure, deterministic, money-free
TypeScript mirror of the Sardis authority-decision and protocol-verification logic.

This package is the open-core decision contract. It lets anyone:

- run the **policy simulator** against a proposed spend and get
  `allow | requires_approval | deny` + a reason code, offline;
- **offline-verify** an AuthorityProof, an AP2 mandate chain, a TAP request, and
  an x402 (EIP-3009) authorization — with **zero money at risk** and **no Sardis
  backend call**.

It is **not** the money-mover. There is no RPC, no provider client, no database,
no key custody, no `fetch`. It never executes a payment. The private backend owns
execution; this package owns the *decision contract* and lets the ecosystem audit
it.

> Status: scaffold. Types, simulator, and verifiers land in subsequent commits.
