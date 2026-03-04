# Issuing Compliance Pack (Warm Integration)

Date: 2026-03-04  
Owner: Product + Compliance + Platform

## Purpose

Keep issuing integrations technically ready while remaining out of production launch mode until an issuer grants conditional/live approval.

This pack is issuer-agnostic and reusable across Stripe, Lithic, Rain, and Bridge.

## Scope

1. Required disclosures and agreements inventory.
2. Complaints/disputes SOP and escalation path.
3. Receipt delivery and record-retention controls.
4. Support channel evidence requirements.
5. Stripe hosted-onboarding-first decision path to minimize custom KYC burden.

## Repository Links

- Warm-mode gate: `packages/sardis-api/src/sardis_api/routers/cards.py`
- Issuer adapter contract: `packages/sardis-cards/src/sardis_cards/providers/issuing_ports.py`
- Issuer adapter shim: `packages/sardis-cards/src/sardis_cards/providers/issuer_adapter.py`
- Funding capability matrix: `packages/sardis-api/src/sardis_api/routers/funding_capabilities.py`
- Release gate check: `scripts/release/issuer_compliance_pack_check.sh`

## Contents

- [disclosures-and-agreements.md](./disclosures-and-agreements.md)
- [complaints-disputes-sop.md](./complaints-disputes-sop.md)
- [receipts-recordkeeping.md](./receipts-recordkeeping.md)
- [support-evidence-checklist.md](./support-evidence-checklist.md)

