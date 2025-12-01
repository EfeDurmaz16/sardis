# sardis-core

Foundational primitives shared across Sardis V2 services: deterministic config loading, key management utilities, shared data contracts, and TAP-aligned agent identity helpers. Nothing here should depend on persistence or transport layers—only pure domain logic.

## Responsibilities
- Canonical AP2/TAP/x402 data models (agents, mandates, receipts)
- Deterministic configuration loading + secret adapters
- Secure key lifecycle helpers (Ed25519/ECDSA, MPC connectors)
- Event types and domain errors shared by higher layers
- Hashing + Merkle utilities for audit trails

## Notes
- Export only typed interfaces; concrete implementations live in feature modules (wallet, ledger, etc.).
- Keep cryptographic dependencies minimal and audited.
