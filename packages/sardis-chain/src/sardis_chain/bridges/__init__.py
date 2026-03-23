"""Cross-chain bridge adapters.

Each adapter implements quote / initiate_transfer / check_status
for a specific bridge protocol.
"""

from .relay import BridgeQuote, BridgeTransfer, RelayBridgeAdapter

__all__ = [
    "BridgeQuote",
    "BridgeTransfer",
    "RelayBridgeAdapter",
]
