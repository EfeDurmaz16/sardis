"""Increase provider package.

Increase is an FDIC partner-bank rails platform: it issues *customer-titled
named accounts* (not pooled FBO) and moves USD over ACH (standard / same-day),
Wire (Fedwire), Real-Time Payments (RTP) and FedNow, plus checks.

Custody model: ``PARTNER_CUSTODIED`` — Increase's partner bank is the custodian
of record for the USD while a rail settles.  Sardis never holds the funds and
no adapter here authorizes a movement; the orchestrator (the moat) does.

Public surface:

* :class:`IncreaseClient` — thin env-gated httpx client (Standard Webhooks).
* :class:`IncreaseFiatAccountAdapter` — :class:`FiatAccountPort`.
* :class:`IncreaseOfframpAdapter` — :class:`OfframpPort` (USD payout to a bank
  via ACH / Wire / RTP; the crypto->fiat leg is settled upstream).
"""

from __future__ import annotations

from .adapter import IncreaseFiatAccountAdapter, IncreaseOfframpAdapter
from .client import IncreaseClient, IncreaseConfig

__all__ = [
    "IncreaseClient",
    "IncreaseConfig",
    "IncreaseFiatAccountAdapter",
    "IncreaseOfframpAdapter",
]
