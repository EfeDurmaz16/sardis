# Provider Live-Lane Certification Scorecard

Date: 2026-02-26  
Owner: Sardis Platform

## Purpose

Use this scorecard to certify Stripe/Lithic/Rain/Bridge for production live-lane usage under Sardis controls.

## Scoring

- `0` = missing / unknown
- `1` = partial / unproven
- `2` = complete / proven in sandbox
- `3` = complete / proven in production-like lane

Max score per provider: `30`  
Pass threshold for live lane: `>= 23` and **no critical zero** in sections A/B/C.

---

## A) Real-time Authorization (critical, max 9)

1. Auth callback timeout clearly documented and tested (`0-3`)
2. Fail-closed behavior under dependency outage confirmed (`0-3`)
3. Deterministic approve/deny webhook contract validated (`0-3`)

## B) Webhook Security + Idempotency (critical, max 9)

1. Signature verification model documented (header format, timestamp, replay window) (`0-3`)
2. Duplicate event/idempotency behavior proven (`0-3`)
3. Retry/backoff semantics and terminal failure behavior confirmed (`0-3`)

## C) Funding Reliability (critical, max 9)

1. Prefund/cutoff model explicit and contractually clear (`0-3`)
2. Funding failure modes + reversals + reconciliation format validated (`0-3`)
3. Fallback strategy tested (primary unavailable -> fallback rail) (`0-3`)

## D) PAN + PCI Posture (max 3)

1. Hosted/ephemeral/tokenized PAN flow available and validated (`0-3`)

## E) Compliance + Ops (max 3)

1. KYB/KYC/KYT ownership matrix + incident SLA + escalation path clear (`0-3`)

---

## Critical zero blockers

- Any `0` in A/B/C blocks production live-lane certification.

---

## Provider records

### Stripe
- A1:
- A2:
- A3:
- B1:
- B2:
- B3:
- C1:
- C2:
- C3:
- D1:
- E1:
- Total:
- Decision:

### Lithic
- A1:
- A2:
- A3:
- B1:
- B2:
- B3:
- C1:
- C2:
- C3:
- D1:
- E1:
- Total:
- Decision:

### Rain
- A1:
- A2:
- A3:
- B1:
- B2:
- B3:
- C1:
- C2:
- C3:
- D1:
- E1:
- Total:
- Decision:

### Bridge
- A1:
- A2:
- A3:
- B1:
- B2:
- B3:
- C1:
- C2:
- C3:
- D1:
- E1:
- Total:
- Decision:
