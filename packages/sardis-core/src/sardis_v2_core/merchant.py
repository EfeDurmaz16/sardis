"""Merchant domain model and repository for Pay with Sardis."""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from .database import Database


def _generate_external_id(prefix: str = "merch") -> str:
    return f"{prefix}_{secrets.token_hex(12)}"


def _generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_hex(24)}"


def _generate_client_secret() -> str:
    return secrets.token_urlsafe(32)


@dataclass(slots=True)
class Merchant:
    """A merchant registered for Pay with Sardis."""
    merchant_id: str = field(default_factory=lambda: _generate_external_id("merch"))
    org_id: Optional[str] = None
    name: str = ""
    logo_url: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: str = field(default_factory=_generate_webhook_secret)
    settlement_preference: str = "usdc"  # usdc | fiat
    settlement_wallet_id: Optional[str] = None
    bank_account: dict[str, Any] = field(default_factory=dict)
    mcc_code: Optional[str] = None
    category: Optional[str] = None
    platform_fee_bps: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class MerchantCheckoutSession:
    """A checkout session for merchant payments."""
    session_id: str = field(default_factory=lambda: _generate_external_id("mcs"))
    client_secret: str = field(default_factory=_generate_client_secret)
    merchant_id: str = ""
    payer_wallet_id: Optional[str] = None
    payer_wallet_address: Optional[str] = None
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    description: Optional[str] = None
    status: str = "pending"  # pending|funded|paid|settled|expired|failed
    payment_method: Optional[str] = None  # wallet|fund_and_pay
    tx_hash: Optional[str] = None
    settlement_tx_hash: Optional[str] = None
    settlement_status: Optional[str] = None
    offramp_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    platform_fee_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    net_amount: Optional[Decimal] = None
    embed_origin: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class MerchantCheckoutLink:
    """A reusable checkout link for merchant payments."""
    link_id: str = field(default_factory=lambda: _generate_external_id("mcl"))
    merchant_id: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    description: Optional[str] = None
    slug: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Column names used in SELECT for sessions (shared across queries)
_SESSION_COLUMNS = """
    s.session_id, s.client_secret, m.external_id AS merchant_id,
    s.payer_wallet_id, s.payer_wallet_address, s.amount, s.currency, s.description,
    s.status, s.payment_method, s.tx_hash,
    s.settlement_tx_hash, s.settlement_status, s.offramp_id,
    s.success_url, s.cancel_url, s.metadata,
    s.expires_at, s.idempotency_key,
    s.platform_fee_amount, s.net_amount, s.embed_origin,
    s.created_at, s.updated_at
"""


