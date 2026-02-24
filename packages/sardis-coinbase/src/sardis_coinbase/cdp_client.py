"""Coinbase CDP wallet client."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any


class CoinbaseCDPProvider:
    """
    Coinbase CDP Agentic Wallet provider.

    Creates dedicated agent spending wallets and executes USDC payments.
    """

    def __init__(self, api_key_name: str, api_key_private_key: str, network_id: str = "base-mainnet"):
        try:
            from cdp import CdpClient
        except ImportError as exc:
            raise ImportError(
                "cdp-sdk is required. Install with: pip install sardis-coinbase[cdp]"
            ) from exc
        self.client = CdpClient(
            api_key_name=api_key_name,
            api_key_private_key=api_key_private_key,
        )
        self.network_id = network_id

    async def create_agent_wallet(self, agent_id: str) -> dict[str, str]:
        wallet = await asyncio.to_thread(
            self.client.wallets.create,
            network_id=self.network_id,
        )
        return {
            "agent_id": agent_id,
            "cdp_wallet_id": wallet.id,
            "address": wallet.default_address.address_id,
            "network": self.network_id,
        }

    async def get_wallet_balance(self, cdp_wallet_id: str, token: str = "usdc") -> Decimal:
        wallet = await asyncio.to_thread(self.client.wallets.get, cdp_wallet_id)
        balance = await asyncio.to_thread(wallet.balance, token)
        return Decimal(str(balance))

    async def fund_from_turnkey(
        self,
        cdp_wallet_id: str,
        turnkey_address: str,
        amount_usdc: Decimal,
        chain_executor: Any,
    ) -> str:
        """
        Transfer USDC from Turnkey-controlled address to CDP wallet.

        The provided executor must implement `send_erc20(...)`.
        """
        cdp_wallet = await asyncio.to_thread(self.client.wallets.get, cdp_wallet_id)
        destination = cdp_wallet.default_address.address_id
        if not hasattr(chain_executor, "send_erc20"):
            raise ValueError("chain_executor must provide send_erc20 for CDP funding")
        return await chain_executor.send_erc20(
            from_address=turnkey_address,
            to_address=destination,
            amount=amount_usdc,
            token="USDC",
            chain="base",
        )

    async def send_usdc(self, cdp_wallet_id: str, to_address: str, amount_usdc: Decimal) -> str:
        wallet = await asyncio.to_thread(self.client.wallets.get, cdp_wallet_id)
        transfer = await asyncio.to_thread(
            wallet.transfer,
            amount=float(amount_usdc),
            asset_id="usdc",
            destination=to_address,
            gasless=True,
        )
        await asyncio.to_thread(transfer.wait)
        return transfer.transaction.transaction_hash
