"""
HD (Hierarchical Deterministic) Wallet path customization for Sardis.

Implements BIP-32/BIP-44/BIP-84 path derivation with custom path support
for different chains and use cases.

Features:
- Standard BIP-44 path derivation
- Custom path templates for different use cases
- Multi-chain address derivation
- Path validation and security checks
- Account and address gap limit management
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HDPathPurpose(int, Enum):
    """BIP purpose values for HD derivation."""
    BIP44 = 44  # Legacy (P2PKH)
    BIP49 = 49  # Nested SegWit (P2SH-P2WPKH)
    BIP84 = 84  # Native SegWit (P2WPKH)
    BIP86 = 86  # Taproot (P2TR)


class CoinType(int, Enum):
    """SLIP-44 coin type values."""
    BITCOIN = 0
    BITCOIN_TESTNET = 1
    ETHEREUM = 60
    SOLANA = 501
    POLYGON = 60  # EVM chains use 60
    BASE = 60
    ARBITRUM = 60
    OPTIMISM = 60
    AVALANCHE = 60


# Chain to coin type mapping
CHAIN_COIN_TYPES: Dict[str, int] = {
    "bitcoin": CoinType.BITCOIN,
    "bitcoin_testnet": CoinType.BITCOIN_TESTNET,
    "ethereum": CoinType.ETHEREUM,
    "polygon": CoinType.ETHEREUM,
    "base": CoinType.ETHEREUM,
    "arbitrum": CoinType.ETHEREUM,
    "optimism": CoinType.ETHEREUM,
    "avalanche": CoinType.ETHEREUM,
    "solana": CoinType.SOLANA,
}

# Default purposes for chains
CHAIN_DEFAULT_PURPOSE: Dict[str, HDPathPurpose] = {
    "bitcoin": HDPathPurpose.BIP84,  # Native SegWit
    "ethereum": HDPathPurpose.BIP44,
    "polygon": HDPathPurpose.BIP44,
    "base": HDPathPurpose.BIP44,
    "solana": HDPathPurpose.BIP44,
}


@dataclass
class HDPathComponent:
    """A single component of an HD derivation path."""
    index: int
    hardened: bool = False

    def __str__(self) -> str:
        suffix = "'" if self.hardened else ""
        return f"{self.index}{suffix}"

    @classmethod
    def from_string(cls, s: str) -> "HDPathComponent":
        """Parse a path component from string."""
        s = s.strip()
        hardened = s.endswith("'") or s.endswith("h") or s.endswith("H")
        index_str = s.rstrip("'hH")
        return cls(index=int(index_str), hardened=hardened)


@dataclass
class HDPath:
    """
    Represents a complete HD derivation path.

    Standard BIP-44 format: m / purpose' / coin_type' / account' / change / address_index
    """
    purpose: int
    coin_type: int
    account: int = 0
    change: int = 0  # 0 = external, 1 = internal (change)
    address_index: int = 0

    # Path configuration
    purpose_hardened: bool = True
    coin_type_hardened: bool = True
    account_hardened: bool = True
    change_hardened: bool = False
    address_hardened: bool = False

    def __str__(self) -> str:
        """Convert to path string."""
        parts = ["m"]

        def fmt(val: int, hardened: bool) -> str:
            return f"{val}'" if hardened else str(val)

        parts.append(fmt(self.purpose, self.purpose_hardened))
        parts.append(fmt(self.coin_type, self.coin_type_hardened))
        parts.append(fmt(self.account, self.account_hardened))
        parts.append(fmt(self.change, self.change_hardened))
        parts.append(fmt(self.address_index, self.address_hardened))

        return "/".join(parts)

    def to_list(self) -> List[Tuple[int, bool]]:
        """Convert to list of (index, hardened) tuples."""
        return [
            (self.purpose, self.purpose_hardened),
            (self.coin_type, self.coin_type_hardened),
            (self.account, self.account_hardened),
            (self.change, self.change_hardened),
            (self.address_index, self.address_hardened),
        ]

    @classmethod
    def parse(cls, path_string: str) -> "HDPath":
        """
        Parse a path string into an HDPath object.

        Args:
            path_string: Path in format "m/44'/60'/0'/0/0"

        Returns:
            HDPath object
        """
        path_string = path_string.strip().lower()

        # Handle 'm' prefix
        if path_string.startswith("m/"):
            path_string = path_string[2:]
        elif path_string.startswith("m"):
            path_string = path_string[1:]

        parts = path_string.split("/")
        if len(parts) < 5:
            raise ValueError(f"Invalid HD path: expected at least 5 components, got {len(parts)}")

        components = [HDPathComponent.from_string(p) for p in parts[:5]]

        return cls(
            purpose=components[0].index,
            coin_type=components[1].index,
            account=components[2].index,
            change=components[3].index,
            address_index=components[4].index,
            purpose_hardened=components[0].hardened,
            coin_type_hardened=components[1].hardened,
            account_hardened=components[2].hardened,
            change_hardened=components[3].hardened,
            address_hardened=components[4].hardened,
        )

    @classmethod
    def for_chain(
        cls,
        chain: str,
        account: int = 0,
        address_index: int = 0,
        change: int = 0,
        purpose: Optional[int] = None,
    ) -> "HDPath":
        """
        Create an HD path for a specific chain.

        Args:
            chain: Chain identifier (e.g., "ethereum", "base")
            account: Account index
            address_index: Address index
            change: Change index (0 = external, 1 = internal)
            purpose: Optional purpose override

        Returns:
            HDPath for the chain
        """
        coin_type = CHAIN_COIN_TYPES.get(chain, CoinType.ETHEREUM)
        default_purpose = CHAIN_DEFAULT_PURPOSE.get(chain, HDPathPurpose.BIP44)

        return cls(
            purpose=purpose if purpose is not None else default_purpose,
            coin_type=coin_type,
            account=account,
            change=change,
            address_index=address_index,
        )

    def derive_child(self, index: int, hardened: bool = False) -> "HDPath":
        """Create a new path with incremented address index."""
        return HDPath(
            purpose=self.purpose,
            coin_type=self.coin_type,
            account=self.account,
            change=self.change,
            address_index=index,
            purpose_hardened=self.purpose_hardened,
            coin_type_hardened=self.coin_type_hardened,
            account_hardened=self.account_hardened,
            change_hardened=self.change_hardened,
            address_hardened=hardened,
        )

    def next_address(self) -> "HDPath":
        """Get path for next address."""
        return self.derive_child(self.address_index + 1, self.address_hardened)

    def validate(self) -> List[str]:
        """Validate the path configuration."""
        errors = []

        # Check for standard compliance
        if self.purpose not in [44, 49, 84, 86]:
            errors.append(f"Non-standard purpose: {self.purpose}")

        # Check hardening requirements
        if not self.purpose_hardened:
            errors.append("Purpose should be hardened for security")
        if not self.coin_type_hardened:
            errors.append("Coin type should be hardened for security")
        if not self.account_hardened:
            errors.append("Account should be hardened for security")

        # Check index bounds
        if self.address_index > 2147483647:
            errors.append("Address index exceeds maximum value")
        if self.account > 2147483647:
            errors.append("Account index exceeds maximum value")

        return errors


@dataclass
class HDPathTemplate:
    """
    Template for generating HD paths with variable substitution.

    Supports templates like:
    - "m/44'/60'/{account}'/{change}/{index}"
    - "m/84'/0'/{account}'/0/{index}"
    """
    template: str
    name: str
    description: str = ""
    chain: Optional[str] = None
    default_account: int = 0
    default_change: int = 0
    max_account: int = 100
    max_address_gap: int = 20  # BIP-44 gap limit

    def render(
        self,
        account: Optional[int] = None,
        change: Optional[int] = None,
        index: int = 0,
    ) -> str:
        """Render the template with values."""
        path = self.template.format(
            account=account if account is not None else self.default_account,
            change=change if change is not None else self.default_change,
            index=index,
        )
        return path

    def to_hd_path(
        self,
        account: Optional[int] = None,
        index: int = 0,
        change: Optional[int] = None,
    ) -> HDPath:
        """Convert template to HDPath with given values."""
        path_str = self.render(account, change, index)
        return HDPath.parse(path_str)


# Standard path templates
STANDARD_TEMPLATES: Dict[str, HDPathTemplate] = {
    "bip44_eth": HDPathTemplate(
        template="m/44'/60'/{account}'/0/{index}",
        name="BIP-44 Ethereum",
        description="Standard Ethereum path (MetaMask, etc.)",
        chain="ethereum",
    ),
    "bip44_btc": HDPathTemplate(
        template="m/44'/0'/{account}'/0/{index}",
        name="BIP-44 Bitcoin",
        description="Standard Bitcoin legacy path",
        chain="bitcoin",
    ),
    "bip84_btc": HDPathTemplate(
        template="m/84'/0'/{account}'/0/{index}",
        name="BIP-84 Bitcoin",
        description="Bitcoin native SegWit path",
        chain="bitcoin",
    ),
    "bip44_sol": HDPathTemplate(
        template="m/44'/501'/{account}'/0'",
        name="BIP-44 Solana",
        description="Standard Solana path",
        chain="solana",
    ),
    "ledger_eth": HDPathTemplate(
        template="m/44'/60'/{account}'/0/{index}",
        name="Ledger Ethereum",
        description="Ledger Live Ethereum path",
        chain="ethereum",
    ),
    "sardis_agent": HDPathTemplate(
        template="m/44'/60'/{account}'/0/{index}",
        name="Sardis Agent",
        description="Default path for Sardis AI agents",
        chain="base",
        max_address_gap=50,  # Higher gap for agents
    ),
}


@dataclass
class DerivedAddress:
    """A derived address with its path information."""
    address: str
    path: str
    path_obj: HDPath
    chain: str
    public_key: Optional[bytes] = None
    derived_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    label: Optional[str] = None
    is_used: bool = False
    last_used_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "address": self.address,
            "path": self.path,
            "chain": self.chain,
            "derived_at": self.derived_at.isoformat(),
            "label": self.label,
            "is_used": self.is_used,
        }


class HDDerivationProvider(Protocol):
    """Protocol for HD key derivation providers."""

    async def derive_key(
        self,
        master_key_ref: str,
        path: HDPath,
    ) -> Dict[str, Any]:
        """
        Derive a key at the given path.

        Returns dict with 'public_key', 'address', etc.
        """
        ...

    async def derive_address(
        self,
        master_key_ref: str,
        path: HDPath,
        chain: str,
    ) -> str:
        """Derive an address at the given path for a chain."""
        ...


@dataclass
class HDWalletConfig:
    """Configuration for HD wallet derivation."""
    # Default template
    default_template: str = "bip44_eth"

    # Account management
    max_accounts: int = 100
    default_account: int = 0

    # Address gap limit (BIP-44)
    address_gap_limit: int = 20
    internal_gap_limit: int = 20

    # Security settings
    require_hardened_purpose: bool = True
    require_hardened_coin_type: bool = True
    require_hardened_account: bool = True

    # Custom templates
    custom_templates: Dict[str, HDPathTemplate] = field(default_factory=dict)

    def get_template(self, name: str) -> Optional[HDPathTemplate]:
        """Get a template by name."""
        if name in self.custom_templates:
            return self.custom_templates[name]
        return STANDARD_TEMPLATES.get(name)


class HDWalletManager:
    """
    Manages HD wallet path derivation and address generation.

    Features:
    - BIP-32/44/84 compliant derivation
    - Custom path template support
    - Multi-chain address generation
    - Gap limit management
    - Address labeling and tracking
    """

    def __init__(
        self,
        config: Optional[HDWalletConfig] = None,
        derivation_provider: Optional[HDDerivationProvider] = None,
    ):
        self._config = config or HDWalletConfig()
        self._provider = derivation_provider

        # Storage (in production, use database)
        self._derived_addresses: Dict[str, Dict[str, DerivedAddress]] = {}  # wallet_id -> path -> address
        self._wallet_configs: Dict[str, Dict[str, Any]] = {}  # wallet_id -> config
        self._address_indices: Dict[str, Dict[str, int]] = {}  # wallet_id -> (chain, account) -> next_index

    def create_path(
        self,
        chain: str,
        account: int = 0,
        address_index: int = 0,
        change: int = 0,
        template: Optional[str] = None,
    ) -> HDPath:
        """
        Create an HD path for a chain.

        Args:
            chain: Chain identifier
            account: Account index
            address_index: Address index
            change: Change index
            template: Optional template name

        Returns:
            HDPath object
        """
        if template:
            tmpl = self._config.get_template(template)
            if tmpl:
                return tmpl.to_hd_path(account=account, index=address_index, change=change)

        return HDPath.for_chain(
            chain=chain,
            account=account,
            address_index=address_index,
            change=change,
        )

    def validate_path(self, path: HDPath) -> Tuple[bool, List[str]]:
        """
        Validate an HD path against security requirements.

        Returns:
            Tuple of (is_valid, list of warnings/errors)
        """
        errors = path.validate()

        # Additional security checks based on config
        if self._config.require_hardened_purpose and not path.purpose_hardened:
            errors.append("Configuration requires hardened purpose")
        if self._config.require_hardened_coin_type and not path.coin_type_hardened:
            errors.append("Configuration requires hardened coin type")
        if self._config.require_hardened_account and not path.account_hardened:
            errors.append("Configuration requires hardened account")

        # Check account limits
        if path.account >= self._config.max_accounts:
            errors.append(f"Account index {path.account} exceeds maximum {self._config.max_accounts}")

        return len(errors) == 0, errors

    async def derive_address(
        self,
        wallet_id: str,
        master_key_ref: str,
        chain: str,
        account: int = 0,
        address_index: Optional[int] = None,
        label: Optional[str] = None,
        template: Optional[str] = None,
    ) -> DerivedAddress:
        """
        Derive a new address for a wallet.

        Args:
            wallet_id: Wallet identifier
            master_key_ref: Reference to master key in MPC provider
            chain: Target chain
            account: Account index
            address_index: Address index (auto-increment if None)
            label: Optional label for the address
            template: Optional template name

        Returns:
            DerivedAddress with path and address information
        """
        # Initialize tracking
        if wallet_id not in self._derived_addresses:
            self._derived_addresses[wallet_id] = {}
        if wallet_id not in self._address_indices:
            self._address_indices[wallet_id] = {}

        # Get next index if not specified
        index_key = f"{chain}_{account}"
        if address_index is None:
            address_index = self._address_indices[wallet_id].get(index_key, 0)

        # Create path
        path = self.create_path(
            chain=chain,
            account=account,
            address_index=address_index,
            template=template,
        )

        # Validate path
        is_valid, errors = self.validate_path(path)
        if not is_valid:
            raise ValueError(f"Invalid path: {', '.join(errors)}")

        # Derive address via provider
        if self._provider:
            address = await self._provider.derive_address(master_key_ref, path, chain)
            key_data = await self._provider.derive_key(master_key_ref, path)
            public_key = key_data.get("public_key")
        else:
            # Mock derivation for testing
            path_hash = hashlib.sha256(f"{master_key_ref}:{path}".encode()).hexdigest()
            address = f"0x{path_hash[:40]}"
            public_key = None

        # Create derived address record
        derived = DerivedAddress(
            address=address,
            path=str(path),
            path_obj=path,
            chain=chain,
            public_key=public_key,
            label=label,
        )

        # Store
        self._derived_addresses[wallet_id][str(path)] = derived
        self._address_indices[wallet_id][index_key] = address_index + 1

        logger.info(
            f"Derived address for wallet {wallet_id}: {address} at {path}"
        )

        return derived

    async def derive_batch(
        self,
        wallet_id: str,
        master_key_ref: str,
        chain: str,
        account: int = 0,
        count: int = 10,
        start_index: int = 0,
    ) -> List[DerivedAddress]:
        """
        Derive multiple addresses in batch.

        Args:
            wallet_id: Wallet identifier
            master_key_ref: Reference to master key
            chain: Target chain
            account: Account index
            count: Number of addresses to derive
            start_index: Starting address index

        Returns:
            List of derived addresses
        """
        addresses = []
        for i in range(count):
            addr = await self.derive_address(
                wallet_id=wallet_id,
                master_key_ref=master_key_ref,
                chain=chain,
                account=account,
                address_index=start_index + i,
            )
            addresses.append(addr)

        return addresses

    def get_derived_addresses(
        self,
        wallet_id: str,
        chain: Optional[str] = None,
        account: Optional[int] = None,
    ) -> List[DerivedAddress]:
        """Get list of derived addresses for a wallet."""
        addresses = list(self._derived_addresses.get(wallet_id, {}).values())

        if chain:
            addresses = [a for a in addresses if a.chain == chain]
        if account is not None:
            addresses = [a for a in addresses if a.path_obj.account == account]

        return sorted(addresses, key=lambda a: (a.chain, a.path_obj.account, a.path_obj.address_index))

    def find_address_by_path(
        self,
        wallet_id: str,
        path: str,
    ) -> Optional[DerivedAddress]:
        """Find a derived address by its path."""
        return self._derived_addresses.get(wallet_id, {}).get(path)

    def find_address(
        self,
        wallet_id: str,
        address: str,
    ) -> Optional[DerivedAddress]:
        """Find a derived address by its address string."""
        for derived in self._derived_addresses.get(wallet_id, {}).values():
            if derived.address.lower() == address.lower():
                return derived
        return None

    def mark_address_used(
        self,
        wallet_id: str,
        address: str,
    ) -> bool:
        """Mark an address as used."""
        derived = self.find_address(wallet_id, address)
        if derived:
            derived.is_used = True
            derived.last_used_at = datetime.now(timezone.utc)
            return True
        return False

    async def get_next_unused_address(
        self,
        wallet_id: str,
        master_key_ref: str,
        chain: str,
        account: int = 0,
    ) -> DerivedAddress:
        """
        Get the next unused address, deriving if necessary.

        Implements BIP-44 gap limit scanning.
        """
        addresses = self.get_derived_addresses(wallet_id, chain, account)

        # Find first unused
        for addr in addresses:
            if not addr.is_used:
                return addr

        # Check gap limit
        if len(addresses) > 0:
            last_used_index = -1
            for addr in addresses:
                if addr.is_used:
                    last_used_index = max(last_used_index, addr.path_obj.address_index)

            next_index = last_used_index + 1
            gap = len(addresses) - next_index

            if gap >= self._config.address_gap_limit:
                # Return first unused instead of deriving new
                for addr in addresses:
                    if not addr.is_used:
                        return addr
                raise ValueError("Gap limit reached - no unused addresses available")

        # Derive new address
        return await self.derive_address(
            wallet_id=wallet_id,
            master_key_ref=master_key_ref,
            chain=chain,
            account=account,
        )

    def add_custom_template(
        self,
        name: str,
        template: str,
        description: str = "",
        chain: Optional[str] = None,
    ) -> HDPathTemplate:
        """Add a custom path template."""
        # Validate template
        try:
            # Test render
            test_path = template.format(account=0, change=0, index=0)
            HDPath.parse(test_path)
        except Exception as e:
            raise ValueError(f"Invalid template: {e}")

        tmpl = HDPathTemplate(
            template=template,
            name=name,
            description=description,
            chain=chain,
        )

        self._config.custom_templates[name] = tmpl
        logger.info(f"Added custom HD template: {name}")

        return tmpl

    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all available path templates."""
        templates = {}

        for name, tmpl in STANDARD_TEMPLATES.items():
            templates[name] = {
                "template": tmpl.template,
                "name": tmpl.name,
                "description": tmpl.description,
                "chain": tmpl.chain,
                "is_custom": False,
            }

        for name, tmpl in self._config.custom_templates.items():
            templates[name] = {
                "template": tmpl.template,
                "name": tmpl.name,
                "description": tmpl.description,
                "chain": tmpl.chain,
                "is_custom": True,
            }

        return templates


# Singleton instance
_hd_wallet_manager: Optional[HDWalletManager] = None


def get_hd_wallet_manager(
    config: Optional[HDWalletConfig] = None,
) -> HDWalletManager:
    """Get the global HD wallet manager instance."""
    global _hd_wallet_manager

    if _hd_wallet_manager is None:
        _hd_wallet_manager = HDWalletManager(config)

    return _hd_wallet_manager


__all__ = [
    "HDPathPurpose",
    "CoinType",
    "HDPathComponent",
    "HDPath",
    "HDPathTemplate",
    "DerivedAddress",
    "HDWalletConfig",
    "HDWalletManager",
    "STANDARD_TEMPLATES",
    "CHAIN_COIN_TYPES",
    "get_hd_wallet_manager",
]