class MerchantRepository:
    """CRUD operations for merchants using shared Database pool."""

    # ── Merchant CRUD ──────────────────────────────────────────────

    async def create_merchant(self, merchant: Merchant) -> Merchant:
        import json
        await Database.execute(
            """
            INSERT INTO merchants (external_id, org_id, name, logo_url,
                webhook_url, webhook_secret, settlement_preference,
                settlement_wallet_id, bank_account, mcc_code, category,
                platform_fee_bps, is_active)
            VALUES ($1,
                (SELECT id FROM organizations WHERE external_id = $2),
                $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, $12, $13)
            """,
            merchant.merchant_id,
            merchant.org_id,
            merchant.name,
            merchant.logo_url,
            merchant.webhook_url,
            merchant.webhook_secret,
            merchant.settlement_preference,
            merchant.settlement_wallet_id,
            json.dumps(merchant.bank_account),
            merchant.mcc_code,
            merchant.category,
            merchant.platform_fee_bps,
            merchant.is_active,
        )
        return merchant

    async def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        row = await Database.fetchrow(
            """
            SELECT m.external_id, o.external_id AS org_ext_id, m.name, m.logo_url,
                m.webhook_url, m.webhook_secret, m.settlement_preference,
                m.settlement_wallet_id, m.bank_account, m.mcc_code, m.category,
                m.platform_fee_bps, m.is_active, m.created_at, m.updated_at
            FROM merchants m
            LEFT JOIN organizations o ON o.id = m.org_id
            WHERE m.external_id = $1
            """,
            merchant_id,
        )
        if not row:
            return None
        return self._row_to_merchant(row)

    async def list_merchants(self, org_id: str) -> list[Merchant]:
        rows = await Database.fetch(
            """
            SELECT m.external_id, o.external_id AS org_ext_id, m.name, m.logo_url,
                m.webhook_url, m.webhook_secret, m.settlement_preference,
                m.settlement_wallet_id, m.bank_account, m.mcc_code, m.category,
                m.platform_fee_bps, m.is_active, m.created_at, m.updated_at
            FROM merchants m
            LEFT JOIN organizations o ON o.id = m.org_id
            WHERE o.external_id = $1
            ORDER BY m.created_at DESC
            """,
            org_id,
        )
        return [self._row_to_merchant(r) for r in rows]

    _MERCHANT_UPDATABLE = frozenset({
        "name", "logo_url", "webhook_url", "webhook_secret",
        "settlement_preference", "settlement_wallet_id", "bank_account",
        "mcc_code", "category", "platform_fee_bps", "is_active",
    })

    async def update_merchant(self, merchant_id: str, **kwargs: Any) -> Optional[Merchant]:
        import json
        sets: list[str] = []
        args: list[Any] = []
        idx = 1
        for key, val in kwargs.items():
            if key not in self._MERCHANT_UPDATABLE:
                raise ValueError(f"Invalid merchant field: {key}")
            if key == "bank_account":
                val = json.dumps(val)
                sets.append(f"bank_account = ${idx}::jsonb")
            else:
                sets.append(f"{key} = ${idx}")
            args.append(val)
            idx += 1
        if not sets:
            return await self.get_merchant(merchant_id)
        sets.append(f"updated_at = NOW()")
        args.append(merchant_id)
        await Database.execute(
            f"UPDATE merchants SET {', '.join(sets)} WHERE external_id = ${idx}",
            *args,
        )
        return await self.get_merchant(merchant_id)

    # ── Session CRUD ───────────────────────────────────────────────

    async def create_session(self, session: MerchantCheckoutSession) -> MerchantCheckoutSession:
        import json
        await Database.execute(
            """
            INSERT INTO merchant_checkout_sessions
                (session_id, client_secret, merchant_id, payer_wallet_id,
                 amount, currency, description, status, payment_method,
                 success_url, cancel_url, metadata, expires_at,
                 platform_fee_amount, net_amount, embed_origin)
            VALUES ($1, $2,
                (SELECT id FROM merchants WHERE external_id = $3),
                $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13,
                $14, $15, $16)
            """,
            session.session_id,
            session.client_secret,
            session.merchant_id,
            session.payer_wallet_id,
            session.amount,
            session.currency,
            session.description,
            session.status,
            session.payment_method,
            session.success_url,
            session.cancel_url,
            json.dumps(session.metadata),
            session.expires_at,
            session.platform_fee_amount,
            session.net_amount,
            session.embed_origin,
        )
        return session

    async def get_session(self, session_id: str) -> Optional[MerchantCheckoutSession]:
        row = await Database.fetchrow(
            f"""
            SELECT {_SESSION_COLUMNS}
            FROM merchant_checkout_sessions s
            JOIN merchants m ON m.id = s.merchant_id
            WHERE s.session_id = $1
            """,
            session_id,
        )
        if not row:
            return None
        return self._row_to_session(row)

    async def get_session_by_secret(self, client_secret: str) -> Optional[MerchantCheckoutSession]:
        """Look up session by client_secret (for public endpoints)."""
        row = await Database.fetchrow(
            f"""
            SELECT {_SESSION_COLUMNS}
            FROM merchant_checkout_sessions s
            JOIN merchants m ON m.id = s.merchant_id
            WHERE s.client_secret = $1
            """,
            client_secret,
        )
        if not row:
            return None
        return self._row_to_session(row)

    async def get_session_for_update(self, session_id: str) -> Optional[MerchantCheckoutSession]:
        """Get session with row lock (FOR UPDATE NOWAIT) to prevent concurrent payment."""
        row = await Database.fetchrow(
            f"""
            SELECT {_SESSION_COLUMNS}
            FROM merchant_checkout_sessions s
            JOIN merchants m ON m.id = s.merchant_id
            WHERE s.session_id = $1
            FOR UPDATE OF s NOWAIT
            """,
            session_id,
        )
        if not row:
            return None
        return self._row_to_session(row)

    _SESSION_UPDATABLE = frozenset({
        "payer_wallet_id", "payer_wallet_address", "status", "payment_method",
        "tx_hash", "settlement_tx_hash", "settlement_status", "offramp_id",
        "metadata", "idempotency_key", "platform_fee_amount", "net_amount",
    })

    async def update_session(self, session_id: str, **kwargs: Any) -> None:
        import json
        sets: list[str] = []
        args: list[Any] = []
        idx = 1
        for key, val in kwargs.items():
            if key not in self._SESSION_UPDATABLE:
                raise ValueError(f"Invalid session field: {key}")
            if key == "metadata":
                val = json.dumps(val)
                sets.append(f"metadata = ${idx}::jsonb")
            else:
                sets.append(f"{key} = ${idx}")
            args.append(val)
            idx += 1
        if not sets:
            return
        sets.append("updated_at = NOW()")
        args.append(session_id)
        await Database.execute(
            f"UPDATE merchant_checkout_sessions SET {', '.join(sets)} WHERE session_id = ${idx}",
            *args,
        )

    async def list_sessions_by_merchant(
        self, merchant_id: str, status: Optional[str] = None, limit: int = 50
    ) -> list[MerchantCheckoutSession]:
        if status:
            rows = await Database.fetch(
                f"""
                SELECT {_SESSION_COLUMNS}
                FROM merchant_checkout_sessions s
                JOIN merchants m ON m.id = s.merchant_id
                WHERE m.external_id = $1 AND s.status = $2
                ORDER BY s.created_at DESC LIMIT $3
                """,
                merchant_id, status, limit,
            )
        else:
            rows = await Database.fetch(
                f"""
                SELECT {_SESSION_COLUMNS}
                FROM merchant_checkout_sessions s
                JOIN merchants m ON m.id = s.merchant_id
                WHERE m.external_id = $1
                ORDER BY s.created_at DESC LIMIT $2
                """,
                merchant_id, limit,
            )
        return [self._row_to_session(r) for r in rows]

    async def get_processing_settlements(self) -> list[MerchantCheckoutSession]:
        """Get sessions with settlement_status = 'processing' for polling."""
        rows = await Database.fetch(
            f"""
            SELECT {_SESSION_COLUMNS}
            FROM merchant_checkout_sessions s
            JOIN merchants m ON m.id = s.merchant_id
            WHERE s.settlement_status = 'processing'
            ORDER BY s.created_at ASC
            """
        )
        return [self._row_to_session(r) for r in rows]

    # ── Checkout Links CRUD ────────────────────────────────────────

    async def create_checkout_link(self, link: MerchantCheckoutLink) -> MerchantCheckoutLink:
        await Database.execute(
            """
            INSERT INTO merchant_checkout_links
                (link_id, merchant_id, amount, currency, description, slug, is_active)
            VALUES ($1,
                (SELECT id FROM merchants WHERE external_id = $2),
                $3, $4, $5, $6, $7)
            """,
            link.link_id,
            link.merchant_id,
            link.amount,
            link.currency,
            link.description,
            link.slug,
            link.is_active,
        )
        return link

    async def get_checkout_link(self, link_id: str) -> Optional[MerchantCheckoutLink]:
        row = await Database.fetchrow(
            """
            SELECT l.link_id, m.external_id AS merchant_id,
                l.amount, l.currency, l.description, l.slug,
                l.is_active, l.created_at, l.updated_at
            FROM merchant_checkout_links l
            JOIN merchants m ON m.id = l.merchant_id
            WHERE l.link_id = $1
            """,
            link_id,
        )
        if not row:
            return None
        return self._row_to_link(row)

    async def get_checkout_link_by_slug(self, slug: str) -> Optional[MerchantCheckoutLink]:
        row = await Database.fetchrow(
            """
            SELECT l.link_id, m.external_id AS merchant_id,
                l.amount, l.currency, l.description, l.slug,
                l.is_active, l.created_at, l.updated_at
            FROM merchant_checkout_links l
            JOIN merchants m ON m.id = l.merchant_id
            WHERE l.slug = $1 AND l.is_active = TRUE
            """,
            slug,
        )
        if not row:
            return None
        return self._row_to_link(row)

    async def list_checkout_links(self, merchant_id: str) -> list[MerchantCheckoutLink]:
        rows = await Database.fetch(
            """
            SELECT l.link_id, m.external_id AS merchant_id,
                l.amount, l.currency, l.description, l.slug,
                l.is_active, l.created_at, l.updated_at
            FROM merchant_checkout_links l
            JOIN merchants m ON m.id = l.merchant_id
            WHERE m.external_id = $1
            ORDER BY l.created_at DESC
            """,
            merchant_id,
        )
        return [self._row_to_link(r) for r in rows]

    async def update_checkout_link(self, link_id: str, **kwargs: Any) -> Optional[MerchantCheckoutLink]:
        allowed = {"amount", "currency", "description", "slug", "is_active"}
        sets: list[str] = []
        args: list[Any] = []
        idx = 1
        for key, val in kwargs.items():
            if key not in allowed:
                raise ValueError(f"Invalid link field: {key}")
            sets.append(f"{key} = ${idx}")
            args.append(val)
            idx += 1
        if not sets:
            return await self.get_checkout_link(link_id)
        sets.append("updated_at = NOW()")
        args.append(link_id)
        await Database.execute(
            f"UPDATE merchant_checkout_links SET {', '.join(sets)} WHERE link_id = ${idx}",
            *args,
        )
        return await self.get_checkout_link(link_id)

    async def delete_checkout_link(self, link_id: str) -> bool:
        result = await Database.execute(
            "DELETE FROM merchant_checkout_links WHERE link_id = $1",
            link_id,
        )
        return result is not None

    # ── Webhook Delivery Tracking ──────────────────────────────────

    async def record_webhook_delivery(
        self, event_id: str, merchant_id: str, event_type: str, payload: dict
    ) -> bool:
        """Record a webhook delivery. Returns False if event_id already exists (dedup)."""
        import json
        try:
            await Database.execute(
                """
                INSERT INTO merchant_webhook_deliveries
                    (event_id, merchant_id, event_type, payload, status, attempts)
                VALUES ($1,
                    (SELECT id FROM merchants WHERE external_id = $2),
                    $3, $4::jsonb, 'pending', 0)
                """,
                event_id, merchant_id, event_type, json.dumps(payload, default=str),
            )
            return True
        except Exception:
            # Unique constraint violation = duplicate
            return False

    async def update_webhook_delivery(
        self, event_id: str, status: str, attempts: int
    ) -> None:
        await Database.execute(
            """
            UPDATE merchant_webhook_deliveries
            SET status = $1, attempts = $2, last_attempt_at = NOW()
            WHERE event_id = $3
            """,
            status, attempts, event_id,
        )

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _row_to_merchant(row) -> Merchant:
        import json
        bank = row["bank_account"]
        if isinstance(bank, str):
            bank = json.loads(bank)
        return Merchant(
            merchant_id=row["external_id"],
            org_id=row["org_ext_id"],
            name=row["name"],
            logo_url=row.get("logo_url"),
            webhook_url=row.get("webhook_url"),
            webhook_secret=row.get("webhook_secret", ""),
            settlement_preference=row["settlement_preference"],
            settlement_wallet_id=row.get("settlement_wallet_id"),
            bank_account=bank if isinstance(bank, dict) else {},
            mcc_code=row.get("mcc_code"),
            category=row.get("category"),
            platform_fee_bps=row.get("platform_fee_bps", 0),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_session(row) -> MerchantCheckoutSession:
        import json
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        net = row.get("net_amount")
        return MerchantCheckoutSession(
            session_id=row["session_id"],
            client_secret=row.get("client_secret", ""),
            merchant_id=row["merchant_id"],
            payer_wallet_id=row.get("payer_wallet_id"),
            payer_wallet_address=row.get("payer_wallet_address"),
            amount=Decimal(str(row["amount"])),
            currency=row["currency"],
            description=row.get("description"),
            status=row["status"],
            payment_method=row.get("payment_method"),
            tx_hash=row.get("tx_hash"),
            settlement_tx_hash=row.get("settlement_tx_hash"),
            settlement_status=row.get("settlement_status"),
            offramp_id=row.get("offramp_id"),
            success_url=row.get("success_url"),
            cancel_url=row.get("cancel_url"),
            metadata=meta if isinstance(meta, dict) else {},
            expires_at=row.get("expires_at"),
            idempotency_key=row.get("idempotency_key"),
            platform_fee_amount=Decimal(str(row.get("platform_fee_amount") or 0)),
            net_amount=Decimal(str(net)) if net is not None else None,
            embed_origin=row.get("embed_origin"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_link(row) -> MerchantCheckoutLink:
        return MerchantCheckoutLink(
            link_id=row["link_id"],
            merchant_id=row["merchant_id"],
            amount=Decimal(str(row["amount"])),
            currency=row["currency"],
            description=row.get("description"),
            slug=row["slug"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
