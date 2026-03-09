"""Merchant execution capability registry.

Rich merchant metadata for intelligent execution mode routing.
"Accepts card" is too coarse — we need per-merchant capability signals.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class MerchantExecutionCapability:
    """Per-merchant capability signals for execution mode routing."""

    merchant_id: str = field(
        default_factory=lambda: f"mec_{uuid.uuid4().hex[:12]}"
    )
    domain: str = ""

    # Capability flags
    accepts_native_crypto: bool = False
    accepts_card: bool = True
    supports_delegated_card: bool = False
    supported_networks: list[str] = field(default_factory=list)
    supports_trusted_agent: bool = False
    supports_tokenized_delegation: bool = False

    # Settlement
    settlement_preference: str = "any"  # crypto, fiat, any

    # Provenance
    first_seen: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    last_verified: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    capability_source: str = "manual"  # manual, discovery, network_api, browser_agent, provider_registry
    verification_status: str = "unverified"  # unverified, inferred, partner_confirmed, network_confirmed
    confidence: float = 0.5  # 0.0–1.0
    risk_category: str | None = None

    # Extra
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_mode(self, mode: str) -> bool:
        """Check if merchant supports a given execution mode."""
        if mode == "native_crypto":
            return self.accepts_native_crypto
        if mode == "offramp_settlement":
            return self.accepts_card  # offramp settles to fiat
        if mode == "delegated_card":
            return self.supports_delegated_card
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "domain": self.domain,
            "accepts_native_crypto": self.accepts_native_crypto,
            "accepts_card": self.accepts_card,
            "supports_delegated_card": self.supports_delegated_card,
            "supported_networks": self.supported_networks,
            "supports_trusted_agent": self.supports_trusted_agent,
            "supports_tokenized_delegation": self.supports_tokenized_delegation,
            "settlement_preference": self.settlement_preference,
            "capability_source": self.capability_source,
            "verification_status": self.verification_status,
            "confidence": self.confidence,
            "risk_category": self.risk_category,
        }


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class MerchantCapabilityStore(Protocol):
    async def get(self, merchant_id: str) -> MerchantExecutionCapability | None: ...
    async def get_by_domain(self, domain: str) -> MerchantExecutionCapability | None: ...
    async def upsert(self, capability: MerchantExecutionCapability) -> None: ...
    async def supports_mode(self, merchant_id: str, mode: str) -> bool: ...


# ---------------------------------------------------------------------------
# In-memory implementation (dev / test)
# ---------------------------------------------------------------------------

class InMemoryMerchantCapabilityStore:
    def __init__(self) -> None:
        self._by_id: dict[str, MerchantExecutionCapability] = {}
        self._by_domain: dict[str, str] = {}  # domain -> merchant_id

    async def get(self, merchant_id: str) -> MerchantExecutionCapability | None:
        return self._by_id.get(merchant_id)

    async def get_by_domain(self, domain: str) -> MerchantExecutionCapability | None:
        mid = self._by_domain.get(domain)
        if mid is None:
            return None
        return self._by_id.get(mid)

    async def upsert(self, capability: MerchantExecutionCapability) -> None:
        self._by_id[capability.merchant_id] = capability
        if capability.domain:
            self._by_domain[capability.domain] = capability.merchant_id

    async def supports_mode(self, merchant_id: str, mode: str) -> bool:
        cap = self._by_id.get(merchant_id)
        if cap is None:
            return False
        return cap.supports_mode(mode)


# ---------------------------------------------------------------------------
# PostgreSQL implementation (production)
# ---------------------------------------------------------------------------

class PostgresMerchantCapabilityStore:
    def __init__(self, pool) -> None:
        self._pool = pool

    def _row_to_cap(self, row: dict) -> MerchantExecutionCapability:
        meta = row.get("metadata") or {}
        if isinstance(meta, str):
            import json
            meta = json.loads(meta)
        return MerchantExecutionCapability(
            merchant_id=row["merchant_id"],
            domain=row.get("domain") or "",
            accepts_native_crypto=row.get("accepts_native_crypto", False),
            accepts_card=row.get("accepts_card", True),
            supports_delegated_card=row.get("supports_delegated_card", False),
            supported_networks=list(row.get("supported_networks") or []),
            supports_trusted_agent=row.get("supports_trusted_agent", False),
            supports_tokenized_delegation=row.get("supports_tokenized_delegation", False),
            settlement_preference=row.get("settlement_preference", "any"),
            first_seen=row.get("first_seen", datetime.now(UTC)),
            last_verified=row.get("last_verified", datetime.now(UTC)),
            capability_source=row.get("capability_source", "manual"),
            verification_status=row.get("verification_status", "unverified"),
            confidence=float(row.get("confidence", 0.5)),
            risk_category=row.get("risk_category"),
            metadata=meta,
        )

    async def get(self, merchant_id: str) -> MerchantExecutionCapability | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM merchant_capabilities WHERE merchant_id = $1",
                merchant_id,
            )
        if row is None:
            return None
        return self._row_to_cap(dict(row))

    async def get_by_domain(self, domain: str) -> MerchantExecutionCapability | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM merchant_capabilities WHERE domain = $1",
                domain,
            )
        if row is None:
            return None
        return self._row_to_cap(dict(row))

    async def upsert(self, capability: MerchantExecutionCapability) -> None:
        import json
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO merchant_capabilities
                    (merchant_id, domain, accepts_native_crypto, accepts_card,
                     supports_delegated_card, supported_networks,
                     supports_trusted_agent, supports_tokenized_delegation,
                     settlement_preference, capability_source,
                     verification_status, confidence, risk_category, metadata)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (merchant_id) DO UPDATE SET
                    domain = EXCLUDED.domain,
                    accepts_native_crypto = EXCLUDED.accepts_native_crypto,
                    accepts_card = EXCLUDED.accepts_card,
                    supports_delegated_card = EXCLUDED.supports_delegated_card,
                    supported_networks = EXCLUDED.supported_networks,
                    supports_trusted_agent = EXCLUDED.supports_trusted_agent,
                    supports_tokenized_delegation = EXCLUDED.supports_tokenized_delegation,
                    settlement_preference = EXCLUDED.settlement_preference,
                    capability_source = EXCLUDED.capability_source,
                    verification_status = EXCLUDED.verification_status,
                    confidence = EXCLUDED.confidence,
                    risk_category = EXCLUDED.risk_category,
                    metadata = EXCLUDED.metadata,
                    last_verified = NOW(),
                    updated_at = NOW()
                """,
                capability.merchant_id,
                capability.domain,
                capability.accepts_native_crypto,
                capability.accepts_card,
                capability.supports_delegated_card,
                capability.supported_networks,
                capability.supports_trusted_agent,
                capability.supports_tokenized_delegation,
                capability.settlement_preference,
                capability.capability_source,
                capability.verification_status,
                capability.confidence,
                capability.risk_category,
                json.dumps(capability.metadata),
            )

    async def supports_mode(self, merchant_id: str, mode: str) -> bool:
        cap = await self.get(merchant_id)
        if cap is None:
            return False
        return cap.supports_mode(mode)
