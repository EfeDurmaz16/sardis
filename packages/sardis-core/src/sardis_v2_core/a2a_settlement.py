"""Agent-to-Agent Settlement Engine.

This module handles settlement of escrowed funds between agents:
- On-chain settlement: Transfer from escrow wallet to payee wallet
- Off-chain settlement: Internal ledger transfer for same-platform agents
- Double-entry ledger recording for audit trail

Settlement Flow:
    1. Escrow is in RELEASED state
    2. Settlement engine determines on-chain vs off-chain
    3. Execute transfer (blockchain or ledger)
    4. Record settlement in ledger for audit
    5. Return settlement result

Usage:
    from sardis_v2_core.a2a_settlement import SettlementEngine

    engine = SettlementEngine()

    # Settle escrow on-chain
    result = await engine.settle_on_chain(escrow)

    # Or settle off-chain (internal ledger)
    result = await engine.settle_off_chain(escrow)
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, Optional, Literal, Protocol
from uuid import uuid4

from .a2a_escrow import Escrow, EscrowState
from .database import Database
from .exceptions import (
    SardisNotFoundError,
    SardisValidationError,
    SardisConflictError,
    SardisTransactionFailedError,
)
from .mandates import PaymentMandate, VCProof
from .tokens import TokenType, to_raw_token_amount


class ChainExecutorPort(Protocol):
    async def dispatch_payment(self, mandate: PaymentMandate) -> Any: ...


class WalletRepositoryPort(Protocol):
    async def get_by_agent(self, agent_id: str) -> Any: ...


@dataclass(slots=True)
class SettlementResult:
    """
    Settlement execution result.

    Records the outcome of a settlement operation, including
    transaction hash, settlement type, and ledger entries.
    """
    escrow_id: str
    tx_hash: Optional[str]
    settlement_type: Literal["on_chain", "off_chain"]
    ledger_entries: list[str]
    settled_at: datetime
    payer_agent_id: str
    payee_agent_id: str
    amount: Decimal
    token: str
    chain: str
    block_number: Optional[int] = None
    explorer_url: Optional[str] = None
    execution_path: Optional[str] = None
    user_op_hash: Optional[str] = None


class SettlementEngine:
    """
    Handles settlement of agent-to-agent escrow payments.

    Supports both on-chain (blockchain transfer) and off-chain
    (internal ledger) settlement paths with full audit trail.
    """

    def __init__(
        self,
        *,
        chain_executor: Optional[ChainExecutorPort] = None,
        wallet_repo: Optional[WalletRepositoryPort] = None,
        domain: str = "sardis.sh",
    ) -> None:
        self._chain_executor = chain_executor
        self._wallet_repo = wallet_repo
        self._domain = domain

    async def settle_on_chain(
        self,
        escrow: Escrow,
        *,
        chain_executor: Optional[ChainExecutorPort] = None,
        wallet_repo: Optional[WalletRepositoryPort] = None,
    ) -> SettlementResult:
        """
        Execute on-chain settlement (blockchain transfer).

        Transfers escrowed funds from escrow wallet to payee's wallet
        on the blockchain. Records the transaction in the ledger.

        Args:
            escrow: Escrow to settle

        Returns:
            SettlementResult with transaction hash

        Raises:
            SardisValidationError: If escrow not in RELEASED state
            SardisTransactionFailedError: If on-chain transfer fails
        """
        # Validate escrow state
        if escrow.state != EscrowState.RELEASED:
            raise SardisValidationError(
                f"Escrow must be in RELEASED state for settlement (current: {escrow.state.value})",
                field="state",
            )

        active_chain_executor = chain_executor or self._chain_executor
        active_wallet_repo = wallet_repo or self._wallet_repo
        if active_chain_executor is None:
            raise SardisValidationError(
                "chain_executor is required for on-chain settlement",
                field="chain_executor",
            )
        if active_wallet_repo is None:
            raise SardisValidationError(
                "wallet_repo is required for on-chain settlement",
                field="wallet_repo",
            )

        payer_wallet = await active_wallet_repo.get_by_agent(escrow.payer_agent_id)
        if payer_wallet is None:
            raise SardisNotFoundError("Wallet", f"agent:{escrow.payer_agent_id}")
        payee_wallet = await active_wallet_repo.get_by_agent(escrow.payee_agent_id)
        if payee_wallet is None:
            raise SardisNotFoundError("Wallet", f"agent:{escrow.payee_agent_id}")

        if getattr(payer_wallet, "is_frozen", False):
            raise SardisConflictError("Payer wallet is frozen")
        if not getattr(payer_wallet, "is_active", True):
            raise SardisConflictError("Payer wallet is inactive")
        if not getattr(payee_wallet, "is_active", True):
            raise SardisConflictError("Payee wallet is inactive")

        destination = payee_wallet.get_address(escrow.chain)
        if not destination:
            raise SardisValidationError(
                f"Payee wallet has no address on chain '{escrow.chain}'",
                field="destination",
            )

        token_symbol = str(escrow.token).upper()
        try:
            token_type = TokenType(token_symbol)
        except ValueError as exc:
            raise SardisValidationError(f"Unsupported token for settlement: {escrow.token}", field="token") from exc

        amount_minor = to_raw_token_amount(token_type, escrow.amount)
        nonce = hashlib.sha256(f"a2a:settle:{escrow.id}".encode()).hexdigest()
        audit_hash = hashlib.sha256(
            f"a2a_settlement:{escrow.id}:{escrow.payer_agent_id}:{escrow.payee_agent_id}:{escrow.amount}:{token_symbol}:{escrow.chain}".encode()
        ).hexdigest()
        mandate = PaymentMandate(
            mandate_id=f"a2a_settle_{nonce[:16]}",
            mandate_type="payment",
            issuer=f"agent:{escrow.payer_agent_id}",
            subject=escrow.payer_agent_id,
            expires_at=int(time.time()) + 300,
            nonce=nonce,
            proof=VCProof(
                verification_method=f"wallet:{getattr(payer_wallet, 'wallet_id', escrow.payer_agent_id)}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="a2a-settlement",
            ),
            domain=self._domain,
            purpose="checkout",
            chain=escrow.chain,
            token=token_symbol,
            amount_minor=amount_minor,
            destination=destination,
            audit_hash=audit_hash,
            wallet_id=getattr(payer_wallet, "wallet_id", None),
            account_type=getattr(payer_wallet, "account_type", "mpc_v1"),
            smart_account_address=getattr(payer_wallet, "smart_account_address", None),
            merchant_domain=self._domain,
        )

        try:
            receipt = await active_chain_executor.dispatch_payment(mandate)
        except SardisTransactionFailedError:
            raise
        except Exception as exc:  # pragma: no cover - defensive adapter boundary
            raise SardisTransactionFailedError(
                "On-chain settlement transfer failed",
                chain=escrow.chain,
                reason=str(exc),
            ) from exc

        tx_hash = getattr(receipt, "tx_hash", None)
        if not tx_hash:
            raise SardisTransactionFailedError(
                "On-chain settlement returned empty transaction hash",
                chain=escrow.chain,
            )

        now = datetime.now(timezone.utc)
        settlement_id = f"settlement_{uuid4().hex[:16]}"
        block_number = getattr(receipt, "block_number", None)
        execution_path = getattr(receipt, "execution_path", None)
        user_op_hash = getattr(receipt, "user_op_hash", None)
        explorer_url = _explorer_url(escrow.chain, tx_hash)

        # Record settlement in ledger
        ledger_entries = await self.record_settlement(
            escrow=escrow,
            settlement_tx=tx_hash,
            settlement_type="on_chain",
        )

        # Store settlement record in database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO settlements (
                    id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                    payer_agent_id, payee_agent_id, settled_at, ledger_entries
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                settlement_id,
                escrow.id,
                "on_chain",
                tx_hash,
                escrow.amount,
                escrow.token,
                escrow.chain,
                escrow.payer_agent_id,
                escrow.payee_agent_id,
                now,
                ledger_entries,
            )

        return SettlementResult(
            escrow_id=escrow.id,
            tx_hash=tx_hash,
            settlement_type="on_chain",
            ledger_entries=ledger_entries,
            settled_at=now,
            payer_agent_id=escrow.payer_agent_id,
            payee_agent_id=escrow.payee_agent_id,
            amount=escrow.amount,
            token=escrow.token,
            chain=escrow.chain,
            block_number=block_number,
            explorer_url=explorer_url,
            execution_path=execution_path,
            user_op_hash=user_op_hash,
        )

    async def settle_off_chain(self, escrow: Escrow) -> SettlementResult:
        """
        Execute off-chain settlement (internal ledger transfer).

        Transfers funds via internal ledger without on-chain transaction.
        Used when both agents are on the same platform with internal balances.

        Args:
            escrow: Escrow to settle

        Returns:
            SettlementResult without transaction hash

        Raises:
            SardisValidationError: If escrow not in RELEASED state
        """
        # Validate escrow state
        if escrow.state != EscrowState.RELEASED:
            raise SardisValidationError(
                f"Escrow must be in RELEASED state for settlement (current: {escrow.state.value})",
                field="state",
            )

        now = datetime.now(timezone.utc)
        settlement_id = f"settlement_{uuid4().hex[:16]}"

        # Record off-chain transfer in ledger (double-entry)
        ledger_entries = await self.record_settlement(
            escrow=escrow,
            settlement_tx=settlement_id,
            settlement_type="off_chain",
        )

        # Store settlement record in database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO settlements (
                    id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                    payer_agent_id, payee_agent_id, settled_at, ledger_entries
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                settlement_id,
                escrow.id,
                "off_chain",
                None,  # No on-chain tx_hash for off-chain settlements
                escrow.amount,
                escrow.token,
                escrow.chain,
                escrow.payer_agent_id,
                escrow.payee_agent_id,
                now,
                ledger_entries,
            )

        return SettlementResult(
            escrow_id=escrow.id,
            tx_hash=None,
            settlement_type="off_chain",
            ledger_entries=ledger_entries,
            settled_at=now,
            payer_agent_id=escrow.payer_agent_id,
            payee_agent_id=escrow.payee_agent_id,
            amount=escrow.amount,
            token=escrow.token,
            chain=escrow.chain,
        )

    async def record_settlement(
        self,
        escrow: Escrow,
        settlement_tx: str,
        settlement_type: Literal["on_chain", "off_chain"] = "on_chain",
    ) -> list[str]:
        """
        Record settlement in double-entry ledger.

        Creates ledger entries for both debit (escrow) and credit (payee)
        to maintain a complete audit trail.

        Args:
            escrow: Escrow being settled
            settlement_tx: Transaction hash or settlement ID
            settlement_type: Type of settlement (on_chain or off_chain)

        Returns:
            List of ledger entry IDs created
        """
        now = datetime.now(timezone.utc)
        ledger_entries = []

        async with Database.transaction() as conn:
            # Debit entry: Escrow account (funds leaving escrow)
            debit_entry_id = f"entry_{uuid4().hex[:16]}"
            await conn.execute(
                """
                INSERT INTO ledger_entries_v2 (
                    entry_id, tx_id, account_id, entry_type, amount, currency,
                    chain, chain_tx_hash, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                debit_entry_id,
                settlement_tx,
                f"escrow:{escrow.id}",
                "debit",
                escrow.amount,
                escrow.token,
                escrow.chain,
                settlement_tx if settlement_type == "on_chain" else None,
                {
                    "settlement_type": settlement_type,
                    "escrow_id": escrow.id,
                    "payer_agent_id": escrow.payer_agent_id,
                    "payee_agent_id": escrow.payee_agent_id,
                },
                "confirmed",
                now,
            )
            ledger_entries.append(debit_entry_id)

            # Credit entry: Payee account (funds received)
            credit_entry_id = f"entry_{uuid4().hex[:16]}"
            await conn.execute(
                """
                INSERT INTO ledger_entries_v2 (
                    entry_id, tx_id, account_id, entry_type, amount, currency,
                    chain, chain_tx_hash, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                credit_entry_id,
                settlement_tx,
                f"agent:{escrow.payee_agent_id}",
                "credit",
                escrow.amount,
                escrow.token,
                escrow.chain,
                settlement_tx if settlement_type == "on_chain" else None,
                {
                    "settlement_type": settlement_type,
                    "escrow_id": escrow.id,
                    "payer_agent_id": escrow.payer_agent_id,
                    "payee_agent_id": escrow.payee_agent_id,
                },
                "confirmed",
                now,
            )
            ledger_entries.append(credit_entry_id)

        return ledger_entries

    async def get_settlement(self, escrow_id: str) -> Optional[SettlementResult]:
        """
        Get settlement result for an escrow.

        Args:
            escrow_id: Escrow identifier

        Returns:
            SettlementResult if found, None otherwise
        """
        async with Database.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                       payer_agent_id, payee_agent_id, settled_at, ledger_entries
                FROM settlements
                WHERE escrow_id = $1
                """,
                escrow_id,
            )

            if not row:
                return None

            return SettlementResult(
                escrow_id=row["escrow_id"],
                tx_hash=row["tx_hash"],
                settlement_type=row["settlement_type"],
                ledger_entries=row["ledger_entries"],
                settled_at=row["settled_at"],
                payer_agent_id=row["payer_agent_id"],
                payee_agent_id=row["payee_agent_id"],
                amount=row["amount"],
                token=row["token"],
                chain=row["chain"],
                block_number=None,
                explorer_url=_explorer_url(row["chain"], row["tx_hash"]) if row["tx_hash"] else None,
                execution_path=None,
                user_op_hash=None,
            )

    async def list_settlements(
        self,
        agent_id: Optional[str] = None,
        settlement_type: Optional[Literal["on_chain", "off_chain"]] = None,
        limit: int = 100,
    ) -> list[SettlementResult]:
        """
        List settlements with optional filters.

        Args:
            agent_id: Filter by payer or payee agent ID
            settlement_type: Filter by settlement type
            limit: Maximum number of results

        Returns:
            List of SettlementResult instances
        """
        query_parts = ["SELECT * FROM settlements WHERE 1=1"]
        params: list = []
        param_idx = 1

        if agent_id:
            query_parts.append(
                f" AND (payer_agent_id = ${param_idx} OR payee_agent_id = ${param_idx})"
            )
            params.append(agent_id)
            param_idx += 1

        if settlement_type:
            query_parts.append(f" AND settlement_type = ${param_idx}")
            params.append(settlement_type)
            param_idx += 1

        query_parts.append(f" ORDER BY settled_at DESC LIMIT ${param_idx}")
        params.append(limit)

        query = "".join(query_parts)

        async with Database.connection() as conn:
            rows = await conn.fetch(query, *params)
            return [
                SettlementResult(
                    escrow_id=row["escrow_id"],
                    tx_hash=row["tx_hash"],
                    settlement_type=row["settlement_type"],
                    ledger_entries=row["ledger_entries"],
                    settled_at=row["settled_at"],
                    payer_agent_id=row["payer_agent_id"],
                    payee_agent_id=row["payee_agent_id"],
                    amount=row["amount"],
                    token=row["token"],
                    chain=row["chain"],
                    block_number=None,
                    explorer_url=_explorer_url(row["chain"], row["tx_hash"]) if row["tx_hash"] else None,
                    execution_path=None,
                    user_op_hash=None,
                )
                for row in rows
            ]


def _explorer_url(chain: str, tx_hash: str) -> Optional[str]:
    normalized = (chain or "").strip().lower()
    if normalized in {"base", "base-mainnet"}:
        return f"https://basescan.org/tx/{tx_hash}"
    if normalized in {"base_sepolia", "base-sepolia"}:
        return f"https://sepolia.basescan.org/tx/{tx_hash}"
    if normalized in {"polygon", "polygon-mainnet"}:
        return f"https://polygonscan.com/tx/{tx_hash}"
    if normalized in {"polygon-amoy", "amoy"}:
        return f"https://amoy.polygonscan.com/tx/{tx_hash}"
    if normalized in {"ethereum", "eth-mainnet"}:
        return f"https://etherscan.io/tx/{tx_hash}"
    if normalized in {"ethereum-sepolia", "sepolia"}:
        return f"https://sepolia.etherscan.io/tx/{tx_hash}"
    if normalized in {"arbitrum", "arb-mainnet"}:
        return f"https://arbiscan.io/tx/{tx_hash}"
    if normalized in {"optimism", "op-mainnet"}:
        return f"https://optimistic.etherscan.io/tx/{tx_hash}"
    return None
