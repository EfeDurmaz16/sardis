"""
Chainalysis Sanctions Oracle provider.

Free on-chain smart contract that validates whether a wallet address appears
on OFAC sanctions designations. Deployed on Base, Ethereum, Polygon, Arbitrum,
Optimism, and more. No signup required.

Oracle docs: https://go.chainalysis.com/chainalysis-oracle-docs.html
"""
from __future__ import annotations

import logging
from typing import Any

from sardis_compliance.sanctions import (
    EntityType,
    SanctionsList,
    SanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
)

logger = logging.getLogger(__name__)

# Chainalysis Sanctions Oracle contract addresses per chain
# Same address on most chains, different on Base
ORACLE_ADDRESSES: dict[str, str] = {
    "ethereum": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
    "polygon": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
    "arbitrum": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
    "optimism": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
    "base": "0x3A91A31cB3dC49b4db9Ce721F50a9D076c8D739B",
    "bsc": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
    "avalanche": "0x40C57923924B5c5c5455c48D93317139ADDaC8fb",
}

# Minimal ABI for the Sanctions Oracle — only the view function we need
SANCTIONS_ORACLE_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "addr", "type": "address"}],
        "name": "isSanctioned",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }
]


class ChainalysisOracleProvider(SanctionsProvider):
    """
    Screens wallet addresses via Chainalysis's free on-chain Sanctions Oracle.

    Calls `isSanctioned(address)` on the oracle contract — a view function
    (free, no gas cost via eth_call). Falls back to fail-closed on RPC errors.

    Supported chains: ethereum, polygon, arbitrum, optimism, base, bsc, avalanche.
    Cost: $0/year — free and permissionless.
    """

    def __init__(
        self,
        rpc_urls: dict[str, str] | None = None,
        default_rpc_url: str | None = None,
    ):
        """
        Args:
            rpc_urls: Mapping of chain name → RPC URL. Falls back to env vars.
            default_rpc_url: Default RPC for chains not in rpc_urls.
        """
        self._rpc_urls = rpc_urls or {}
        self._default_rpc_url = default_rpc_url
        self._custom_blocklist: set[str] = set()

    def _get_rpc_url(self, chain: str) -> str | None:
        """Get RPC URL for a chain."""
        import os

        chain_lower = chain.lower()

        # Explicit mapping first
        if chain_lower in self._rpc_urls:
            return self._rpc_urls[chain_lower]

        # Environment variable fallback
        env_key = f"SARDIS_{chain_lower.upper()}_RPC_URL"
        env_url = os.getenv(env_key)
        if env_url:
            return env_url

        # Generic fallback
        generic = os.getenv("SARDIS_BASE_RPC_URL") if chain_lower == "base" else None
        if generic:
            return generic

        return self._default_rpc_url

    async def _check_oracle(self, address: str, chain: str) -> bool | None:
        """
        Call the on-chain oracle. Returns True if sanctioned, False if clean,
        None if the chain is unsupported or RPC fails.
        """
        chain_lower = chain.lower()

        oracle_address = ORACLE_ADDRESSES.get(chain_lower)
        if not oracle_address:
            logger.debug("Chainalysis oracle not available on chain %s", chain)
            return None

        rpc_url = self._get_rpc_url(chain_lower)
        if not rpc_url:
            logger.warning("No RPC URL configured for chain %s", chain)
            return None

        try:
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(oracle_address),
                abi=SANCTIONS_ORACLE_ABI,
            )
            return contract.functions.isSanctioned(
                Web3.to_checksum_address(address)
            ).call()
        except Exception as e:
            logger.warning("Chainalysis oracle call failed on %s: %s", chain, e)
            return None

    async def screen_wallet(self, request: WalletScreeningRequest) -> ScreeningResult:
        """Screen a wallet address via the Chainalysis on-chain oracle."""
        # Check custom blocklist first (instant)
        if request.address.lower() in self._custom_blocklist:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="chainalysis_oracle",
                matches=[{"list": "custom_blocklist", "address": request.address.lower()}],
                reason="Address is on internal blocklist",
            )

        # Call on-chain oracle
        result = await self._check_oracle(request.address, request.chain)

        if result is None:
            # Oracle unavailable — fail-closed
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="chainalysis_oracle",
                reason=f"Chainalysis oracle unavailable on {request.chain} — fail-closed",
            )

        if result:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="chainalysis_oracle",
                matches=[{"list": "OFAC (Chainalysis Oracle)", "address": request.address}],
                reason="Address flagged by Chainalysis Sanctions Oracle",
                lists_checked=[SanctionsList.OFAC],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.address,
            entity_type=EntityType.WALLET,
            provider="chainalysis_oracle",
            lists_checked=[SanctionsList.OFAC],
        )

    async def screen_transaction(self, request: TransactionScreeningRequest) -> ScreeningResult:
        """Screen both sides of a transaction via the on-chain oracle."""
        from_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.from_address, chain=request.chain)
        )
        to_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.to_address, chain=request.chain)
        )

        if from_result.should_block or to_result.should_block:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=from_result.is_sanctioned or to_result.is_sanctioned,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="chainalysis_oracle",
                matches=from_result.matches + to_result.matches,
                reason="Transaction involves sanctioned address (Chainalysis Oracle)",
                lists_checked=[SanctionsList.OFAC],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="chainalysis_oracle",
            lists_checked=[SanctionsList.OFAC],
        )

    async def add_to_blocklist(self, address: str, reason: str) -> bool:
        self._custom_blocklist.add(address.lower())
        logger.info("Chainalysis provider blocklist: added %s (%s)", address, reason)
        return True

    async def remove_from_blocklist(self, address: str) -> bool:
        self._custom_blocklist.discard(address.lower())
        logger.info("Chainalysis provider blocklist: removed %s", address)
        return True
