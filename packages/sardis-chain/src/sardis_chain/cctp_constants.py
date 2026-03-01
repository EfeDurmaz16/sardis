"""Circle CCTP V2 contract addresses and domain mappings.

Cross-Chain Transfer Protocol V2 enables native USDC bridging between
supported chains with zero bridging fees (only gas costs).

V2 uses unified contract addresses across all EVM chains.

Reference: https://developers.circle.com/cctp/evm-smart-contracts
"""
from __future__ import annotations

# CCTP V2 Domain IDs (assigned by Circle)
CCTP_DOMAINS: dict[str, int] = {
    "ethereum": 0,
    "avalanche": 1,
    "optimism": 2,
    "arbitrum": 3,
    "base": 6,
    "polygon": 7,
    "unichain": 10,
    "linea": 11,
    "sonic": 13,
    "world_chain": 14,
}

# Reverse mapping: domain_id -> chain name
DOMAIN_TO_CHAIN: dict[int, str] = {v: k for k, v in CCTP_DOMAINS.items()}

# CCTP V2 TokenMessengerV2 — same address on all EVM chains
_TOKEN_MESSENGER_V2 = "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d"
TOKEN_MESSENGER_ADDRESSES: dict[str, str] = {
    chain: _TOKEN_MESSENGER_V2 for chain in CCTP_DOMAINS
}

# CCTP V2 MessageTransmitterV2 — same address on all EVM chains
_MESSAGE_TRANSMITTER_V2 = "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64"
MESSAGE_TRANSMITTER_ADDRESSES: dict[str, str] = {
    chain: _MESSAGE_TRANSMITTER_V2 for chain in CCTP_DOMAINS
}

# CCTP V2 TokenMinterV2 — same address on all EVM chains
TOKEN_MINTER_V2 = "0xfd78EE919681417d192449715b2594ab58f5D002"

# USDC contract addresses per chain (mainnet)
USDC_ADDRESSES: dict[str, str] = {
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "unichain": "0x078D782b760474a361dDA0AF3839290b0EF57AD6",
    "linea": "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",
    "sonic": "0x29219dd400f2Bf60E5a23d13Be72B486D4038894",
    "world_chain": "0x79A02482A880bCE3B13e5da8d5b4645eFf852cc8",
}

# Circle Attestation API (V2 format)
CIRCLE_ATTESTATION_API_URL = "https://iris-api.circle.com/v2/messages"
CIRCLE_ATTESTATION_API_SANDBOX_URL = "https://iris-api-sandbox.circle.com/v2/messages"

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
    "TOKEN_MINTER_V2",
    "USDC_ADDRESSES",
    "CIRCLE_ATTESTATION_API_URL",
    "CIRCLE_ATTESTATION_API_SANDBOX_URL",
    "ESTIMATED_BRIDGE_TIMES",
    "get_cctp_domain",
    "is_cctp_supported",
    "get_bridge_estimate_seconds",
]
