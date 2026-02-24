"""Non-custodial wallet primitives for AI agent payments.

This module provides the core Wallet model for AI agents in the Sardis
payment infrastructure. Wallets are non-custodial, meaning:

- Funds are held on-chain, not in our database
- Balances are read directly from blockchain
- Transactions are signed via MPC providers (Turnkey, Fireblocks)
- Private keys never leave secure enclaves

Usage:
    from sardis_v2_core import Wallet, TokenType

    # Create a new wallet
    wallet = Wallet.new(agent_id="agent_xxx", mpc_provider="turnkey")

    # Get balance from chain
    balance = await wallet.get_balance(
        chain="base",
        token=TokenType.USDC,
        rpc_client=rpc_client,
    )

    # Sign a transaction
    signed_tx = await wallet.sign_transaction(
        chain="base",
        to_address="0x...",
        amount=Decimal("100.00"),
        token=TokenType.USDC,
        mpc_signer=signer,
    )
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from .tokens import TokenType
from .virtual_card import VirtualCard
from .exceptions import SardisRPCError

if TYPE_CHECKING:
    from sardis_chain.executor import TransactionRequest, MPCSignerPort


class TokenLimit(BaseModel):
    """Token-specific spending limits (for policy tracking only, not balance storage)."""
    token: TokenType
    limit_per_tx: Optional[Decimal] = None
    limit_total: Optional[Decimal] = None
    # Note: No balance field - balances are read from chain


class Wallet(BaseModel):
    """
    Non-custodial wallet for AI agents.

    This wallet never holds funds. It only:
    - Stores MPC provider and addresses
    - Signs transactions via MPC
    - Reads balances from chain (on-demand)
    """
    wallet_id: str
    agent_id: str
    mpc_provider: str = Field(default="turnkey")  # "turnkey" | "fireblocks" | "local"
    account_type: Literal["mpc_v1", "erc4337_v2"] = Field(default="mpc_v1")
    addresses: dict[str, str] = Field(default_factory=dict)  # chain -> address mapping
    currency: str = Field(default="USDC")  # Default currency for display
    token_limits: dict[str, TokenLimit] = Field(default_factory=dict)  # Token-specific limits
    limit_per_tx: Decimal = Field(default=Decimal("100.00"))
    limit_total: Decimal = Field(default=Decimal("1000.00"))
    smart_account_address: Optional[str] = None
    entrypoint_address: Optional[str] = None
    paymaster_enabled: bool = False
    bundler_profile: Optional[str] = None
    cdp_wallet_id: Optional[str] = None
    cdp_wallet_address: Optional[str] = None
    cdp_funded_amount: Decimal = Field(default=Decimal("0"))
    x402_enabled: bool = False
    virtual_card: Optional[VirtualCard] = None
    is_active: bool = True

    # Freeze state (blocks all transactions)
    is_frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
    freeze_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
        }

    @staticmethod
    def new(
        agent_id: str,
        *,
        mpc_provider: str = "turnkey",
        account_type: Literal["mpc_v1", "erc4337_v2"] = "mpc_v1",
        currency: str = "USDC",
        wallet_id: str | None = None,
    ) -> "Wallet":
        """Create a new non-custodial wallet."""
        from uuid import uuid4
        return Wallet(
            wallet_id=wallet_id or f"wallet_{uuid4().hex[:16]}",
            agent_id=agent_id,
            mpc_provider=mpc_provider,
            account_type=account_type,
            currency=currency,
        )

    def get_address(self, chain: str) -> Optional[str]:
        """Get wallet address for a specific chain."""
        return self.addresses.get(chain)

    def set_address(self, chain: str, address: str) -> None:
        """Set wallet address for a chain."""
        self.addresses[chain] = address
        self.updated_at = datetime.now(timezone.utc)

    async def get_balance(
        self,
        chain: str,
        token: TokenType,
        rpc_client: Optional[Any] = None,  # ChainRPCClient from sardis_chain
    ) -> Decimal:
        """
        Get wallet balance from chain (read-only, non-custodial).
        
        Args:
            chain: Chain identifier (e.g., "base", "polygon")
            token: Token type (USDC, USDT, etc.)
            rpc_client: RPC client for balance query (required)
            
        Returns:
            Balance in token units (e.g., 100.00 USDC)
            
        Raises:
            ValueError: If address not found or RPC client not provided
        """
        address = self.get_address(chain)
        if not address:
            raise ValueError(f"No address found for chain {chain}")
        
        if not rpc_client:
            raise ValueError("RPC client required for balance query")
        
        # Get token contract address
        from .tokens import get_token_metadata
        token_meta = get_token_metadata(token)
        token_address = token_meta.contract_addresses.get(chain)
        if not token_address:
            raise ValueError(f"Token {token} not supported on chain {chain}")
        
        # Query ERC20 balance using RPC client
        # balanceOf(address) -> uint256
        # Function selector: 0x70a08231
        from sardis_chain.executor import encode_erc20_transfer
        # Actually, we need balanceOf, not transfer
        # balanceOf(address) selector: 0x70a08231
        selector = bytes.fromhex("70a08231")
        # Pad address to 32 bytes
        address_bytes = bytes.fromhex(address[2:].lower().zfill(64))
        call_data = selector + address_bytes
        
        # Call contract
        tx_params = {
            "to": token_address,
            "data": "0x" + call_data.hex(),
        }
        
        try:
            # Use RPC client's _call method if available
            if hasattr(rpc_client, "_call"):
                result = await rpc_client._call("eth_call", [tx_params, "latest"])
                # Parse result (hex string to int)
                balance_raw = int(result, 16)
                # Convert from raw amount to token units
                from .tokens import normalize_token_amount
                return normalize_token_amount(token, balance_raw)
            else:
                # Fallback: try direct method call
                if hasattr(rpc_client, "get_token_balance"):
                    return await rpc_client.get_token_balance(address, token_address)
                raise ValueError("RPC client does not support balance queries")
        except Exception as e:
            # Re-raise as SardisRPCError with context
            raise SardisRPCError(
                f"Failed to query balance for {address} on {chain}",
                chain=chain,
                method="eth_call",
                rpc_error=str(e),
            ) from e

    async def sign_transaction(
        self,
        chain: str,
        to_address: str,
        amount: Decimal,
        token: TokenType,
        mpc_signer: Optional["MPCSignerPort"] = None,
        tx_request: Optional["TransactionRequest"] = None,
    ) -> str:
        """
        Sign a transaction via MPC (non-custodial, sign-only).
        
        Args:
            chain: Chain identifier
            to_address: Recipient address
            amount: Amount in token units
            token: Token type
            mpc_signer: MPC signer instance
            tx_request: Pre-built transaction request (optional)
            
        Returns:
            Signed transaction hex string
        """
        if not mpc_signer:
            raise ValueError("MPC signer required for transaction signing")
        
        # Import here to avoid circular dependency
        from sardis_chain.executor import TransactionRequest, encode_erc20_transfer
        
        # Build transaction request if not provided
        if not tx_request:
            # Get token contract address
            from .tokens import get_token_metadata, to_raw_token_amount
            token_meta = get_token_metadata(token)
            token_address = token_meta.contract_addresses.get(chain)
            if not token_address:
                raise ValueError(f"Token {token} not supported on chain {chain}")
            
            # Encode ERC20 transfer
            amount_raw = to_raw_token_amount(token, amount)
            transfer_data = encode_erc20_transfer(to_address, amount_raw)
            
            tx_request = TransactionRequest(
                chain=chain,
                to_address=token_address,
                value=0,  # ERC20 transfers have value=0
                data=transfer_data,
            )
        
        # Sign via MPC
        signed_tx = await mpc_signer.sign_transaction(self.wallet_id, tx_request)
        return signed_tx

    def get_limit_per_tx(self, token: Optional[TokenType] = None) -> Decimal:
        """Get per-transaction limit for token (or default)."""
        if token and token.value in self.token_limits:
            token_limit = self.token_limits[token.value]
            if token_limit.limit_per_tx is not None:
                return token_limit.limit_per_tx
        return self.limit_per_tx

    def get_limit_total(self, token: Optional[TokenType] = None) -> Decimal:
        """Get total spending limit for token (or default)."""
        if token and token.value in self.token_limits:
            token_limit = self.token_limits[token.value]
            if token_limit.limit_total is not None:
                return token_limit.limit_total
        return self.limit_total

    def freeze(self, by: str, reason: str) -> None:
        """
        Freeze the wallet (blocks all transactions).

        Args:
            by: Admin/system identifier who froze the wallet
            reason: Reason for freezing (compliance, suspicious activity, etc.)
        """
        self.is_frozen = True
        self.frozen_at = datetime.now(timezone.utc)
        self.frozen_by = by
        self.freeze_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def unfreeze(self) -> None:
        """Unfreeze the wallet (restore transaction capability)."""
        self.is_frozen = False
        self.frozen_at = None
        self.frozen_by = None
        self.freeze_reason = None
        self.updated_at = datetime.now(timezone.utc)


@dataclass(slots=True)
class WalletSnapshot:
    wallet_id: str
    balances: dict[str, Decimal]
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Backwards compatibility alias
TokenBalance = TokenLimit
