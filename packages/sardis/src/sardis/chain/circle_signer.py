"""Circle Programmable Wallets MPC signer implementation.

Implements MPCSignerPort using Circle's developer-controlled wallets
for transaction signing, supporting both regular transactions and
ERC-4337 UserOperation hash signing.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .executor import MPCSignerPort

if TYPE_CHECKING:
    from sardis_wallet.circle_client import CircleWalletClient

    from .executor import TransactionRequest

logger = logging.getLogger(__name__)


class CircleWalletSigner(MPCSignerPort):
    """MPC signer backed by Circle Programmable Wallets.

    Each instance is bound to a specific Circle wallet ID and address.
    Transaction signing is handled by Circle's infrastructure — private
    keys never leave Circle's secure enclaves.
    """

    def __init__(
        self,
        circle_client: CircleWalletClient,
        wallet_id: str,
        address: str,
    ):
        self._client = circle_client
        self._wallet_id = wallet_id
        self._address = address

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign a transaction via Circle and return the tx hash.

        Args:
            wallet_id: Sardis wallet ID (used for logging; Circle wallet ID
                       is bound at construction time).
            tx: Transaction request with to_address, value, data.

        Returns:
            Transaction hash hex string.
        """
        # Build calldata from TransactionRequest
        calldata = getattr(tx, "data", "0x") or "0x"
        if isinstance(calldata, bytes):
            calldata = "0x" + calldata.hex()

        logger.info(
            "Signing transaction via Circle: sardis_wallet=%s circle_wallet=%s to=%s",
            wallet_id, self._wallet_id, getattr(tx, "to_address", "?"),
        )

        result = await self._client.sign_transaction(
            wallet_id=self._wallet_id,
            raw_transaction=calldata,
        )

        # Poll until confirmed
        confirmed = await self._client.poll_transaction(result.tx_id)
        tx_hash = confirmed.tx_hash or f"0x{result.tx_id}"

        logger.info(
            "Circle transaction confirmed: tx_hash=%s circle_tx=%s",
            tx_hash, result.tx_id,
        )
        return tx_hash

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Return the Circle wallet address.

        Circle SCA wallets have the same address across all EVM chains,
        so the chain parameter is accepted but not used for lookup.
        """
        return self._address

    async def sign_user_operation_hash(
        self,
        wallet_id: str,
        user_op_hash: str,
    ) -> str:
        """Sign an ERC-4337 UserOperation hash via Circle.

        Args:
            wallet_id: Sardis wallet ID.
            user_op_hash: Hex-encoded UserOperation hash to sign.

        Returns:
            Hex-encoded signature.
        """
        logger.info(
            "Signing UserOp hash via Circle: sardis_wallet=%s circle_wallet=%s",
            wallet_id, self._wallet_id,
        )

        # Circle's sign message endpoint handles arbitrary hash signing
        result = await self._client.sign_transaction(
            wallet_id=self._wallet_id,
            raw_transaction=user_op_hash,
        )

        confirmed = await self._client.poll_transaction(result.tx_id)
        return confirmed.tx_hash or f"0x{result.tx_id}"
