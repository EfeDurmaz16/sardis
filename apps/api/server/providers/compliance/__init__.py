"""Compliance provider package.

Two env-gated providers behind the identity/screening ports
:class:`server.providers.ports.KycPort` and
:class:`server.providers.ports.KytPort`:

* **Didit** (``DIDIT_API_KEY``) — one ``/v3/`` API for KYC + KYB (with UBO /
  Key People), AML screening, and HMAC-SHA256 webhooks.  Backs the KYC port
  (KYC/KYB session create + decision + webhook verify) and, for KYT, screens a
  named counterparty via ``POST /v3/aml/``.
* **OpenSanctions** (``OPENSANCTIONS_API_KEY``) — self-serve, pay-as-you-go
  sanctions / PEP / watchlist matching via ``POST /match/{scope}``.  Backs the
  KYT port for on-chain *address* screening and counterparty screening; it is
  the preferred KYT provider when configured (better raw-address coverage).

Each provider activates only when its env key is set; otherwise the registry
returns the SIMULATED :class:`server.providers.sandbox.SandboxKycPort` /
:class:`server.providers.sandbox.SandboxKytPort` so the suite + dev run green
WITHOUT live keys.  KYT is required-in-production: with no real KYT provider in
prod the registry fails closed before handing out a port (no silent sandbox on
a screening path).

No adapter authorizes/initiates/settles money — a KYC adapter only creates an
identity session and reports its status; a KYT adapter only reports a screening
verdict; the orchestrator (moat) decides allow/deny and fails CLOSED on a
screening transport/auth error.  Custody model is ``PARTNER_CUSTODIED`` (a
regulated verification partner performs the check of record; Sardis holds no
funds on these paths).  No secret is hardcoded.

See :mod:`server.providers.compliance.client` for the researched 2026 API facts.
"""

from __future__ import annotations

from .adapter import (
    DiditKycAdapter,
    DiditKytAdapter,
    OpenSanctionsKytAdapter,
)
from .client import (
    DiditClient,
    DiditConfig,
    KycSession,
    OpenSanctionsClient,
    OpenSanctionsConfig,
    ScreeningHit,
    ScreeningResult,
)

__all__ = [
    "DiditClient",
    "DiditConfig",
    "DiditKycAdapter",
    "DiditKytAdapter",
    "KycSession",
    "OpenSanctionsClient",
    "OpenSanctionsConfig",
    "OpenSanctionsKytAdapter",
    "ScreeningHit",
    "ScreeningResult",
]
