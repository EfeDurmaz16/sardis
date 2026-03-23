"""Tempo Account Factory — passkey accounts and agent key provisioning.

Tempo accounts use passkeys (WebAuthn) for end users and
Access Keys from the Account Keychain for AI agents.

Account hierarchy:
  1. Root Account (passkey) → owned by human principal
  2. Access Key (secp256k1/p256) → delegated to AI agent
  3. Sardis Policy Layer → NLP + anomaly detection + audit

No Safe contracts needed on Tempo — the protocol handles
account abstraction natively via type 0x76 transactions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.wallet.tempo_accounts")


@dataclass
class TempoAccount:
    """A Tempo account (passkey-based or programmatic)."""

    account_id: str = field(default_factory=lambda: f"tacc_{uuid4().hex[:12]}")
    address: str = ""
    account_type: str = "passkey"  # passkey, programmatic, multisig
    owner_id: str = ""  # Sardis user/org ID

    # Passkey info (for passkey accounts)
    credential_id: str | None = None
    public_key_cose: bytes | None = None

    # Key management
    root_key_type: str = "webauthn"  # webauthn, secp256k1, p256
    access_key_count: int = 0

    # Chain
    chain_id: int = 4217  # Tempo mainnet
    is_active: bool = True

    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TempoAccountFactory:
    """Creates and manages Tempo accounts.

    For end users: passkey-based accounts via WebAuthn
    For AI agents: programmatic accounts with scoped Access Keys
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.tempo.xyz",
        chain_id: int = 4217,
        turnkey_client=None,
    ) -> None:
        self._rpc_url = rpc_url
        self._chain_id = chain_id
        self._turnkey = turnkey_client
        self._accounts: dict[str, TempoAccount] = {}

    async def create_passkey_account(
        self,
        owner_id: str,
        credential_id: str,
        public_key_cose: bytes,
    ) -> TempoAccount:
        """Create a passkey-based Tempo account for an end user.

        Uses WebAuthn credential for native account creation.
        """
        account = TempoAccount(
            account_type="passkey",
            owner_id=owner_id,
            credential_id=credential_id,
            public_key_cose=public_key_cose,
            root_key_type="webauthn",
            chain_id=self._chain_id,
        )

        # In production: submit account creation tx to Tempo
        # The protocol creates the account from the WebAuthn credential
        account.address = await self._deploy_account(account)

        self._accounts[account.account_id] = account
        logger.info("Created passkey account %s for %s", account.account_id, owner_id)
        return account

    async def create_programmatic_account(
        self,
        owner_id: str,
    ) -> TempoAccount:
        """Create a programmatic Tempo account (Turnkey-managed root key).

        Used for enterprise accounts where the root key is
        managed by Turnkey MPC custody.
        """
        account = TempoAccount(
            account_type="programmatic",
            owner_id=owner_id,
            root_key_type="secp256k1",
            chain_id=self._chain_id,
        )

        # Create root key via Turnkey
        if self._turnkey:
            key_result = await self._turnkey.create_private_key(
                key_name=f"tempo-{account.account_id}",
                curve="CURVE_SECP256K1",
            )
            account.address = key_result.get("address", "")

        self._accounts[account.account_id] = account
        logger.info("Created programmatic account %s for %s", account.account_id, owner_id)
        return account

    async def get_account(self, account_id: str) -> TempoAccount | None:
        return self._accounts.get(account_id)

    async def get_accounts_for_owner(self, owner_id: str) -> list[TempoAccount]:
        return [
            a for a in self._accounts.values()
            if a.owner_id == owner_id and a.is_active
        ]

    async def _deploy_account(self, account: TempoAccount) -> str:
        """Deploy account on Tempo (derive address from credential)."""
        # In production: compute counterfactual address from credential
        # and submit account creation tx
        import hashlib
        if account.credential_id:
            addr_hash = hashlib.sha256(account.credential_id.encode()).hexdigest()[:40]
            return f"0x{addr_hash}"
        return f"0x{'0' * 40}"
