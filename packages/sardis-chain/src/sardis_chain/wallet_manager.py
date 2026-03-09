"""
Turnkey wallet management for Sardis.

Provides high-level wallet operations:
- Wallet creation with agent binding
- Wallet lookup and caching
- Address derivation per chain
- Key rotation scheduling
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sardis_v2_core import SardisSettings

logger = logging.getLogger(__name__)


@dataclass
class WalletInfo:
    """Information about a Turnkey wallet."""
    wallet_id: str
    wallet_name: str
    addresses: dict[str, str] = field(default_factory=dict)  # chain -> address
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    agent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyRotationSchedule:
    """Key rotation schedule for a wallet."""
    wallet_id: str
    rotation_interval_days: int = 90
    last_rotation: datetime | None = None
    next_rotation: datetime | None = None
    enabled: bool = True


class WalletManager:
    """
    High-level wallet management for Turnkey MPC wallets.

    Features:
    - Create wallets bound to agent IDs
    - Cache wallet information
    - Multi-chain address derivation
    - Key rotation scheduling
    """

    def __init__(self, settings: SardisSettings):
        self._settings = settings
        self._signer = None
        self._wallet_cache: dict[str, WalletInfo] = {}
        self._agent_wallet_map: dict[str, str] = {}  # agent_id -> wallet_id
        self._rotation_schedules: dict[str, KeyRotationSchedule] = {}

    async def _get_signer(self):
        """Get or create Turnkey signer."""
        if self._signer is None:
            from .executor import TurnkeyMPCSigner

            turnkey = self._settings.turnkey
            self._signer = TurnkeyMPCSigner(
                api_base=turnkey.api_base,
                organization_id=turnkey.organization_id,
                api_public_key=turnkey.api_public_key,
                api_private_key=turnkey.api_private_key,
            )
        return self._signer

    async def create_wallet(
        self,
        agent_id: str,
        wallet_name: str | None = None,
    ) -> WalletInfo:
        """
        Create a new wallet for an agent.

        Args:
            agent_id: The agent ID to bind the wallet to
            wallet_name: Optional custom wallet name

        Returns:
            WalletInfo with wallet details and addresses
        """
        signer = await self._get_signer()

        # Generate wallet name if not provided
        if not wallet_name:
            wallet_name = f"sardis-agent-{agent_id[:16]}"

        # Create wallet via Turnkey
        result = await signer.create_wallet(wallet_name)

        wallet_id = result["wallet_id"]
        address = result["address"]

        # Create wallet info
        wallet_info = WalletInfo(
            wallet_id=wallet_id,
            wallet_name=wallet_name,
            addresses={"ethereum": address, "base": address, "polygon": address},
            agent_id=agent_id,
            metadata={"source": "sardis_wallet_manager"},
        )

        # Cache the wallet
        self._wallet_cache[wallet_id] = wallet_info
        self._agent_wallet_map[agent_id] = wallet_id

        # Set up rotation schedule
        self._rotation_schedules[wallet_id] = KeyRotationSchedule(
            wallet_id=wallet_id,
            last_rotation=datetime.now(UTC),
        )

        logger.info(f"Created wallet {wallet_id} for agent {agent_id}")

        return wallet_info

    async def get_wallet(self, wallet_id: str) -> WalletInfo | None:
        """Get wallet information by ID."""
        # Check cache first
        if wallet_id in self._wallet_cache:
            return self._wallet_cache[wallet_id]

        # Fetch from Turnkey
        try:
            signer = await self._get_signer()
            address = await signer.get_address(wallet_id, "ethereum")

            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                wallet_name=f"wallet-{wallet_id[:8]}",
                addresses={"ethereum": address, "base": address, "polygon": address},
            )

            self._wallet_cache[wallet_id] = wallet_info
            return wallet_info

        except Exception as e:
            logger.error(f"Failed to get wallet {wallet_id}: {e}")
            return None

    async def get_wallet_for_agent(self, agent_id: str) -> WalletInfo | None:
        """Get the wallet associated with an agent."""
        wallet_id = self._agent_wallet_map.get(agent_id)
        if wallet_id:
            return await self.get_wallet(wallet_id)
        return None

    async def get_or_create_wallet(self, agent_id: str) -> WalletInfo:
        """Get existing wallet for agent or create a new one."""
        existing = await self.get_wallet_for_agent(agent_id)
        if existing:
            return existing
        return await self.create_wallet(agent_id)

    async def list_wallets(self) -> list[WalletInfo]:
        """List all wallets in the organization."""
        signer = await self._get_signer()

        wallets = await signer.list_wallets()

        result = []
        for wallet in wallets:
            wallet_id = wallet.get("walletId", "")
            wallet_name = wallet.get("walletName", "")

            # Get address for this wallet
            try:
                address = await signer.get_address(wallet_id, "ethereum")
            except Exception:
                address = ""

            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                wallet_name=wallet_name,
                addresses={"ethereum": address} if address else {},
            )

            self._wallet_cache[wallet_id] = wallet_info
            result.append(wallet_info)

        return result

    async def get_address(
        self,
        wallet_id: str,
        chain: str = "ethereum",
    ) -> str:
        """
        Get the address for a wallet on a specific chain.

        For EVM chains (Ethereum, Base, Polygon, etc.), the address is the same.
        """
        # Check cache
        wallet_info = self._wallet_cache.get(wallet_id)
        if wallet_info and chain in wallet_info.addresses:
            return wallet_info.addresses[chain]

        # Fetch from Turnkey
        signer = await self._get_signer()
        address = await signer.get_address(wallet_id, chain)

        # Update cache
        if wallet_info:
            wallet_info.addresses[chain] = address
        else:
            self._wallet_cache[wallet_id] = WalletInfo(
                wallet_id=wallet_id,
                wallet_name=f"wallet-{wallet_id[:8]}",
                addresses={chain: address},
            )

        return address

    def get_rotation_schedule(self, wallet_id: str) -> KeyRotationSchedule | None:
        """Get key rotation schedule for a wallet."""
        return self._rotation_schedules.get(wallet_id)

    async def check_rotation_needed(self, wallet_id: str) -> bool:
        """Check if key rotation is needed for a wallet."""
        schedule = self._rotation_schedules.get(wallet_id)
        if not schedule or not schedule.enabled:
            return False

        if not schedule.last_rotation:
            return True

        age = datetime.now(UTC) - schedule.last_rotation
        return age.days >= schedule.rotation_interval_days

    async def schedule_rotation(
        self,
        wallet_id: str,
        interval_days: int = 90,
    ) -> KeyRotationSchedule:
        """Schedule key rotation for a wallet."""
        from datetime import timedelta

        now = datetime.now(UTC)
        schedule = KeyRotationSchedule(
            wallet_id=wallet_id,
            rotation_interval_days=interval_days,
            last_rotation=now,
            next_rotation=now + timedelta(days=interval_days),
            enabled=True,
        )

        self._rotation_schedules[wallet_id] = schedule
        logger.info(f"Scheduled key rotation for wallet {wallet_id} every {interval_days} days")

        return schedule

    def bind_agent_to_wallet(self, agent_id: str, wallet_id: str) -> None:
        """Bind an agent ID to an existing wallet."""
        self._agent_wallet_map[agent_id] = wallet_id

        wallet_info = self._wallet_cache.get(wallet_id)
        if wallet_info:
            wallet_info.agent_id = agent_id

        logger.info(f"Bound agent {agent_id} to wallet {wallet_id}")

    async def close(self):
        """Close the wallet manager and release resources."""
        if self._signer:
            await self._signer.close()
            self._signer = None


# Singleton instance
_wallet_manager: WalletManager | None = None


def get_wallet_manager(settings: SardisSettings | None = None) -> WalletManager:
    """Get the global wallet manager instance."""
    global _wallet_manager

    if _wallet_manager is None:
        if settings is None:
            from sardis_v2_core import load_settings
            settings = load_settings()
        _wallet_manager = WalletManager(settings)

    return _wallet_manager






