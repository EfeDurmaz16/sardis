"""
Stablecoin service for unified token management.

Provides:
- Token metadata registry access
- Deposit and withdraw operations
- Internal mint/burn for demo/testing
- Balance operations across tokens
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import threading
import uuid

from sardis_core.models.token import (
    TokenType,
    TokenMetadata,
    TOKEN_REGISTRY,
    get_token_metadata,
    get_supported_tokens,
    get_active_tokens,
)


@dataclass
class DepositResult:
    """Result of a deposit operation."""
    success: bool
    deposit_id: str
    wallet_id: str
    token: TokenType
    amount: Decimal
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class WithdrawResult:
    """Result of a withdraw operation."""
    success: bool
    withdraw_id: str
    wallet_id: str
    token: TokenType
    amount: Decimal
    destination_address: Optional[str] = None
    tx_hash: Optional[str] = None
    fee: Decimal = Decimal("0")
    error: Optional[str] = None
    status: str = "pending"  # pending, confirmed, failed
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class MintResult:
    """Result of an internal mint operation (demo/testing only)."""
    success: bool
    mint_id: str
    wallet_id: str
    token: TokenType
    amount: Decimal
    reason: str
    error: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class StablecoinService:
    """
    Service for managing stablecoin operations.
    
    This service provides a unified interface for:
    - Token metadata queries
    - Deposit tracking (on-ramp from blockchain)
    - Withdraw processing (off-ramp to blockchain)
    - Internal mint/burn for demo mode
    
    In production, this would integrate with:
    - Blockchain listeners for deposit detection
    - MPC wallets for withdraw signing
    - Compliance checks for large transfers
    """
    
    def __init__(self, ledger=None, demo_mode: bool = True):
        """
        Initialize the stablecoin service.
        
        Args:
            ledger: The ledger instance for balance operations
            demo_mode: If True, enables internal mint/burn operations
        """
        self._ledger = ledger
        self._demo_mode = demo_mode
        self._lock = threading.RLock()
        
        # Track pending deposits and withdrawals
        self._pending_deposits: dict[str, DepositResult] = {}
        self._pending_withdrawals: dict[str, WithdrawResult] = {}
        
        # Mint/burn history for audit
        self._mint_history: list[MintResult] = []
    
    # ==================== Token Metadata ====================
    
    def get_token_info(self, token: TokenType) -> TokenMetadata:
        """Get metadata for a specific token."""
        return get_token_metadata(token)
    
    def list_tokens(self, active_only: bool = True) -> list[dict]:
        """
        List all supported tokens with their metadata.
        
        Args:
            active_only: If True, only return active tokens
            
        Returns:
            List of token info dicts
        """
        tokens = get_active_tokens() if active_only else get_supported_tokens()
        return [
            {
                "symbol": t.value,
                "name": TOKEN_REGISTRY[t].name,
                "decimals": TOKEN_REGISTRY[t].decimals,
                "issuer": TOKEN_REGISTRY[t].issuer,
                "peg_currency": TOKEN_REGISTRY[t].peg_currency,
                "is_active": TOKEN_REGISTRY[t].is_active,
            }
            for t in tokens
        ]
    
    def get_token_price_usd(self, token: TokenType, amount: Decimal) -> Decimal:
        """
        Get USD value for a token amount.
        
        For USD-pegged stablecoins, this is 1:1.
        For other currencies, applies conversion rate.
        """
        metadata = get_token_metadata(token)
        return metadata.to_usd(amount)
    
    # ==================== Deposit Operations ====================
    
    def create_deposit_address(
        self,
        wallet_id: str,
        token: TokenType,
        chain: str
    ) -> dict:
        """
        Create a deposit address for receiving tokens.
        
        In production, this would:
        1. Generate a unique deposit address (or return shared address with memo)
        2. Register the address with our blockchain listener
        3. Return deposit instructions
        
        For demo, we return a placeholder address.
        """
        metadata = get_token_metadata(token)
        
        if chain not in metadata.contract_addresses:
            raise ValueError(f"Token {token.value} not available on {chain}")
        
        # In demo mode, generate a fake address
        # In production, this would be a real derived address
        deposit_id = f"dep_{uuid.uuid4().hex[:16]}"
        
        if chain == "solana":
            demo_address = f"Sardis{uuid.uuid4().hex[:8]}Demo{wallet_id[-8:]}"
        else:
            demo_address = f"0x{'0' * 24}{uuid.uuid4().hex[:16]}"
        
        return {
            "deposit_id": deposit_id,
            "wallet_id": wallet_id,
            "token": token.value,
            "chain": chain,
            "address": demo_address,
            "memo": None,  # Some chains require memo/tag
            "min_amount": str(metadata.min_transfer_amount),
            "expires_at": None,  # Permanent for now
            "instructions": f"Send {token.value} on {chain} to the address above. "
                           f"Minimum deposit: {metadata.min_transfer_amount} {token.value}",
        }
    
    def confirm_deposit(
        self,
        wallet_id: str,
        token: TokenType,
        amount: Decimal,
        tx_hash: str
    ) -> DepositResult:
        """
        Confirm a deposit has been received.
        
        In production, this is called by blockchain listeners.
        For demo, this can be called manually.
        
        Args:
            wallet_id: Wallet to credit
            token: Token type
            amount: Amount deposited
            tx_hash: On-chain transaction hash
            
        Returns:
            DepositResult with success status
        """
        deposit_id = f"dep_{uuid.uuid4().hex[:16]}"
        
        metadata = get_token_metadata(token)
        if amount < metadata.min_transfer_amount:
            return DepositResult(
                success=False,
                deposit_id=deposit_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                tx_hash=tx_hash,
                error=f"Amount below minimum: {metadata.min_transfer_amount}",
            )
        
        # Credit the wallet
        if self._ledger:
            try:
                wallet = self._ledger.get_wallet(wallet_id)
                if not wallet:
                    return DepositResult(
                        success=False,
                        deposit_id=deposit_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        tx_hash=tx_hash,
                        error=f"Wallet {wallet_id} not found",
                    )
                
                # Update balance
                from sardis_core.models.wallet import TokenType as WalletTokenType
                wallet.add_token_balance(WalletTokenType(token.value), amount)
                self._ledger.update_wallet(wallet)
                
            except Exception as e:
                return DepositResult(
                    success=False,
                    deposit_id=deposit_id,
                    wallet_id=wallet_id,
                    token=token,
                    amount=amount,
                    tx_hash=tx_hash,
                    error=str(e),
                )
        
        result = DepositResult(
            success=True,
            deposit_id=deposit_id,
            wallet_id=wallet_id,
            token=token,
            amount=amount,
            tx_hash=tx_hash,
        )
        
        with self._lock:
            self._pending_deposits[deposit_id] = result
        
        return result
    
    # ==================== Withdraw Operations ====================
    
    def estimate_withdraw_fee(
        self,
        token: TokenType,
        amount: Decimal,
        chain: str
    ) -> dict:
        """
        Estimate fees for a withdrawal.
        
        Returns breakdown of network fees and service fees.
        """
        metadata = get_token_metadata(token)
        
        if chain not in metadata.contract_addresses:
            raise ValueError(f"Token {token.value} not available on {chain}")
        
        # Fee estimates by chain (in USD)
        chain_fees = {
            "base": Decimal("0.01"),
            "solana": Decimal("0.001"),
            "polygon": Decimal("0.05"),
            "ethereum": Decimal("2.00"),
        }
        
        network_fee = chain_fees.get(chain, Decimal("0.10"))
        service_fee = Decimal("0.00")  # No service fee for now
        total_fee = network_fee + service_fee
        
        return {
            "token": token.value,
            "chain": chain,
            "amount": str(amount),
            "network_fee": str(network_fee),
            "service_fee": str(service_fee),
            "total_fee": str(total_fee),
            "amount_received": str(amount - total_fee),
            "estimated_time_seconds": {
                "base": 2,
                "solana": 1,
                "polygon": 5,
                "ethereum": 180,
            }.get(chain, 60),
        }
    
    def request_withdraw(
        self,
        wallet_id: str,
        token: TokenType,
        amount: Decimal,
        destination_address: str,
        chain: str
    ) -> WithdrawResult:
        """
        Request a withdrawal to an external address.
        
        In production, this would:
        1. Validate destination address format
        2. Check compliance (AML/sanctions)
        3. Queue for MPC signing
        4. Broadcast to blockchain
        
        For demo, we simulate the process.
        """
        withdraw_id = f"wth_{uuid.uuid4().hex[:16]}"
        metadata = get_token_metadata(token)
        
        # Validate chain support
        if chain not in metadata.contract_addresses:
            return WithdrawResult(
                success=False,
                withdraw_id=withdraw_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                destination_address=destination_address,
                error=f"Token {token.value} not available on {chain}",
                status="failed",
            )
        
        # Validate minimum amount
        if amount < metadata.min_transfer_amount:
            return WithdrawResult(
                success=False,
                withdraw_id=withdraw_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                destination_address=destination_address,
                error=f"Amount below minimum: {metadata.min_transfer_amount}",
                status="failed",
            )
        
        # Calculate fees
        fee_estimate = self.estimate_withdraw_fee(token, amount, chain)
        fee = Decimal(fee_estimate["total_fee"])
        
        # Check wallet balance
        if self._ledger:
            try:
                wallet = self._ledger.get_wallet(wallet_id)
                if not wallet:
                    return WithdrawResult(
                        success=False,
                        withdraw_id=withdraw_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        destination_address=destination_address,
                        error=f"Wallet {wallet_id} not found",
                        status="failed",
                    )
                
                from sardis_core.models.wallet import TokenType as WalletTokenType
                balance = wallet.get_token_balance(WalletTokenType(token.value))
                
                if balance < amount:
                    return WithdrawResult(
                        success=False,
                        withdraw_id=withdraw_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        destination_address=destination_address,
                        error=f"Insufficient balance: have {balance}, need {amount}",
                        status="failed",
                    )
                
                # Deduct from wallet
                wallet.subtract_token_balance(WalletTokenType(token.value), amount)
                self._ledger.update_wallet(wallet)
                
            except Exception as e:
                return WithdrawResult(
                    success=False,
                    withdraw_id=withdraw_id,
                    wallet_id=wallet_id,
                    token=token,
                    amount=amount,
                    destination_address=destination_address,
                    error=str(e),
                    status="failed",
                )
        
        # In demo mode, simulate successful withdrawal
        result = WithdrawResult(
            success=True,
            withdraw_id=withdraw_id,
            wallet_id=wallet_id,
            token=token,
            amount=amount,
            destination_address=destination_address,
            fee=fee,
            tx_hash=f"0x{'0' * 60}{uuid.uuid4().hex[:4]}" if chain != "solana" else f"Demo{uuid.uuid4().hex[:16]}",
            status="confirmed",
        )
        
        with self._lock:
            self._pending_withdrawals[withdraw_id] = result
        
        return result
    
    def get_withdraw_status(self, withdraw_id: str) -> Optional[WithdrawResult]:
        """Get status of a pending withdrawal."""
        return self._pending_withdrawals.get(withdraw_id)
    
    # ==================== Demo/Testing Operations ====================
    
    def mint(
        self,
        wallet_id: str,
        token: TokenType,
        amount: Decimal,
        reason: str = "demo_funding"
    ) -> MintResult:
        """
        Mint tokens directly to a wallet (demo/testing only).
        
        This creates tokens out of thin air for testing purposes.
        In production, this would be disabled or heavily restricted.
        
        Args:
            wallet_id: Wallet to credit
            token: Token to mint
            amount: Amount to mint
            reason: Reason for minting (for audit)
            
        Returns:
            MintResult with success status
        """
        mint_id = f"mint_{uuid.uuid4().hex[:16]}"
        
        if not self._demo_mode:
            return MintResult(
                success=False,
                mint_id=mint_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                reason=reason,
                error="Minting is disabled in production mode",
            )
        
        if amount <= Decimal("0"):
            return MintResult(
                success=False,
                mint_id=mint_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                reason=reason,
                error="Amount must be positive",
            )
        
        # Credit the wallet
        if self._ledger:
            try:
                wallet = self._ledger.get_wallet(wallet_id)
                if not wallet:
                    return MintResult(
                        success=False,
                        mint_id=mint_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        reason=reason,
                        error=f"Wallet {wallet_id} not found",
                    )
                
                from sardis_core.models.wallet import TokenType as WalletTokenType
                wallet.add_token_balance(WalletTokenType(token.value), amount)
                self._ledger.update_wallet(wallet)
                
            except Exception as e:
                return MintResult(
                    success=False,
                    mint_id=mint_id,
                    wallet_id=wallet_id,
                    token=token,
                    amount=amount,
                    reason=reason,
                    error=str(e),
                )
        
        result = MintResult(
            success=True,
            mint_id=mint_id,
            wallet_id=wallet_id,
            token=token,
            amount=amount,
            reason=reason,
        )
        
        with self._lock:
            self._mint_history.append(result)
        
        return result
    
    def burn(
        self,
        wallet_id: str,
        token: TokenType,
        amount: Decimal,
        reason: str = "demo_burn"
    ) -> MintResult:
        """
        Burn tokens from a wallet (demo/testing only).
        
        This destroys tokens for testing purposes.
        
        Args:
            wallet_id: Wallet to debit
            token: Token to burn
            amount: Amount to burn
            reason: Reason for burning (for audit)
            
        Returns:
            MintResult with success status (using same type for simplicity)
        """
        burn_id = f"burn_{uuid.uuid4().hex[:16]}"
        
        if not self._demo_mode:
            return MintResult(
                success=False,
                mint_id=burn_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                reason=reason,
                error="Burning is disabled in production mode",
            )
        
        if amount <= Decimal("0"):
            return MintResult(
                success=False,
                mint_id=burn_id,
                wallet_id=wallet_id,
                token=token,
                amount=amount,
                reason=reason,
                error="Amount must be positive",
            )
        
        # Debit the wallet
        if self._ledger:
            try:
                wallet = self._ledger.get_wallet(wallet_id)
                if not wallet:
                    return MintResult(
                        success=False,
                        mint_id=burn_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        reason=reason,
                        error=f"Wallet {wallet_id} not found",
                    )
                
                from sardis_core.models.wallet import TokenType as WalletTokenType
                balance = wallet.get_token_balance(WalletTokenType(token.value))
                
                if balance < amount:
                    return MintResult(
                        success=False,
                        mint_id=burn_id,
                        wallet_id=wallet_id,
                        token=token,
                        amount=amount,
                        reason=reason,
                        error=f"Insufficient balance: have {balance}, need {amount}",
                    )
                
                wallet.subtract_token_balance(WalletTokenType(token.value), amount)
                self._ledger.update_wallet(wallet)
                
            except Exception as e:
                return MintResult(
                    success=False,
                    mint_id=burn_id,
                    wallet_id=wallet_id,
                    token=token,
                    amount=amount,
                    reason=reason,
                    error=str(e),
                )
        
        result = MintResult(
            success=True,
            mint_id=burn_id,
            wallet_id=wallet_id,
            token=token,
            amount=amount,
            reason=reason,
        )
        
        with self._lock:
            self._mint_history.append(result)
        
        return result
    
    def get_mint_history(self, wallet_id: Optional[str] = None) -> list[MintResult]:
        """Get mint/burn history, optionally filtered by wallet."""
        with self._lock:
            if wallet_id:
                return [m for m in self._mint_history if m.wallet_id == wallet_id]
            return list(self._mint_history)


# Global stablecoin service instance
_stablecoin_service: Optional[StablecoinService] = None


def get_stablecoin_service() -> StablecoinService:
    """Get the global stablecoin service instance."""
    global _stablecoin_service
    if _stablecoin_service is None:
        _stablecoin_service = StablecoinService()
    return _stablecoin_service

