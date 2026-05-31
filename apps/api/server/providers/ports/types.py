"""Shared types for the unified provider port layer.

Every external money/identity provider in Sardis is reached through a typed
*capability port* (see :mod:`server.providers.ports`).  The orchestrator and
execution routers talk only to these ports — never to a vendor SDK directly —
so that the authority core (the "moat" from #396) is never bypassed.

Hard invariants enforced here:

* **No adapter authorizes money.** A port only *normalizes* and *executes*
  what the orchestrator has already authorized.  Each adapter therefore
  declares an explicit :class:`CustodyModel` so the caller (and audit trail)
  knows who holds funds at every hop.
* **Money is exact.**  Amounts cross port boundaries as integer
  :data:`MinorUnits` (smallest currency unit, e.g. cents / USDC base units)
  or :class:`decimal.Decimal` — never ``float``.
* **Sandbox is explicit.**  Every :class:`ProviderResult` carries a
  ``sandbox`` flag so a simulated/sandbox response can never be mistaken for a
  settled production movement of funds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

# Integer amount in the smallest unit of ``currency`` (cents for USD,
# 6-decimal base units for USDC, etc.).  Money never crosses a port boundary
# as ``float``.
MinorUnits = int


class CustodyModel(str, Enum):
    """Who holds the funds while a provider executes an instruction.

    This is a *property of the adapter*, surfaced on every result so the
    authority core and audit trail can reason about custody at each hop.
    """

    #: Sardis / the agent never relinquishes key control; the provider only
    #: signs or routes a movement the user already authorized (e.g. Turnkey
    #: MPC signing, on-chain stablecoin transfer).
    NON_CUSTODIAL = "non_custodial"

    #: A regulated partner takes temporary custody to bridge a rail Sardis
    #: cannot touch directly (e.g. Lithic ACH, Circle CPN payout, a fiat
    #: bank account, a card issuer).  Sardis remains non-custodial; the
    #: *partner* is the custodian of record for that leg.
    PARTNER_CUSTODIED = "partner_custodied"

    #: No real funds move.  Sandbox / mock adapter used in dev and tests.
    SIMULATED = "simulated"


class ProviderCapability(str, Enum):
    """Capability ports the registry can resolve an implementation for."""

    CUSTODY = "custody"
    FIAT_ACCOUNT = "fiat_account"
    ONRAMP = "onramp"
    OFFRAMP = "offramp"
    SWAP = "swap"
    BRIDGE = "bridge"
    CARD = "card"
    KYC = "kyc"
    KYT = "kyt"


@dataclass(frozen=True)
class ProviderResult:
    """Envelope returned by every port call.

    ``ok`` lets callers branch without exception handling on the happy path;
    adapters still raise :class:`ProviderError` for transport/auth failures so
    the orchestrator's fail-closed logic engages.
    """

    provider: str
    capability: ProviderCapability
    custody_model: CustodyModel
    sandbox: bool
    ok: bool = True
    #: Provider-side identifier for the created/looked-up resource.
    reference: str | None = None
    #: Lifecycle status as normalized by the adapter (e.g. ``"pending"``,
    #: ``"settled"``, ``"failed"``).  Not the raw vendor enum.
    status: str | None = None
    #: Untouched vendor payload, for debugging and audit replay.
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class NormalizedTxn:
    """A money movement normalized across providers.

    Amounts are integer :data:`MinorUnits` of ``currency``.  ``custody_model``
    records who held funds for *this* movement so a settled ledger entry can
    always answer "who was the custodian?".
    """

    provider: str
    capability: ProviderCapability
    custody_model: CustodyModel
    reference: str
    status: str
    amount_minor: MinorUnits
    currency: str
    sandbox: bool
    #: Optional destination/source descriptors (chain address, bank token,
    #: counterparty id) — opaque strings the orchestrator already authorized.
    source: str | None = None
    destination: str | None = None
    chain: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ProviderError(RuntimeError):
    """Raised by adapters for transport, auth, or response-shape failures.

    Carries the capability and provider so the orchestrator can fail closed
    with an actionable, non-leaky error.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        capability: ProviderCapability,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.capability = capability
        self.retryable = retryable


class ProviderNotConfigured(ProviderError):
    """Raised when a real provider is required but no credentials are set.

    In non-production this is what triggers the registry's sandbox fallback;
    in production the registry fails closed before any port is handed out.
    """


def to_minor_units(amount: Decimal | str | int, decimals: int) -> MinorUnits:
    """Convert a decimal/string amount to integer minor units, exactly.

    Never uses ``float``.  ``Decimal`` arithmetic keeps the conversion exact;
    a fractional remainder (more precision than the currency supports) is a
    programmer error and raises rather than silently truncating money.
    """
    if isinstance(amount, float):  # pragma: no cover - defensive
        raise TypeError("float amounts are forbidden on money paths; use Decimal/str")
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    scaled = dec * (Decimal(10) ** decimals)
    if scaled != scaled.to_integral_value():
        raise ValueError(
            f"amount {amount!r} has more precision than {decimals} decimals allow"
        )
    return int(scaled)


def from_minor_units(amount_minor: MinorUnits, decimals: int) -> Decimal:
    """Convert integer minor units back to a :class:`~decimal.Decimal`."""
    return Decimal(amount_minor) / (Decimal(10) ** decimals)
