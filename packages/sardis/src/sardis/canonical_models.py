"""Canonical typed domain-model index for Sardis.

Single source-of-truth lookup for the entities the Phase-2 persistence MAP
flagged as "defined twice" (Agent, Wallet, Payment, Group, plus the
DTO/domain pairs). This module is **additive and behaviour-identical**: it does
NOT define new types and does NOT change any field, wire shape, or DB shape. It
re-exports the already-canonical class for each entity so callers and reviewers
have exactly one place to answer "which class is canonical for X, and for whom".

## Why two layers exist (and are NOT dead duplication)

Per `docs/productization/PHASE2_MAP.md` §3, Sardis has two parallel model layers
that serve **different consumers** and have **different field semantics**:

- **Engine / domain layer** — `sardis.core.*` (pydantic `BaseModel` / dataclass).
  Used by the orchestrator, policy engine, jobs, and `apps/api` routes. Carries
  money-safety and engine-internal state the public client must never see, e.g.
  `Wallet.is_frozen` / `freeze()` / `unfreeze()` (wallet freeze is a money-safety
  control), CDP/x402/circle provider fields, `Agent.spending_limits` /
  `AgentPolicy` / KYA fields, `PaymentObject` lifecycle + `PrivacyTier`.
  **Canonical engine re-export point: `sardis.core` (`core/__init__.py`).**

- **Public SDK DTO layer** — `sardis.models.*` (pydantic `SardisModel`). Used by
  the public SDK client (`sardis.resources.*`, `sardis.cards.*`, `sardis.ledger.*`).
  Wire-stable DTOs with API field aliases (e.g. `Agent.agent_id` aliased to `id`,
  `Payment.payment_id` aliased to `id`), `str`-typed tokens, no engine/money-safety
  internals. **Canonical DTO re-export point: `sardis.models` (`models/__init__.py`).**

These are NOT accidental copies: a field-level merge would either leak engine /
money-safety state into the public wire DTO or strip it from the engine domain
model. The MAP ranks collapsing them as **medium-to-money-path-risky**, requiring
an explicit adapter/mapping layer (future work), never a deletion. This index
therefore establishes the single source-of-truth **without** changing semantics.

## How to use this module

    from sardis.canonical_models import EngineAgent, SdkAgent
    from sardis.canonical_models import EngineWallet, SdkWallet

`Engine*` names always resolve to the `sardis.core` domain class; `Sdk*` names
always resolve to the `sardis.models` DTO. Bare names (`Agent`, `Wallet`, ...)
resolve to the **engine domain** class, because the engine layer is the one used
on the money path / by `apps/api` and the orchestrator — i.e. the authoritative
internal model. Public-client code should keep importing from `sardis.models`.

## DONE_WITH_CONCERNS (deferred field-level consolidation)

The actual field-level collapse of each pair into one type is intentionally
deferred (MAP §3, §6c). Specifically NOT done here, by design:

- `Wallet` — engine adds `is_frozen`/`freeze()`/`unfreeze()` (money-safety) and
  provider fields the DTO lacks. Collapsing risks money-path behaviour. DEFER.
- `Payment` (SDK DTO) vs `PaymentObject` (engine) — structurally different
  lifecycle objects; MAP: "do NOT naively merge". DEFER.
- `TokenLimit` — engine `token: TokenType` vs DTO `token: str`. Type change on
  merge → wire/semantic shift. DEFER.
- `Agent`, `Group`, `Card/Hold/Policy/Treasury/Webhook/Marketplace` — each is a
  DTO-vs-domain pair with diverging fields. DEFER (needs adapter layer).
"""
from __future__ import annotations

# --- Engine / domain layer (sardis.core) — money-path / orchestrator canonical ---
from sardis.core import (
    Agent as EngineAgent,
)
from sardis.core import (
    AgentGroup as EngineAgentGroup,
)
from sardis.core import (
    AgentPolicy,
    SpendingLimits,
)
from sardis.core import (
    PaymentObject as EnginePayment,
)
from sardis.core import (
    TokenBalance as EngineTokenBalance,
)
from sardis.core import (
    TokenLimit as EngineTokenLimit,
)
from sardis.core import (
    Wallet as EngineWallet,
)

# --- Public SDK DTO layer (sardis.models) — wire-stable client canonical ---
from sardis.models import (
    Agent as SdkAgent,
)
from sardis.models import (
    AgentGroupModel as SdkAgentGroup,
)
from sardis.models import (
    Payment as SdkPayment,
)
from sardis.models import (
    PaymentStatus as SdkPaymentStatus,
)
from sardis.models import (
    TokenBalance as SdkTokenBalance,
)
from sardis.models import (
    TokenLimit as SdkTokenLimit,
)
from sardis.models import (
    Wallet as SdkWallet,
)

# --- Bare canonical names resolve to the ENGINE domain class ---
# (engine is authoritative on the money path / orchestrator / apps-api).
Agent = EngineAgent
Wallet = EngineWallet
Payment = EnginePayment
AgentGroup = EngineAgentGroup
TokenLimit = EngineTokenLimit
TokenBalance = EngineTokenBalance

__all__ = [
    # bare canonical (engine domain)
    "Agent",
    "Wallet",
    "Payment",
    "AgentGroup",
    "TokenLimit",
    "TokenBalance",
    "AgentPolicy",
    "SpendingLimits",
    # explicit engine-domain
    "EngineAgent",
    "EngineWallet",
    "EnginePayment",
    "EngineAgentGroup",
    "EngineTokenLimit",
    "EngineTokenBalance",
    # explicit public-SDK DTO
    "SdkAgent",
    "SdkWallet",
    "SdkPayment",
    "SdkPaymentStatus",
    "SdkAgentGroup",
    "SdkTokenLimit",
    "SdkTokenBalance",
]
