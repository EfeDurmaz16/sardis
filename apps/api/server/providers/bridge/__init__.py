"""Cross-chain bridge provider package.

Two env-gated providers, each behind :class:`server.providers.ports.BridgePort`:

* **Squid** — v2 intent-based cross-chain aggregation (Axelar / CCTP / LayerZero
  under the hood); live on Tempo day-one for pathUSD (the Base/Solana -> Tempo
  pattern).  Requires ``x-integrator-id`` on every request.  Non-custodial:
  ``POST /v2/route`` returns the ``transactionRequest`` the CustodyPort signs.
* **CCTP v2** — Circle native USDC burn/mint.  Canonical and permissionless;
  no API key (Iris is public).  The adapter ABI-encodes ``depositForBurn`` for
  the source TokenMessengerV2 and the CustodyPort signs it; mint on the
  destination uses the Iris attestation.  Fully non-custodial.

Each activates only when its env is set; otherwise the registry returns the
SIMULATED :class:`server.providers.sandbox.SandboxBridgePort`.  No adapter
authorizes/initiates/settles money — it returns a quote and the already-shaped
transaction.  Money is integer minor units / exact strings; no float, no secret
hardcoded.

See :mod:`server.providers.bridge.client` for the researched 2026 API facts.
"""

from __future__ import annotations

from .adapter import CctpBridgeAdapter, SquidBridgeAdapter
from .client import (
    CCTP_DOMAINS,
    CCTP_FINALITY_FAST,
    CCTP_FINALITY_STANDARD,
    CCTP_MESSAGE_TRANSMITTER_V2,
    CCTP_TOKEN_MESSENGER_V2,
    BridgeQuote,
    CctpClient,
    CctpConfig,
    SquidClient,
    SquidConfig,
)

__all__ = [
    "BridgeQuote",
    "CCTP_DOMAINS",
    "CCTP_FINALITY_FAST",
    "CCTP_FINALITY_STANDARD",
    "CCTP_MESSAGE_TRANSMITTER_V2",
    "CCTP_TOKEN_MESSENGER_V2",
    "CctpBridgeAdapter",
    "CctpClient",
    "CctpConfig",
    "SquidBridgeAdapter",
    "SquidClient",
    "SquidConfig",
]
