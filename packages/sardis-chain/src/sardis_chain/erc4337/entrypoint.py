"""EntryPoint addresses for ERC-4337."""

from __future__ import annotations

ENTRYPOINT_V07_BY_CHAIN: dict[str, str] = {
    "base_sepolia": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "base": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "ethereum_sepolia": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "ethereum": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "polygon_amoy": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "polygon": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "arbitrum_sepolia": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "arbitrum": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "optimism_sepolia": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
    "optimism": "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
}


def get_entrypoint_v07(chain: str) -> str:
    return ENTRYPOINT_V07_BY_CHAIN.get(chain, ENTRYPOINT_V07_BY_CHAIN["base_sepolia"])
