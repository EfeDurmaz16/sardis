"""Dakota provider package.

Dakota is a crypto-native stablecoin platform: inbound fiat (ACH / Fedwire /
SWIFT / SEPA) auto-settles to USDC on a destination wallet (Base, Solana, …),
and outbound transfers can pay out to a bank (offramp) or to a crypto wallet.
Accounts are *named* (customer-titled) and assets are backed by U.S.
Treasuries.

Custody model: ``PARTNER_CUSTODIED`` — Dakota custodies the fiat/USDC balance
while a rail settles; Sardis never holds the funds and no adapter here
authorizes a movement (the orchestrator/moat does).

Public surface:

* :class:`DakotaClient` — thin env-gated httpx client (Ed25519 webhooks).
* :class:`DakotaFiatAccountAdapter` — :class:`FiatAccountPort`.
"""

from __future__ import annotations

from .adapter import DakotaFiatAccountAdapter
from .client import DakotaClient, DakotaConfig

__all__ = [
    "DakotaClient",
    "DakotaConfig",
    "DakotaFiatAccountAdapter",
]
