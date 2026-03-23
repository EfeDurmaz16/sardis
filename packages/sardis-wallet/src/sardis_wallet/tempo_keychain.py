"""Tempo Account Keychain — native spending mandate enforcement.

The Account Keychain precompile at 0xAAAAAAAA00000000000000000000000000000000
provides protocol-level access control:

- Root keys provision scoped Access Keys
- Access Keys have: per-TIP20 spending limits, expiry, key types
- Protocol enforces limits natively — no smart contract needed

This IS the spending mandate primitive on Tempo:
  Root key = human owner (Turnkey-managed)
  Access Key = AI agent with bounded permissions

Sardis adds the intelligence layer on top:
  NLP policy parsing → Access Key parameters
  Anomaly detection on access key usage
  Audit trail linking
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.wallet.tempo_keychain")

KEYCHAIN_PRECOMPILE = "0xAAAAAAAA00000000000000000000000000000000"


@dataclass
class AccessKeyConfig:
    """Configuration for a Tempo Access Key (scoped agent permissions)."""

    # Key identity
    key_type: str = "secp256k1"  # secp256k1, p256, webauthn
    public_key: str = ""

    # Per-token spending limits
    token_limits: dict[str, Decimal] = field(default_factory=dict)
    # e.g., {"0x20c0...": Decimal("1000")} = max 1000 pathUSD

    # Time bounds
    expires_at: datetime | None = None
    valid_from: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Restrictions
    allowed_targets: list[str] | None = None  # Contract addresses this key can call
    max_calls_per_day: int | None = None

    # Metadata
    label: str | None = None  # Human-readable label (e.g., "procurement-agent")
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessKeyRecord:
    """A provisioned access key on the Tempo Account Keychain."""

    key_id: str = field(default_factory=lambda: f"tkey_{uuid4().hex[:12]}")
    account_address: str = ""
    config: AccessKeyConfig = field(default_factory=AccessKeyConfig)
    is_active: bool = True
    provisioned_tx: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TempoKeychainProvider:
    """Manages Tempo Account Keychain access keys for agent wallets.

    Maps Sardis spending policies to Tempo Access Key parameters:
    - max_per_tx → per-TIP20 spending limit
    - mandate_expiry → Access Key expiry timestamp
    - allowed_merchants → allowed_targets (if on-chain)

    Root key management via Turnkey (enterprise MPC custody).
    Access key provisioning via Keychain precompile.
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.tempo.xyz",
        turnkey_client=None,
        executor=None,
    ) -> None:
        self._rpc_url = rpc_url
        self._turnkey = turnkey_client
        self._executor = executor
        self._keys: dict[str, AccessKeyRecord] = {}

    async def provision_access_key(
        self,
        account_address: str,
        agent_id: str,
        token_limits: dict[str, Decimal],
        expires_in_hours: int = 24,
        key_type: str = "secp256k1",
        label: str | None = None,
        allowed_targets: list[str] | None = None,
    ) -> AccessKeyRecord:
        """Provision a scoped Access Key for an AI agent.

        The root key (Turnkey-managed) signs the provisioning transaction
        that grants the agent an Access Key with bounded permissions.
        """
        config = AccessKeyConfig(
            key_type=key_type,
            token_limits=token_limits,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
            allowed_targets=allowed_targets,
            label=label or f"agent-{agent_id}",
            metadata={"agent_id": agent_id},
        )

        # In production: call Keychain precompile to provision the key
        record = AccessKeyRecord(
            account_address=account_address,
            config=config,
        )

        if self._executor:
            # Build the provisioning transaction
            tx_data = self._build_provision_tx(account_address, config)
            receipt = await self._executor.execute_transfer(
                token_address=KEYCHAIN_PRECOMPILE,
                to=account_address,
                amount=0,
                memo=None,
            )
            record.provisioned_tx = receipt.tx_hash

        self._keys[record.key_id] = record
        logger.info(
            "Provisioned access key %s for agent %s on %s",
            record.key_id, agent_id, account_address,
        )
        return record

    async def revoke_access_key(self, key_id: str) -> bool:
        """Revoke an Access Key (removes agent's spending authority)."""
        record = self._keys.get(key_id)
        if not record:
            return False

        record.is_active = False
        record.revoked_at = datetime.now(UTC)

        # In production: call Keychain precompile to revoke
        logger.info("Revoked access key %s", key_id)
        return True

    async def update_limits(
        self,
        key_id: str,
        new_limits: dict[str, Decimal],
    ) -> AccessKeyRecord | None:
        """Update spending limits on an existing Access Key."""
        record = self._keys.get(key_id)
        if not record or not record.is_active:
            return None

        record.config.token_limits = new_limits
        logger.info("Updated limits on access key %s", key_id)
        return record

    def mandate_to_access_key_config(
        self,
        mandate,
        token_address: str = "0x20c0000000000000000000000000000000000000",
    ) -> AccessKeyConfig:
        """Convert a Sardis SpendingMandate to Tempo Access Key parameters.

        This is the bridge between Sardis policy intelligence and
        Tempo protocol-level enforcement.
        """
        token_limits = {}
        if mandate.amount_per_tx:
            token_limits[token_address] = mandate.amount_per_tx
        elif mandate.amount_daily:
            token_limits[token_address] = mandate.amount_daily

        return AccessKeyConfig(
            token_limits=token_limits,
            expires_at=mandate.expires_at,
            valid_from=mandate.valid_from,
            label=f"mandate-{mandate.id}",
            metadata={
                "mandate_id": mandate.id,
                "agent_id": mandate.agent_id,
                "purpose": mandate.purpose_scope,
            },
        )

    def get_active_keys(self, account_address: str) -> list[AccessKeyRecord]:
        """Get all active access keys for an account."""
        return [
            k for k in self._keys.values()
            if k.account_address == account_address and k.is_active
        ]

    def _build_provision_tx(
        self, account: str, config: AccessKeyConfig
    ) -> dict[str, Any]:
        """Build the Keychain precompile transaction for provisioning."""
        # Simplified — actual ABI depends on Keychain precompile interface
        return {
            "to": KEYCHAIN_PRECOMPILE,
            "data": {
                "method": "provisionAccessKey",
                "account": account,
                "keyType": config.key_type,
                "publicKey": config.public_key,
                "tokenLimits": {
                    k: str(v) for k, v in config.token_limits.items()
                },
                "expiresAt": int(config.expires_at.timestamp()) if config.expires_at else 0,
            },
        }
