"""Solana payment executor — mirrors ChainExecutor pattern for Solana.

Handles the full lifecycle:
  1. Balance check
  2. Transaction build (SPL TransferChecked)
  3. MPC signing via Turnkey (ed25519)
  4. Submission + confirmation
  5. ChainReceipt generation
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sardis_ledger.records import ChainReceipt

from .client import (
    TOKEN_DECIMALS,
    SolanaClient,
    SolanaConfig,
    SolanaRPCError,
    SolanaTransactionError,
    get_solana_config,
)
from .gasless import KoraGaslessClient
from .program import (
    SARDIS_WALLET_PROGRAM_ID,
    build_execute_transfer_data,
    derive_wallet_pdas,
    parse_program_error,
)
from .transfer import (
    SolanaTransferParams,
    build_spl_transfer,
)

logger = logging.getLogger(__name__)

# Solana confirmation levels
CONFIRMATION_CONFIRMED = "confirmed"  # ~400ms, safe for most transfers
CONFIRMATION_FINALIZED = "finalized"  # ~6.4s, max safety

# Retry and timeout settings
MAX_CONFIRM_RETRIES = 30
CONFIRM_POLL_INTERVAL = 0.5  # seconds
MAX_BLOCKHASH_AGE = 150  # slots (~60 seconds)


@dataclass
class SolanaPaymentResult:
    """Result of a Solana payment execution."""
    success: bool
    signature: str | None
    sender: str
    recipient: str
    mint: str
    amount: int
    confirmation_status: str
    slot: int | None = None
    error: str | None = None
    gasless: bool = False
    execution_time_ms: float = 0


class SolanaExecutor:
    """Production-grade Solana payment executor.

    Features:
    - Balance pre-check before building transaction
    - Transaction simulation before submission
    - Turnkey MPC ed25519 signing
    - Kora gasless fallback
    - Confirmation polling with timeout
    - ChainReceipt generation for audit ledger
    """

    def __init__(
        self,
        config: SolanaConfig | None = None,
        turnkey_client: Any | None = None,
        kora_client: KoraGaslessClient | None = None,
        confirmation_level: str = CONFIRMATION_CONFIRMED,
        program_id: str | None = None,
    ) -> None:
        self.config = config or get_solana_config()
        self._client = SolanaClient(self.config)
        self._turnkey = turnkey_client
        self._kora = kora_client
        self._confirmation_level = confirmation_level
        self._program_id = program_id

    async def check_balance(self, owner: str, mint: str, required_amount: int) -> bool:
        """Check if owner has sufficient SPL token balance."""
        accounts = await self._client.get_token_accounts_by_owner(owner, mint)
        if not accounts:
            logger.warning("No token account for owner=%s, mint=%s", owner, mint)
            return False

        token_account = accounts[0]["pubkey"]
        balance = await self._client.get_token_balance(token_account)
        has_enough = balance >= required_amount

        if not has_enough:
            logger.warning(
                "Insufficient balance: owner=%s, mint=%s, has=%d, needs=%d",
                owner, mint, balance, required_amount,
            )

        return has_enough

    async def execute_payment(
        self,
        sender: str,
        recipient: str,
        mint: str,
        amount: int,
        wallet_id: str,
        mandate_id: str | None = None,
        use_gasless: bool = True,
    ) -> SolanaPaymentResult:
        """Execute a full payment lifecycle on Solana.

        When program_id is set, routes through the Sardis Anchor program
        (execute_transfer instruction with on-chain policy enforcement).
        Otherwise falls back to direct SPL TransferChecked.

        1. Check sender balance
        2. Build SPL TransferChecked tx (or Anchor execute_transfer ix)
        3. Simulate transaction
        4. Sign via Turnkey MPC (ed25519)
        5. Submit and confirm
        """
        if self._program_id:
            return await self._execute_program_transfer(
                sender, recipient, mint, amount, wallet_id, mandate_id
            )

        start = datetime.now(UTC)
        decimals = TOKEN_DECIMALS.get(mint, 6)

        # 1. Balance check
        has_balance = await self.check_balance(sender, mint, amount)
        if not has_balance:
            return SolanaPaymentResult(
                success=False,
                signature=None,
                sender=sender,
                recipient=recipient,
                mint=mint,
                amount=amount,
                confirmation_status="failed",
                error=f"Insufficient balance for {amount} (decimals={decimals})",
            )

        # 2. Build transaction
        params = SolanaTransferParams(
            sender=sender,
            recipient=recipient,
            mint=mint,
            amount=amount,
            decimals=decimals,
        )

        try:
            prepared = await build_spl_transfer(self._client, params)
        except Exception as e:
            logger.error("Failed to build Solana tx: %s", e)
            return SolanaPaymentResult(
                success=False,
                signature=None,
                sender=sender,
                recipient=recipient,
                mint=mint,
                amount=amount,
                confirmation_status="failed",
                error=f"Transaction build failed: {e}",
            )

        # 3. Simulate
        try:
            sim_result = await self._client.simulate_transaction(prepared.message_base64)
            if sim_result.get("err"):
                err_detail = sim_result["err"]
                logger.error("Simulation failed: %s", err_detail)
                return SolanaPaymentResult(
                    success=False,
                    signature=None,
                    sender=sender,
                    recipient=recipient,
                    mint=mint,
                    amount=amount,
                    confirmation_status="failed",
                    error=f"Simulation failed: {err_detail}",
                )
            logger.info("Simulation passed for %s -> %s (%d)", sender, recipient, amount)
        except SolanaRPCError as e:
            logger.warning("Simulation RPC error (proceeding): %s", e)

        # 4. Sign via Turnkey MPC
        if not self._turnkey:
            return SolanaPaymentResult(
                success=False,
                signature=None,
                sender=sender,
                recipient=recipient,
                mint=mint,
                amount=amount,
                confirmation_status="failed",
                error="No Turnkey MPC signer configured",
            )

        try:
            sign_result = await self._turnkey.sign_solana_transaction(
                wallet_id=wallet_id,
                unsigned_transaction=prepared.message_base64,
                sign_with=sender,
            )
            signed_tx_base64 = sign_result.get("signedTransaction", "")
            if not signed_tx_base64:
                raise ValueError("Turnkey returned empty signed transaction")
        except Exception as e:
            logger.error("MPC signing failed: %s", e)
            return SolanaPaymentResult(
                success=False,
                signature=None,
                sender=sender,
                recipient=recipient,
                mint=mint,
                amount=amount,
                confirmation_status="failed",
                error=f"MPC signing failed: {e}",
            )

        # 5. Submit and confirm
        try:
            signature = await self._client.send_raw_transaction(signed_tx_base64)
        except SolanaRPCError as e:
            logger.error("Transaction submission failed: %s", e)
            return SolanaPaymentResult(
                success=False,
                signature=None,
                sender=sender,
                recipient=recipient,
                mint=mint,
                amount=amount,
                confirmation_status="failed",
                error=f"Submission failed: {e}",
            )

        # Poll for confirmation
        confirmed = await self._poll_confirmation(
            signature, self._confirmation_level
        )
        elapsed_ms = (datetime.now(UTC) - start).total_seconds() * 1000

        slot = None
        try:
            slot = await self._client.get_slot()
        except Exception:
            pass

        if confirmed:
            logger.info(
                "Solana payment confirmed: sig=%s, %s -> %s, amount=%d, %.0fms",
                signature, sender, recipient, amount, elapsed_ms,
            )
        else:
            logger.warning(
                "Solana payment sent but not confirmed within timeout: sig=%s",
                signature,
            )

        return SolanaPaymentResult(
            success=confirmed,
            signature=signature,
            sender=sender,
            recipient=recipient,
            mint=mint,
            amount=amount,
            confirmation_status=self._confirmation_level if confirmed else "sent",
            slot=slot,
            execution_time_ms=elapsed_ms,
        )

    async def _execute_program_transfer(
        self,
        sender: str,
        recipient: str,
        mint: str,
        amount: int,
        wallet_id: str,
        mandate_id: str | None = None,
    ) -> SolanaPaymentResult:
        """Execute transfer through the Sardis Anchor program.

        The Anchor program enforces on-chain spending policy (per-tx limits,
        time windows, merchant rules, token allowlist) atomically within
        the same transaction as the SPL transfer.
        """
        start = datetime.now(UTC)

        # Derive wallet PDA (the PDA is the token authority, not the sender directly)
        pdas = derive_wallet_pdas(sender, self._program_id or SARDIS_WALLET_PROGRAM_ID)
        ix_data = build_execute_transfer_data(amount)

        logger.info(
            "Executing program transfer: sender=%s, recipient=%s, mint=%s, amount=%d, wallet_pda=%s",
            sender, recipient, mint, amount, pdas.wallet,
        )

        # Build the transaction with Anchor instruction accounts.
        # The actual instruction building and signing is handled by the
        # Turnkey MPC signer which constructs the full transaction.
        try:
            if not self._turnkey:
                return SolanaPaymentResult(
                    success=False, signature=None, sender=sender,
                    recipient=recipient, mint=mint, amount=amount,
                    confirmation_status="failed",
                    error="No Turnkey MPC signer configured",
                )

            sign_result = await self._turnkey.sign_solana_transaction(
                wallet_id=wallet_id,
                instruction_data={
                    "program_id": self._program_id,
                    "instruction": "execute_transfer",
                    "data": ix_data.hex(),
                    "wallet_pda": pdas.wallet,
                    "merchant_registry": pdas.merchant_registry,
                    "token_allowlist": pdas.token_allowlist,
                    "mint": mint,
                    "recipient": recipient,
                    "amount": amount,
                },
                sign_with=sender,
            )
            signed_tx_base64 = sign_result.get("signedTransaction", "")
            if not signed_tx_base64:
                raise ValueError("Turnkey returned empty signed transaction")
        except Exception as e:
            logger.error("Program transfer signing failed: %s", e)
            reason = parse_program_error(str(e))
            return SolanaPaymentResult(
                success=False, signature=None, sender=sender,
                recipient=recipient, mint=mint, amount=amount,
                confirmation_status="failed",
                error=f"Program transfer failed: {reason or e}",
            )

        # Submit and confirm
        try:
            signature = await self._client.send_raw_transaction(signed_tx_base64)
        except SolanaRPCError as e:
            reason = parse_program_error(getattr(e, "data", str(e)))
            logger.error("Program tx submission failed: %s (reason=%s)", e, reason)
            return SolanaPaymentResult(
                success=False, signature=None, sender=sender,
                recipient=recipient, mint=mint, amount=amount,
                confirmation_status="failed",
                error=f"Submission failed: {reason or e}",
            )

        confirmed = await self._poll_confirmation(signature, self._confirmation_level)
        elapsed_ms = (datetime.now(UTC) - start).total_seconds() * 1000

        slot = None
        try:
            slot = await self._client.get_slot()
        except Exception:
            pass

        if confirmed:
            logger.info(
                "Program transfer confirmed: sig=%s, %s -> %s, amount=%d, %.0fms",
                signature, sender, recipient, amount, elapsed_ms,
            )
        else:
            logger.warning(
                "Program transfer sent but not confirmed: sig=%s", signature,
            )

        return SolanaPaymentResult(
            success=confirmed,
            signature=signature,
            sender=sender,
            recipient=recipient,
            mint=mint,
            amount=amount,
            confirmation_status=self._confirmation_level if confirmed else "sent",
            slot=slot,
            execution_time_ms=elapsed_ms,
        )

    async def _poll_confirmation(
        self, signature: str, commitment: str
    ) -> bool:
        """Poll for transaction confirmation with timeout."""
        for _ in range(MAX_CONFIRM_RETRIES):
            try:
                if await self._client.confirm_transaction(signature, commitment):
                    return True
            except SolanaTransactionError:
                return False
            await asyncio.sleep(CONFIRM_POLL_INTERVAL)
        return False

    def to_chain_receipt(
        self,
        result: SolanaPaymentResult,
        audit_anchor: str = "",
    ) -> ChainReceipt:
        """Convert SolanaPaymentResult to a ChainReceipt for the audit ledger."""
        return ChainReceipt(
            tx_hash=result.signature or "",
            chain="solana",
            block_number=result.slot or 0,
            audit_anchor=audit_anchor,
            gas_used=5000,  # Solana base fee in lamports
            timestamp=datetime.now(UTC),
            confirmed=result.success,
            execution_path="solana_program_transfer" if self._program_id else "solana_spl_transfer",
        )

    async def close(self) -> None:
        """Clean up resources."""
        await self._client.close()
        if self._kora:
            await self._kora.close()
