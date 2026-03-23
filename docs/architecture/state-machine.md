# Payment Object State Machine

The Sardis payment lifecycle has **22 states** across 5 paths.

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> ISSUED: mint

    %% Happy path
    ISSUED --> PRESENTED: present
    PRESENTED --> VERIFIED: verify
    VERIFIED --> LOCKED: lock
    LOCKED --> SETTLING: settle
    SETTLING --> SETTLED: confirm_settlement
    SETTLED --> FULFILLED: fulfill
    FULFILLED --> [*]

    %% Escrow path
    VERIFIED --> ESCROWED: escrow
    ESCROWED --> CONFIRMING: await_delivery
    CONFIRMING --> RELEASED: confirm_delivery
    ESCROWED --> AUTO_RELEASING: timelock_expire
    AUTO_RELEASING --> RELEASED: auto_release
    RELEASED --> [*]

    %% Dispute path
    ESCROWED --> DISPUTING: dispute
    CONFIRMING --> DISPUTING: dispute
    DISPUTING --> ARBITRATING: arbitrate
    ARBITRATING --> RESOLVED_REFUND: resolve_refund
    ARBITRATING --> RESOLVED_RELEASE: resolve_release
    ARBITRATING --> RESOLVED_SPLIT: resolve_split
    RESOLVED_REFUND --> [*]
    RESOLVED_RELEASE --> [*]
    RESOLVED_SPLIT --> [*]

    %% Terminal transitions
    ISSUED --> REVOKED: revoke
    PRESENTED --> REVOKED: revoke
    ISSUED --> EXPIRED: expire
    PRESENTED --> EXPIRED: expire
    VERIFIED --> EXPIRED: expire
    LOCKED --> EXPIRED: expire
    SETTLING --> FAILED: fail
    SETTLED --> REFUNDED: refund
    FULFILLED --> REFUNDED: refund
    REVOKED --> [*]
    EXPIRED --> [*]
    FAILED --> [*]
    REFUNDED --> [*]

    %% Special
    SETTLING --> PARTIAL_SETTLED: partial_settle
    LOCKED --> UNLOCKING: unlock
    UNLOCKING --> CANCELLED: cancel
    ISSUED --> CANCELLED: cancel
    CANCELLED --> [*]
```

## Paths

### Happy Path (7 states)
```
ISSUED → PRESENTED → VERIFIED → LOCKED → SETTLING → SETTLED → FULFILLED
```
Standard payment flow: mint object, present to merchant, verify signatures, lock funds, settle on-chain, confirm delivery.

### Escrow Path (4 additional states)
```
VERIFIED → ESCROWED → CONFIRMING → RELEASED
                    → AUTO_RELEASING → RELEASED
```
Funds held in escrow until delivery confirmation or timelock expiry.

### Dispute Path (4 additional states)
```
ESCROWED/CONFIRMING → DISPUTING → ARBITRATING → RESOLVED_REFUND
                                              → RESOLVED_RELEASE
                                              → RESOLVED_SPLIT
```
Evidence-based dispute resolution with 3 possible outcomes.

### Terminal States (7)
`FULFILLED`, `RELEASED`, `REVOKED`, `EXPIRED`, `FAILED`, `REFUNDED`, `CANCELLED`, `RESOLVED_*`

### Special States (3)
`PARTIAL_SETTLED` — partial amount settled on-chain
`UNLOCKING` — funds being unlocked from LOCKED state
`CANCELLED` — cancelled by payer before settlement

## Auto-Transitions

The `payment_expiry` background job handles:
- `LOCKED → EXPIRED` when mandate expiry passes
- `ESCROWED → AUTO_RELEASING → RELEASED` when timelock expires
- `ARBITRATING` past deadline → logged as warning (no auto-resolve)

## Guards

Each transition has optional guards (conditions that must be met):
- `lock`: Funding cells must be claimed
- `settle`: SettlementLock must be acquired
- `escrow`: Escrow contract must be deployed
- `dispute`: Must be within evidence deadline
- `resolve_*`: Only arbitrator can resolve

## Usage

```python
from sardis_v2_core.state_machine import PaymentStateMachine, PaymentState

machine = PaymentStateMachine(payment_object_id="po_abc123")
machine.transition(PaymentState.PRESENTED, actor="merchant_xyz")
machine.transition(PaymentState.VERIFIED, actor="merchant_xyz")
machine.transition(PaymentState.LOCKED, actor="system")

# Check available transitions
for state, name in machine.available_transitions():
    print(f"Can {name} → {state.value}")
```
