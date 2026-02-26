"""PostgreSQL-backed wallet repository."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Any, Literal

from .wallets import Wallet


class PostgresWalletRepository:
    """PostgreSQL wallet repository.

    Maps:
    - Wallet.wallet_id <-> wallets.external_id
    - Wallet.agent_id <-> agents.external_id (via wallets.agent_id FK)

    Stores multi-chain addresses in `wallets.addresses` (JSONB). For backwards
    compatibility, also reads `chain` + `chain_address` if `addresses` is NULL.
    """

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    @staticmethod
    def _wallet_from_row(row: Any, agent_external_id: str) -> Wallet:
        addresses = row.get("addresses")
        if not isinstance(addresses, dict):
            addresses = {}

        # Backwards compatibility
        chain = row.get("chain")
        chain_address = row.get("chain_address")
        if chain and chain_address and chain not in addresses:
            addresses[str(chain)] = str(chain_address)

        return Wallet(
            wallet_id=str(row["external_id"]),
            agent_id=agent_external_id,
            mpc_provider=str(row.get("mpc_provider") or "turnkey"),
            account_type=str(row.get("account_type") or "mpc_v1"),
            addresses=addresses,
            currency=str(row.get("currency") or "USDC"),
            limit_per_tx=Decimal(str(row.get("limit_per_tx") or "100.00")),
            limit_total=Decimal(str(row.get("limit_total") or "1000.00")),
            smart_account_address=row.get("smart_account_address"),
            entrypoint_address=row.get("entrypoint_address"),
            paymaster_enabled=bool(row.get("paymaster_enabled", False)),
            bundler_profile=row.get("bundler_profile"),
            is_active=bool(row.get("is_active", True)),
            is_frozen=bool(row.get("is_frozen", False)),
            frozen_at=row.get("frozen_at"),
            frozen_by=row.get("frozen_by"),
            freeze_reason=row.get("freeze_reason"),
            created_at=row.get("created_at") or datetime.now(timezone.utc),
            updated_at=row.get("updated_at") or datetime.now(timezone.utc),
        )

    async def create(
        self,
        agent_id: str,
        wallet_id: str | None = None,
        mpc_provider: str = "turnkey",
        account_type: Literal["mpc_v1", "erc4337_v2"] = "mpc_v1",
        currency: str = "USDC",
        limit_per_tx: Decimal = Decimal("100.00"),
        limit_total: Decimal = Decimal("1000.00"),
        addresses: Optional[dict[str, str]] = None,
        smart_account_address: Optional[str] = None,
        entrypoint_address: Optional[str] = None,
        paymaster_enabled: bool = False,
        bundler_profile: Optional[str] = None,
    ) -> Wallet:
        pool = await self._get_pool()
        wallet_id = wallet_id or f"wallet_{__import__('uuid').uuid4().hex[:16]}"
        addresses = dict(addresses or {})
        # best-effort compatibility columns
        chain = "base"
        chain_address = addresses.get("base") or addresses.get("base_sepolia")

        async with pool.acquire() as conn:
            async with conn.transaction():
                agent_row = await conn.fetchrow("SELECT id FROM agents WHERE external_id = $1", agent_id)
                if not agent_row:
                    raise ValueError("agent_not_found")
                agent_uuid = str(agent_row["id"])

                import json as _json
                row = await conn.fetchrow(
                    """
                    INSERT INTO wallets (
                        external_id, agent_id, chain_address, chain,
                        mpc_provider, currency, limit_per_tx, limit_total,
                        addresses, is_active, account_type, smart_account_address,
                        entrypoint_address, paymaster_enabled, bundler_profile
                    )
                    VALUES (
                        $1, $2::uuid, $3, $4,
                        $5, $6, $7, $8,
                        $9::jsonb, TRUE, $10, $11, $12, $13, $14
                    )
                    RETURNING external_id, chain_address, chain, mpc_provider, currency,
                              limit_per_tx, limit_total, addresses, account_type,
                              smart_account_address, entrypoint_address, paymaster_enabled, bundler_profile,
                              is_active, is_frozen, frozen_at, frozen_by, freeze_reason,
                              created_at, updated_at
                    """,
                    wallet_id,
                    agent_uuid,
                    chain_address,
                    chain,
                    mpc_provider,
                    currency,
                    str(limit_per_tx),
                    str(limit_total),
                    _json.dumps(addresses),
                    account_type,
                    smart_account_address,
                    entrypoint_address,
                    paymaster_enabled,
                    bundler_profile,
                )
                return self._wallet_from_row(dict(row), agent_id)

    async def get(self, wallet_id: str) -> Optional[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT w.external_id, w.chain_address, w.chain, w.mpc_provider, w.currency,
                       w.limit_per_tx, w.limit_total, w.addresses, w.account_type,
                       w.smart_account_address, w.entrypoint_address, w.paymaster_enabled, w.bundler_profile,
                       w.is_active, w.is_frozen, w.frozen_at, w.frozen_by, w.freeze_reason,
                       w.created_at, w.updated_at,
                       a.external_id AS agent_external_id
                FROM wallets w
                JOIN agents a ON a.id = w.agent_id
                WHERE w.external_id = $1
                """,
                wallet_id,
            )
            if not row:
                return None
            return self._wallet_from_row(dict(row), str(row["agent_external_id"]))

    async def get_by_agent(self, agent_id: str) -> Optional[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT w.external_id, w.chain_address, w.chain, w.mpc_provider, w.currency,
                       w.limit_per_tx, w.limit_total, w.addresses, w.account_type,
                       w.smart_account_address, w.entrypoint_address, w.paymaster_enabled, w.bundler_profile,
                       w.is_active, w.is_frozen, w.frozen_at, w.frozen_by, w.freeze_reason,
                       w.created_at, w.updated_at,
                       a.external_id AS agent_external_id
                FROM wallets w
                JOIN agents a ON a.id = w.agent_id
                WHERE a.external_id = $1
                ORDER BY w.created_at DESC
                LIMIT 1
                """,
                agent_id,
            )
            if not row:
                return None
            return self._wallet_from_row(dict(row), str(row["agent_external_id"]))

    async def list(
        self,
        agent_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            where = []
            params: list[Any] = []
            idx = 1
            if agent_id:
                where.append(f"a.external_id = ${idx}")
                params.append(agent_id)
                idx += 1
            if is_active is not None:
                where.append(f"w.is_active = ${idx}")
                params.append(is_active)
                idx += 1
            where_sql = ("WHERE " + " AND ".join(where)) if where else ""
            rows = await conn.fetch(
                f"""
                SELECT w.external_id, w.chain_address, w.chain, w.mpc_provider, w.currency,
                       w.limit_per_tx, w.limit_total, w.addresses, w.account_type,
                       w.smart_account_address, w.entrypoint_address, w.paymaster_enabled, w.bundler_profile,
                       w.is_active, w.is_frozen, w.frozen_at, w.frozen_by, w.freeze_reason,
                       w.created_at, w.updated_at,
                       a.external_id AS agent_external_id
                FROM wallets w
                JOIN agents a ON a.id = w.agent_id
                {where_sql}
                ORDER BY w.created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
                limit,
                offset,
            )
            return [self._wallet_from_row(dict(r), str(r["agent_external_id"])) for r in rows]

    async def get_many(self, wallet_ids: list[str]) -> list[Wallet]:
        """Batch load wallets by external IDs in a single query."""
        if not wallet_ids:
            return []

        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.external_id, w.chain_address, w.chain, w.mpc_provider, w.currency,
                       w.limit_per_tx, w.limit_total, w.addresses, w.account_type,
                       w.smart_account_address, w.entrypoint_address, w.paymaster_enabled, w.bundler_profile,
                       w.is_active, w.is_frozen, w.frozen_at, w.frozen_by, w.freeze_reason,
                       w.created_at, w.updated_at,
                       a.external_id AS agent_external_id
                FROM wallets w
                JOIN agents a ON a.id = w.agent_id
                WHERE w.external_id = ANY($1::varchar[])
                """,
                wallet_ids,
            )

            by_id: dict[str, Wallet] = {}
            for row in rows:
                wallet = self._wallet_from_row(dict(row), str(row["agent_external_id"]))
                by_id[wallet.wallet_id] = wallet
            return [by_id[wallet_id] for wallet_id in wallet_ids if wallet_id in by_id]

    async def update(
        self,
        wallet_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        addresses: Optional[dict[str, str]] = None,
        account_type: Optional[Literal["mpc_v1", "erc4337_v2"]] = None,
        smart_account_address: Optional[str] = None,
        entrypoint_address: Optional[str] = None,
        paymaster_enabled: Optional[bool] = None,
        bundler_profile: Optional[str] = None,
    ) -> Optional[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT addresses FROM wallets WHERE external_id = $1",
                wallet_id,
            )
            if not current:
                return None
            merged = current["addresses"] if isinstance(current["addresses"], dict) else {}
            if not isinstance(merged, dict):
                merged = {}
            if addresses:
                merged.update(addresses)

            import json as _json
            await conn.execute(
                """
                UPDATE wallets
                SET limit_per_tx = COALESCE($2, limit_per_tx),
                    limit_total = COALESCE($3, limit_total),
                    is_active = COALESCE($4, is_active),
                    addresses = $5::jsonb,
                    account_type = COALESCE($6, account_type),
                    smart_account_address = COALESCE($7, smart_account_address),
                    entrypoint_address = COALESCE($8, entrypoint_address),
                    paymaster_enabled = COALESCE($9, paymaster_enabled),
                    bundler_profile = COALESCE($10, bundler_profile),
                    updated_at = NOW()
                WHERE external_id = $1
                """,
                wallet_id,
                str(limit_per_tx) if limit_per_tx is not None else None,
                str(limit_total) if limit_total is not None else None,
                is_active,
                _json.dumps(merged),
                account_type,
                smart_account_address,
                entrypoint_address,
                paymaster_enabled,
                bundler_profile,
            )
            return await self.get(wallet_id)

    async def set_limits(
        self,
        wallet_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
    ) -> Optional[Wallet]:
        return await self.update(wallet_id, limit_per_tx=limit_per_tx, limit_total=limit_total)

    async def set_address(self, wallet_id: str, chain: str, address: str) -> Optional[Wallet]:
        return await self.update(wallet_id, addresses={chain: address})

    async def delete(self, wallet_id: str) -> bool:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            res = await conn.execute("DELETE FROM wallets WHERE external_id = $1", wallet_id)
            return "DELETE 1" in res

    async def freeze(self, wallet_id: str, frozen_by: str, reason: str) -> Optional[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE wallets
                SET is_frozen = TRUE,
                    frozen_at = NOW(),
                    frozen_by = $2,
                    freeze_reason = $3,
                    updated_at = NOW()
                WHERE external_id = $1
                """,
                wallet_id,
                frozen_by,
                reason,
            )
        return await self.get(wallet_id)

    async def unfreeze(self, wallet_id: str) -> Optional[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE wallets
                SET is_frozen = FALSE,
                    frozen_at = NULL,
                    frozen_by = NULL,
                    freeze_reason = NULL,
                    updated_at = NOW()
                WHERE external_id = $1
                """,
                wallet_id,
            )
        return await self.get(wallet_id)

    async def get_frozen_wallets(self) -> List[Wallet]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT w.external_id, w.chain_address, w.chain, w.mpc_provider, w.currency,
                       w.limit_per_tx, w.limit_total, w.addresses, w.account_type,
                       w.smart_account_address, w.entrypoint_address, w.paymaster_enabled, w.bundler_profile,
                       w.is_active, w.is_frozen, w.frozen_at, w.frozen_by, w.freeze_reason,
                       w.created_at, w.updated_at,
                       a.external_id AS agent_external_id
                FROM wallets w
                JOIN agents a ON a.id = w.agent_id
                WHERE w.is_frozen = TRUE
                ORDER BY w.frozen_at DESC NULLS LAST
                LIMIT 1000
                """
            )
            return [self._wallet_from_row(dict(r), str(r["agent_external_id"])) for r in rows]

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
