"""ERC-4337 paymaster clients (Pimlico + Circle)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from .user_operation import UserOperation

logger = logging.getLogger(__name__)


class PaymasterProvider(str, Enum):
    """Supported paymaster providers."""
    PIMLICO = "pimlico"
    CIRCLE = "circle"


@dataclass
class PaymasterConfig:
    url: str
    timeout_seconds: float = 30.0
    provider: PaymasterProvider = PaymasterProvider.PIMLICO


@dataclass
class SponsoredUserOperation:
    paymaster_and_data: str
    paymaster: str = ""
    paymaster_verification_gas_limit: int = 0
    paymaster_post_op_gas_limit: int = 0


# Circle Paymaster v0.8 mainnet addresses (all chains, permissionless, no API key needed)
# Reference: https://developers.circle.com/paymaster
CIRCLE_PAYMASTER_ADDRESSES: dict[str, str] = {
    "base": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
    "arbitrum": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
    "ethereum": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
    "optimism": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
    "polygon": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
    "avalanche": "0x0578cFB241215b77442a541325d6A4E6dFE700Ec",
}

# Circle Paymaster v0.8 testnet addresses (all testnets)
CIRCLE_PAYMASTER_V08_ADDRESSES: dict[str, str] = {
    "base_sepolia": "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
    "arbitrum_sepolia": "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
    "ethereum_sepolia": "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
    "optimism_sepolia": "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
    "polygon_amoy": "0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966",
}

# USDC addresses for paymaster approval
USDC_FOR_PAYMASTER: dict[str, str] = {
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
}


class PaymasterClient:
    """Pimlico-compatible paymaster client (sponsor model)."""

    def __init__(self, config: PaymasterConfig):
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = await self._client.post(self._config.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(f"Paymaster RPC error ({method}): {data['error']}")
        return data.get("result")

    async def sponsor_user_operation(
        self,
        user_op: UserOperation,
        entrypoint: str,
        chain: str,
        sponsorship_policy_id: str | None = None,
    ) -> SponsoredUserOperation:
        result = await self._rpc(
            "pm_sponsorUserOperation",
            [
                user_op.to_rpc(),
                entrypoint,
                {
                    "sponsorshipPolicyId": sponsorship_policy_id or f"sardis-{chain}",
                },
            ],
        )
        if not isinstance(result, dict) or not isinstance(result.get("paymasterAndData"), str):
            raise RuntimeError("Paymaster returned invalid sponsorship payload")
        return SponsoredUserOperation(paymaster_and_data=result["paymasterAndData"])

    async def close(self) -> None:
        await self._client.aclose()


class CirclePaymasterClient:
    """Circle Paymaster client — users pay gas in USDC.

    Circle's permissionless paymaster allows ERC-4337 user operations
    to pay gas fees in USDC instead of native tokens. No API key required.
    10% surcharge on gas fees on Base and Arbitrum.

    Supports ERC-4337 v0.7 and v0.8.

    Reference: https://developers.circle.com/paymaster
    """

    def __init__(
        self,
        bundler_url: str,
        *,
        erc4337_version: str = "v0.7",
        timeout_seconds: float = 30.0,
    ):
        self._bundler_url = bundler_url
        self._version = erc4337_version
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    def get_paymaster_address(self, chain: str) -> str:
        """Get Circle Paymaster address for a given chain.

        Testnet chains (base_sepolia, arbitrum_sepolia, etc.) use the testnet address.
        All mainnet chains use the v0.8 mainnet address.
        """
        # Testnet chains are in the V08 testnet dict
        addr = CIRCLE_PAYMASTER_V08_ADDRESSES.get(chain)
        if addr:
            return addr
        # Mainnet chains
        addr = CIRCLE_PAYMASTER_ADDRESSES.get(chain)
        if not addr:
            raise ValueError(
                f"Circle Paymaster not available on '{chain}'. "
                f"Mainnet chains: {list(CIRCLE_PAYMASTER_ADDRESSES.keys())}. "
                f"Testnet chains: {list(CIRCLE_PAYMASTER_V08_ADDRESSES.keys())}."
            )
        return addr

    async def sponsor_user_operation(
        self,
        user_op: UserOperation,
        entrypoint: str,
        chain: str,
    ) -> SponsoredUserOperation:
        """Sponsor a user operation using Circle Paymaster (USDC gas).

        The Circle Paymaster requires the user to have approved USDC spending
        for the paymaster contract. The paymaster data encodes:
        - mode byte (0x00 for ERC-20 token payment)
        - USDC token address
        - permit amount
        - permit signature (if using EIP-2612 permit)

        For the simplest integration, the user pre-approves USDC to the
        paymaster and the paymaster deducts gas cost in USDC.
        """
        paymaster_address = self.get_paymaster_address(chain)
        usdc_address = USDC_FOR_PAYMASTER.get(chain)
        if not usdc_address:
            raise ValueError(f"USDC address not configured for chain '{chain}'")

        # Build paymaster data: mode(uint8) + token(address) + maxCost(uint256)
        # Mode 0 = ERC-20 token payment with pre-approval
        mode = "00"
        token_padded = usdc_address.lower().removeprefix("0x").zfill(64)
        # Max USDC cost for gas: 10 USDC (10_000_000 minor units) — generous upper bound
        max_cost = hex(10_000_000)[2:].zfill(64)
        paymaster_data = f"0x{mode}{token_padded}{max_cost}"

        result = SponsoredUserOperation(
            paymaster=paymaster_address,
            paymaster_and_data=f"{paymaster_address}{paymaster_data[2:]}",
            paymaster_verification_gas_limit=200_000,
            paymaster_post_op_gas_limit=15_000,
        )

        logger.info(
            "Circle Paymaster sponsorship prepared: chain=%s, paymaster=%s",
            chain, paymaster_address,
        )
        return result

    @staticmethod
    def encode_usdc_approve(chain: str, amount: int = 10_000_000) -> tuple[str, str]:
        """Encode USDC approve call for Circle Paymaster.

        Returns (usdc_address, calldata) for an approve transaction.
        Must be called once before using Circle Paymaster.
        """
        usdc = USDC_FOR_PAYMASTER.get(chain)
        if not usdc:
            raise ValueError(f"USDC not configured for chain '{chain}'")

        paymaster = (
            CIRCLE_PAYMASTER_V08_ADDRESSES.get(chain)
            or CIRCLE_PAYMASTER_ADDRESSES.get(chain)
        )
        if not paymaster:
            raise ValueError(f"Circle Paymaster not available on '{chain}'")

        spender_padded = paymaster.lower().removeprefix("0x").zfill(64)
        amount_hex = hex(amount)[2:].zfill(64)
        calldata = f"0x095ea7b3{spender_padded}{amount_hex}"
        return usdc, calldata

    async def close(self) -> None:
        await self._client.aclose()
