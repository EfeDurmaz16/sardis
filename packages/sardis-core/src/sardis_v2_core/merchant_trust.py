"""Merchant trust scoring — compute and manage per-merchant trust levels.

Trust scores are derived from transaction history, dispute rates, and manual
verification. Scores feed directly into approval threshold adjustments, giving
high-trust merchants more headroom and flagging unknown/new merchants for
closer scrutiny.

Usage:
    from sardis_v2_core.merchant_trust import MerchantTrustService, MerchantTrustLevel

    service = MerchantTrustService(db)
    profile = await service.get_or_create_profile("merchant_stripe_abc123")
    threshold = await service.get_approval_threshold_for_merchant(
        "merchant_stripe_abc123", base_threshold=Decimal("500")
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from .database import Database

logger = logging.getLogger("sardis.core.merchant_trust")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MerchantTrustLevel(str, Enum):
    """Merchant trust tier derived from transaction history."""

    UNKNOWN = "unknown"   # No history — first-seen merchant
    LOW = "low"           # < 5 transactions
    MEDIUM = "medium"     # 5-50 transactions, < 2 % dispute rate
    HIGH = "high"         # 50+ transactions, < 1 % dispute rate
    VERIFIED = "verified" # Manual verification + meets HIGH criteria


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class MerchantProfile:
    """Snapshot of a merchant's trust state."""

    merchant_id: str
    merchant_name: str | None
    category: str | None
    mcc_code: str | None
    trust_level: MerchantTrustLevel
    trust_score: float          # 0.0 – 1.0
    first_seen: datetime
    last_seen: datetime
    transaction_count: int
    total_volume: Decimal
    dispute_count: int
    dispute_rate: float         # 0.0 – 1.0 (fraction of txns that were disputed)
    is_first_seen: bool         # True when this is the very first transaction


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MerchantTrustService:
    """Compute and manage merchant trust levels backed by PostgreSQL."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    async def get_profile(self, merchant_id: str) -> MerchantProfile | None:
        """Return the stored profile for *merchant_id*, or ``None`` if absent."""
        row = await Database.fetchrow(
            """
            SELECT merchant_id, merchant_name, category, mcc_code,
                   trust_level, trust_score, first_seen, last_seen,
                   transaction_count, total_volume, dispute_count,
                   verified_at
            FROM merchant_trust_profiles
            WHERE merchant_id = $1
            """,
            merchant_id,
        )
        if row is None:
            return None
        return _row_to_profile(row)

    async def get_or_create_profile(
        self,
        merchant_id: str,
        merchant_name: str | None = None,
        category: str | None = None,
        mcc_code: str | None = None,
    ) -> MerchantProfile:
        """Return the existing profile or insert a new one with UNKNOWN trust.

        The returned profile's ``is_first_seen`` flag is ``True`` only when
        the row was just created.
        """
        existing = await self.get_profile(merchant_id)
        if existing is not None:
            existing.is_first_seen = False
            return existing

        now = datetime.now(UTC)
        await Database.execute(
            """
            INSERT INTO merchant_trust_profiles (
                merchant_id, merchant_name, category, mcc_code,
                trust_level, trust_score, first_seen, last_seen,
                transaction_count, total_volume, dispute_count,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4,
                'unknown', 0.3, $5, $5,
                0, 0, 0,
                $5, $5
            )
            ON CONFLICT (merchant_id) DO NOTHING
            """,
            merchant_id,
            merchant_name,
            category,
            mcc_code,
            now,
        )

        profile = MerchantProfile(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            category=category,
            mcc_code=mcc_code,
            trust_level=MerchantTrustLevel.UNKNOWN,
            trust_score=0.3,
            first_seen=now,
            last_seen=now,
            transaction_count=0,
            total_volume=Decimal("0"),
            dispute_count=0,
            dispute_rate=0.0,
            is_first_seen=True,
        )
        return profile

    # ------------------------------------------------------------------
    # Mutation API
    # ------------------------------------------------------------------

    async def record_transaction(
        self,
        merchant_id: str,
        amount: Decimal,
        success: bool = True,
    ) -> MerchantProfile:
        """Increment transaction counters and recalculate trust.

        If *success* is ``False`` the transaction count still grows (so the
        merchant's history is reflected accurately) but the amount is not
        added to *total_volume*.
        """
        profile = await self.get_or_create_profile(merchant_id)

        new_count = profile.transaction_count + 1
        new_volume = profile.total_volume + amount if success else profile.total_volume
        now = datetime.now(UTC)

        # Recompute dispute rate with the new count denominator
        new_dispute_rate = (
            profile.dispute_count / new_count if new_count > 0 else 0.0
        )

        # Build an updated profile for score / level computation
        updated = MerchantProfile(
            merchant_id=profile.merchant_id,
            merchant_name=profile.merchant_name,
            category=profile.category,
            mcc_code=profile.mcc_code,
            trust_level=profile.trust_level,
            trust_score=profile.trust_score,
            first_seen=profile.first_seen,
            last_seen=now,
            transaction_count=new_count,
            total_volume=new_volume,
            dispute_count=profile.dispute_count,
            dispute_rate=new_dispute_rate,
            is_first_seen=False,
        )
        updated.trust_level = self.compute_trust_level(updated)
        updated.trust_score = self.compute_trust_score(updated)

        await Database.execute(
            """
            UPDATE merchant_trust_profiles
            SET transaction_count = $2,
                total_volume      = $3,
                last_seen         = $4,
                trust_level       = $5,
                trust_score       = $6,
                updated_at        = $4
            WHERE merchant_id = $1
            """,
            merchant_id,
            new_count,
            new_volume,
            now,
            updated.trust_level.value,
            updated.trust_score,
        )

        logger.info(
            "Merchant transaction recorded",
            extra={
                "merchant_id": merchant_id,
                "transaction_count": new_count,
                "trust_level": updated.trust_level.value,
                "trust_score": round(updated.trust_score, 4),
            },
        )
        return updated

    async def record_dispute(self, merchant_id: str) -> MerchantProfile:
        """Increment the dispute counter and recalculate trust."""
        profile = await self.get_or_create_profile(merchant_id)

        new_dispute_count = profile.dispute_count + 1
        new_dispute_rate = (
            new_dispute_count / profile.transaction_count
            if profile.transaction_count > 0
            else 1.0
        )
        now = datetime.now(UTC)

        updated = MerchantProfile(
            merchant_id=profile.merchant_id,
            merchant_name=profile.merchant_name,
            category=profile.category,
            mcc_code=profile.mcc_code,
            trust_level=profile.trust_level,
            trust_score=profile.trust_score,
            first_seen=profile.first_seen,
            last_seen=now,
            transaction_count=profile.transaction_count,
            total_volume=profile.total_volume,
            dispute_count=new_dispute_count,
            dispute_rate=new_dispute_rate,
            is_first_seen=False,
        )
        updated.trust_level = self.compute_trust_level(updated)
        updated.trust_score = self.compute_trust_score(updated)

        await Database.execute(
            """
            UPDATE merchant_trust_profiles
            SET dispute_count = $2,
                trust_level   = $3,
                trust_score   = $4,
                last_seen     = $5,
                updated_at    = $5
            WHERE merchant_id = $1
            """,
            merchant_id,
            new_dispute_count,
            updated.trust_level.value,
            updated.trust_score,
            now,
        )

        logger.warning(
            "Merchant dispute recorded",
            extra={
                "merchant_id": merchant_id,
                "dispute_count": new_dispute_count,
                "dispute_rate": round(new_dispute_rate, 4),
                "trust_level": updated.trust_level.value,
            },
        )
        return updated

    async def verify_merchant(self, merchant_id: str) -> MerchantProfile:
        """Manually elevate a merchant to VERIFIED trust (admin action)."""
        profile = await self.get_or_create_profile(merchant_id)
        now = datetime.now(UTC)

        updated = MerchantProfile(
            merchant_id=profile.merchant_id,
            merchant_name=profile.merchant_name,
            category=profile.category,
            mcc_code=profile.mcc_code,
            trust_level=MerchantTrustLevel.VERIFIED,
            trust_score=1.0,
            first_seen=profile.first_seen,
            last_seen=now,
            transaction_count=profile.transaction_count,
            total_volume=profile.total_volume,
            dispute_count=profile.dispute_count,
            dispute_rate=profile.dispute_rate,
            is_first_seen=False,
        )

        await Database.execute(
            """
            UPDATE merchant_trust_profiles
            SET trust_level = 'verified',
                trust_score  = 1.0,
                verified_at  = $2,
                updated_at   = $2
            WHERE merchant_id = $1
            """,
            merchant_id,
            now,
        )

        logger.info(
            "Merchant manually verified",
            extra={"merchant_id": merchant_id},
        )
        return updated

    # ------------------------------------------------------------------
    # Synchronous computation helpers
    # ------------------------------------------------------------------

    def compute_trust_level(self, profile: MerchantProfile) -> MerchantTrustLevel:
        """Derive the qualitative trust tier from profile statistics.

        Rules (evaluated in order):
        - VERIFIED  — already set by manual verification (preserved if score stays high)
        - HIGH      — 50+ transactions AND dispute rate < 1 %
        - MEDIUM    — 5-50 transactions AND dispute rate < 2 %
        - LOW       — 1-4 transactions
        - UNKNOWN   — no transaction history
        """
        # Preserve VERIFIED when it was set externally (score already maxed)
        if profile.trust_level == MerchantTrustLevel.VERIFIED:
            return MerchantTrustLevel.VERIFIED

        if profile.transaction_count == 0:
            return MerchantTrustLevel.UNKNOWN

        if profile.transaction_count < 5:
            return MerchantTrustLevel.LOW

        if profile.transaction_count < 50:
            if profile.dispute_rate < 0.02:
                return MerchantTrustLevel.MEDIUM
            return MerchantTrustLevel.LOW

        # 50+ transactions
        if profile.dispute_rate < 0.01:
            return MerchantTrustLevel.HIGH
        if profile.dispute_rate < 0.02:
            return MerchantTrustLevel.MEDIUM
        return MerchantTrustLevel.LOW

    def compute_trust_score(self, profile: MerchantProfile) -> float:
        """Compute a numeric trust score in [0.0, 1.0].

        Scoring breakdown
        -----------------
        Base                  0.5
        +0.1 per 10 txns      up to +0.3 maximum
        +0.1 if volume > $1k
        +0.1 if volume > $10k
        -0.1 if dispute rate > 1 %
        -0.2 if dispute rate > 2 %
        -0.3 if dispute rate > 5 %

        First-seen merchants (no txns) receive a fixed score of 0.3.
        VERIFIED merchants are always set to 1.0 (handled by verify_merchant).
        """
        if profile.transaction_count == 0:
            return 0.3

        score = 0.5

        # Volume-of-transactions bonus (up to +0.3)
        tx_bonus = min(0.3, (profile.transaction_count // 10) * 0.1)
        score += tx_bonus

        # Volume-of-money bonuses
        volume_float = float(profile.total_volume)
        if volume_float > 10_000 or volume_float > 1_000:
            score += 0.1

        # Dispute rate penalties (cumulative levels)
        if profile.dispute_rate > 0.05:
            score -= 0.3
        elif profile.dispute_rate > 0.02:
            score -= 0.2
        elif profile.dispute_rate > 0.01:
            score -= 0.1

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    async def check_first_seen(self, merchant_id: str) -> bool:
        """Return ``True`` if this merchant has never appeared in the system."""
        row = await Database.fetchrow(
            "SELECT 1 FROM merchant_trust_profiles WHERE merchant_id = $1",
            merchant_id,
        )
        return row is None

    async def get_approval_threshold_for_merchant(
        self,
        merchant_id: str,
        base_threshold: Decimal,
    ) -> Decimal:
        """Adjust the auto-approval amount threshold based on merchant trust.

        A *lower* returned threshold means payments above a smaller amount
        need explicit approval — tighter scrutiny for unknown merchants.

        Multipliers by level:
        - UNKNOWN   × 0.5  (tighter — more likely to trigger approval)
        - LOW       × 0.7
        - MEDIUM    × 1.0  (unchanged)
        - HIGH      × 1.5  (looser)
        - VERIFIED  × 2.0  (most permissive)
        """
        profile = await self.get_profile(merchant_id)

        if profile is None:
            # Treat completely unknown merchants the same as UNKNOWN tier
            return base_threshold * Decimal("0.5")

        multipliers: dict[MerchantTrustLevel, Decimal] = {
            MerchantTrustLevel.UNKNOWN: Decimal("0.5"),
            MerchantTrustLevel.LOW: Decimal("0.7"),
            MerchantTrustLevel.MEDIUM: Decimal("1.0"),
            MerchantTrustLevel.HIGH: Decimal("1.5"),
            MerchantTrustLevel.VERIFIED: Decimal("2.0"),
        }

        multiplier = multipliers.get(profile.trust_level, Decimal("0.5"))
        adjusted = base_threshold * multiplier

        logger.debug(
            "Approval threshold adjusted for merchant",
            extra={
                "merchant_id": merchant_id,
                "trust_level": profile.trust_level.value,
                "base_threshold": str(base_threshold),
                "adjusted_threshold": str(adjusted),
            },
        )
        return adjusted


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_profile(row: object) -> MerchantProfile:
    """Convert a database row mapping to a :class:`MerchantProfile`."""
    tx_count: int = row["transaction_count"]  # type: ignore[index]
    dispute_count: int = row["dispute_count"]  # type: ignore[index]
    dispute_rate: float = dispute_count / tx_count if tx_count > 0 else 0.0

    return MerchantProfile(
        merchant_id=row["merchant_id"],  # type: ignore[index]
        merchant_name=row["merchant_name"],  # type: ignore[index]
        category=row["category"],  # type: ignore[index]
        mcc_code=row["mcc_code"],  # type: ignore[index]
        trust_level=MerchantTrustLevel(row["trust_level"]),  # type: ignore[index]
        trust_score=float(row["trust_score"]),  # type: ignore[index]
        first_seen=row["first_seen"],  # type: ignore[index]
        last_seen=row["last_seen"],  # type: ignore[index]
        transaction_count=tx_count,
        total_volume=Decimal(str(row["total_volume"])),  # type: ignore[index]
        dispute_count=dispute_count,
        dispute_rate=dispute_rate,
        is_first_seen=False,
    )
