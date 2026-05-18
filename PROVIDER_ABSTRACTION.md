# Provider Abstraction

Sardis is rail-agnostic. It should not force agents to use one wallet, card, stablecoin, ACH, swap, KYC, or compliance provider.

Providers are execution dependencies beneath the authority layer. Sardis should decide whether an action is authorized before a provider is allowed to execute it.

## Public Contract

Public provider adapters should expose:

- declared capabilities
- deterministic request and response models
- idempotency behavior
- webhook verification requirements
- error and retry semantics
- audit/evidence fields
- sandbox or simulator mode

## Private Operations

Managed-provider operations should stay private when they include:

- production credentials
- vendor-specific routing strategy
- customer-specific limits
- pricing or commercial terms
- internal support procedures
- incident response playbooks

## Safety Invariant

Provider execution must never bypass mandate, policy, approval, revocation, idempotency, and evidence checks.
