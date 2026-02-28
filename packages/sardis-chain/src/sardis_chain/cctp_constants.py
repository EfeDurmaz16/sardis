"""Circle CCTP V2 contract addresses and domain mappings.

Cross-Chain Transfer Protocol enables native USDC bridging between
supported chains with zero bridging fees (only gas costs).

Reference: https://developers.circle.com/stablecoins/docs/cctp-getting-started
"""
from __future__ import annotations

# CCTP V2 Domain IDs (assigned by Circle)
CCTP_DOMAINS: dict[str, int] = {
    "ethereum": 0,
    "optimism": 2,
    "arbitrum": 3,
    "base": 6,
    "polygon": 7,
}

# Reverse mapping: domain_id -> chain name
DOMAIN_TO_CHAIN: dict[int, str] = {v: k for k, v in CCTP_DOMAINS.items()}

# CCTP V2 TokenMessenger contract addresses (mainnet)
TOKEN_MESSENGER_ADDRESSES: dict[str, str] = {
    "ethereum": "0xBd3fa81B58Ba92a82136038B25aDec7066af3155",
    "optimism": "0x2B4069517957735bE00ceE0fadAE88a26365528f",
    "arbitrum": "0x19330d10D9Cc8751218eaf51E8885D058642E08A",
    "base": "0x1682Ae6375C4E4A97e4B583BC394c861A46D8962",
    "polygon": "0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE",
}

# CCTP V2 MessageTransmitter contract addresses (mainnet)
MESSAGE_TRANSMITTER_ADDRESSES: dict[str, str] = {
    "ethereum": "0x0a992d191DEeC32aFe36203Ad87D7d289a738F81",
    "optimism": "0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8",
    "arbitrum": "0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca",
    "base": "0xAD09780d193884d503182aD4F75D8d59B696c4D7",
    "polygon": "0xF3be9355363857F3e001be68856A2f96b4C39bA9",
}

# USDC contract addresses per chain (mainnet)
USDC_ADDRESSES: dict[str, str] = {
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
}

# Circle Attestation API
CIRCLE_ATTESTATION_API_URL = "https://iris-api.circle.com/attestations"
CIRCLE_ATTESTATION_API_SANDBOX_URL = "https://iris-api-sandbox.circle.com/attestations"

# Typical bridge times (in seconds)
ESTIMATED_BRIDGE_TIMES: dict[str, int] = {
    "ethereum": 1200,  # ~20 min (L1 finality)
    "optimism": 780,   # ~13 min
    "arbitrum": 780,   # ~13 min
    "base": 780,       # ~13 min
    "polygon": 900,    # ~15 min
}

# ERC-20 approve function selector
ERC20_APPROVE_SELECTOR = "0x095ea7b3"

# CCTP depositForBurn function selector
DEPOSIT_FOR_BURN_SELECTOR = "0x6fd3504e"

# CCTP receiveMessage function selector
RECEIVE_MESSAGE_SELECTOR = "0x57ecfd28"


def get_cctp_domain(chain: str) -> int:
    """Get CCTP domain ID for a chain."""
    domain = CCTP_DOMAINS.get(chain)
    if domain is None:
        raise ValueError(f"Chain '{chain}' not supported by CCTP. Supported: {list(CCTP_DOMAINS.keys())}")
    return domain


def is_cctp_supported(chain: str) -> bool:
    """Check if a chain is supported by CCTP."""
    return chain in CCTP_DOMAINS


def get_bridge_estimate_seconds(from_chain: str, to_chain: str) -> int:
    """Estimate bridge time in seconds based on source chain finality."""
    return max(
        ESTIMATED_BRIDGE_TIMES.get(from_chain, 900),
        ESTIMATED_BRIDGE_TIMES.get(to_chain, 900),
    )


__all__ = [
    "CCTP_DOMAINS",
    "DOMAIN_TO_CHAIN",
    "TOKEN_MESSENGER_ADDRESSES",
    "MESSAGE_TRANSMITTER_ADDRESSES",
    "USDC_ADDRESSES",
    "CIRCLE_ATTESTATION_API_URL",
    "CIRCLE_ATTESTATION_API_SANDBOX_URL",
    "ESTIMATED_BRIDGE_TIMES",
    "get_cctp_domain",
    "is_cctp_supported",
    "get_bridge_estimate_seconds",
]
