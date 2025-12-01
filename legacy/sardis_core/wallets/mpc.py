"""MPC (Multi-Party Computation) Wallet Provider Interface.

This module provides an abstraction layer for MPC wallet providers,
enabling secure key management without exposing raw private keys.

Supported providers (conceptual integration):
- Fireblocks
- Fordefi
- Safe (with MPC modules)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
import secrets


class MPCProviderType(str, Enum):
    """Supported MPC wallet providers."""
    FIREBLOCKS = "fireblocks"
    FORDEFI = "fordefi"
    SAFE = "safe"
    MOCK = "mock"  # For testing


class TransactionPolicyAction(str, Enum):
    """Actions for transaction policy rules."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    TWO_FACTOR = "two_factor"


@dataclass
class TransactionPolicy:
    """Policy rules for transaction signing."""
    policy_id: str
    name: str
    max_amount: Optional[Decimal] = None
    max_daily_volume: Optional[Decimal] = None
    allowed_destinations: List[str] = field(default_factory=list)
    blocked_destinations: List[str] = field(default_factory=list)
    require_approval_above: Optional[Decimal] = None
    whitelisted_tokens: List[str] = field(default_factory=list)
    action_on_policy_breach: TransactionPolicyAction = TransactionPolicyAction.DENY
    is_active: bool = True


@dataclass
class MPCWallet:
    """Represents an MPC-managed wallet."""
    wallet_id: str
    address: str
    chain_ids: List[int]
    provider: MPCProviderType
    policy: Optional[TransactionPolicy] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "chain_ids": self.chain_ids,
            "provider": self.provider.value,
            "policy_id": self.policy.policy_id if self.policy else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class SigningRequest:
    """Request to sign a transaction via MPC."""
    request_id: str
    wallet_id: str
    chain_id: int
    to_address: str
    value: Decimal  # Native token value
    data: str  # Transaction data (hex)
    gas_limit: int
    gas_price: Decimal
    nonce: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class SigningResult:
    """Result of an MPC signing request."""
    request_id: str
    success: bool
    tx_hash: Optional[str] = None
    signed_tx: Optional[str] = None
    error: Optional[str] = None
    policy_evaluation: Optional[Dict[str, Any]] = None


class MPCWalletProvider(ABC):
    """Abstract base class for MPC wallet providers."""
    
    @property
    @abstractmethod
    def provider_type(self) -> MPCProviderType:
        """Get the provider type."""
        pass
    
    @abstractmethod
    async def create_wallet(
        self,
        chain_ids: List[int],
        policy: Optional[TransactionPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MPCWallet:
        """
        Create a new MPC wallet.
        
        Args:
            chain_ids: List of chain IDs this wallet should support
            policy: Optional transaction policy
            metadata: Optional metadata for the wallet
            
        Returns:
            Created MPCWallet
        """
        pass
    
    @abstractmethod
    async def get_wallet(self, wallet_id: str) -> Optional[MPCWallet]:
        """Get wallet by ID."""
        pass
    
    @abstractmethod
    async def sign_transaction(self, request: SigningRequest) -> SigningResult:
        """
        Request transaction signing from MPC provider.
        
        The provider will:
        1. Evaluate transaction against wallet's policy
        2. If approved, coordinate MPC signing
        3. Return signed transaction or broadcast it
        
        Args:
            request: Signing request details
            
        Returns:
            SigningResult with outcome
        """
        pass
    
    @abstractmethod
    async def update_policy(
        self,
        wallet_id: str,
        policy: TransactionPolicy
    ) -> bool:
        """Update wallet's transaction policy."""
        pass
    
    @abstractmethod
    async def get_address(self, wallet_id: str, chain_id: int) -> Optional[str]:
        """Get wallet address for a specific chain."""
        pass


class MockMPCProvider(MPCWalletProvider):
    """
    Mock MPC provider for development and testing.
    
    Simulates MPC wallet operations without actual key management.
    """
    
    def __init__(self):
        self._wallets: Dict[str, MPCWallet] = {}
        self._policies: Dict[str, TransactionPolicy] = {}
    
    @property
    def provider_type(self) -> MPCProviderType:
        return MPCProviderType.MOCK
    
    async def create_wallet(
        self,
        chain_ids: List[int],
        policy: Optional[TransactionPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MPCWallet:
        """Create a mock MPC wallet."""
        wallet_id = f"mpc_wallet_{secrets.token_hex(8)}"
        address = "0x" + secrets.token_hex(20)
        
        wallet = MPCWallet(
            wallet_id=wallet_id,
            address=address,
            chain_ids=chain_ids,
            provider=self.provider_type,
            policy=policy,
            metadata=metadata or {}
        )
        
        self._wallets[wallet_id] = wallet
        
        if policy:
            self._policies[wallet_id] = policy
        
        return wallet
    
    async def get_wallet(self, wallet_id: str) -> Optional[MPCWallet]:
        """Get wallet by ID."""
        return self._wallets.get(wallet_id)
    
    async def sign_transaction(self, request: SigningRequest) -> SigningResult:
        """
        Simulate MPC transaction signing.
        
        Evaluates policy and returns mock signed transaction.
        """
        wallet = self._wallets.get(request.wallet_id)
        if not wallet:
            return SigningResult(
                request_id=request.request_id,
                success=False,
                error="Wallet not found"
            )
        
        # Evaluate policy
        policy_result = self._evaluate_policy(wallet, request)
        if not policy_result["approved"]:
            return SigningResult(
                request_id=request.request_id,
                success=False,
                error=policy_result.get("reason", "Policy denied"),
                policy_evaluation=policy_result
            )
        
        # Simulate signing
        tx_hash = "0x" + secrets.token_hex(32)
        signed_tx = "0x" + secrets.token_hex(100)  # Mock signed transaction
        
        return SigningResult(
            request_id=request.request_id,
            success=True,
            tx_hash=tx_hash,
            signed_tx=signed_tx,
            policy_evaluation=policy_result
        )
    
    def _evaluate_policy(
        self,
        wallet: MPCWallet,
        request: SigningRequest
    ) -> Dict[str, Any]:
        """Evaluate transaction against wallet policy."""
        policy = wallet.policy
        
        if not policy or not policy.is_active:
            return {"approved": True, "reason": "No active policy"}
        
        # Check max amount
        if policy.max_amount and request.value > policy.max_amount:
            return {
                "approved": False,
                "reason": f"Amount {request.value} exceeds max {policy.max_amount}",
                "policy_rule": "max_amount"
            }
        
        # Check blocked destinations
        if request.to_address.lower() in [d.lower() for d in policy.blocked_destinations]:
            return {
                "approved": False,
                "reason": f"Destination {request.to_address} is blocked",
                "policy_rule": "blocked_destinations"
            }
        
        # Check allowed destinations (if whitelist exists)
        if policy.allowed_destinations:
            if request.to_address.lower() not in [d.lower() for d in policy.allowed_destinations]:
                return {
                    "approved": False,
                    "reason": f"Destination {request.to_address} not in whitelist",
                    "policy_rule": "allowed_destinations"
                }
        
        # Check approval threshold
        if policy.require_approval_above and request.value > policy.require_approval_above:
            return {
                "approved": True,
                "requires_approval": True,
                "reason": "Transaction requires additional approval",
                "policy_rule": "require_approval_above"
            }
        
        return {"approved": True, "reason": "Policy passed"}
    
    async def update_policy(
        self,
        wallet_id: str,
        policy: TransactionPolicy
    ) -> bool:
        """Update wallet policy."""
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return False
        
        wallet.policy = policy
        self._policies[wallet_id] = policy
        return True
    
    async def get_address(self, wallet_id: str, chain_id: int) -> Optional[str]:
        """Get wallet address (same across all EVM chains for simplicity)."""
        wallet = self._wallets.get(wallet_id)
        if not wallet:
            return None
        
        if chain_id not in wallet.chain_ids:
            return None
        
        return wallet.address


class FireblocksMPCProvider(MPCWalletProvider):
    """
    Fireblocks MPC Provider (Placeholder).
    
    In production, this would integrate with Fireblocks SDK:
    - pip install fireblocks-sdk
    - Configure API keys
    - Handle vault accounts and assets
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Fireblocks provider.
        
        Args:
            api_key: Fireblocks API key
            api_secret: Fireblocks API secret (private key)
        """
        # In production:
        # from fireblocks_sdk import FireblocksSDK
        # self.sdk = FireblocksSDK(api_secret, api_key)
        
        self._api_key = api_key
        self._api_secret = api_secret
        
        # Use mock for now
        self._mock = MockMPCProvider()
    
    @property
    def provider_type(self) -> MPCProviderType:
        return MPCProviderType.FIREBLOCKS
    
    async def create_wallet(
        self,
        chain_ids: List[int],
        policy: Optional[TransactionPolicy] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MPCWallet:
        """Create wallet via Fireblocks."""
        # In production:
        # vault_account = self.sdk.create_vault_account(
        #     name=f"sardis_agent_{metadata.get('agent_id', 'unknown')}",
        #     hidden_on_ui=False,
        #     customer_ref_id=metadata.get('agent_id')
        # )
        # ... create wallet addresses for each chain
        
        wallet = await self._mock.create_wallet(chain_ids, policy, metadata)
        wallet.provider = self.provider_type
        return wallet
    
    async def get_wallet(self, wallet_id: str) -> Optional[MPCWallet]:
        """Get wallet from Fireblocks."""
        return await self._mock.get_wallet(wallet_id)
    
    async def sign_transaction(self, request: SigningRequest) -> SigningResult:
        """Sign transaction via Fireblocks."""
        # In production:
        # tx = self.sdk.create_transaction(
        #     asset_id="ETH",  # or appropriate asset
        #     source={"type": "VAULT_ACCOUNT", "id": vault_id},
        #     destination={"type": "ONE_TIME_ADDRESS", "oneTimeAddress": {"address": request.to_address}},
        #     amount=str(request.value),
        #     fee_level="MEDIUM"
        # )
        
        return await self._mock.sign_transaction(request)
    
    async def update_policy(
        self,
        wallet_id: str,
        policy: TransactionPolicy
    ) -> bool:
        """Update policy in Fireblocks."""
        return await self._mock.update_policy(wallet_id, policy)
    
    async def get_address(self, wallet_id: str, chain_id: int) -> Optional[str]:
        """Get address from Fireblocks."""
        return await self._mock.get_address(wallet_id, chain_id)


def get_mpc_provider(
    provider_type: MPCProviderType = MPCProviderType.MOCK,
    **kwargs
) -> MPCWalletProvider:
    """
    Factory function to get MPC provider.
    
    Args:
        provider_type: Type of provider to use
        **kwargs: Provider-specific configuration
        
    Returns:
        Configured MPCWalletProvider
    """
    if provider_type == MPCProviderType.MOCK:
        return MockMPCProvider()
    elif provider_type == MPCProviderType.FIREBLOCKS:
        return FireblocksMPCProvider(
            api_key=kwargs.get("api_key", ""),
            api_secret=kwargs.get("api_secret", "")
        )
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")

