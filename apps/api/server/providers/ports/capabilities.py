"""Capability port protocols.

Each protocol is the *minimal* surface the orchestrator / execution routers
need from a class of provider.  Concrete adapters (Turnkey, Circle, Lithic,
Conduit, …) implement one or more of these; sandbox impls implement the same
protocols with simulated behavior so dev and tests run without live keys.

Design rules:

* Protocols are ``runtime_checkable`` to match the existing ``rail.py`` /
  ``funding_ports.py`` conventions and to let the registry assert shape.
* Every port exposes ``provider``, ``capability`` and ``custody_model`` so a
  caller can record custody without knowing the concrete class.
* No method *authorizes* money.  Methods named ``create_*`` / ``execute_*``
  carry out an instruction the orchestrator already authorized; they do not
  perform policy, KYA, sanctions, or mandate checks (those live in the moat).
* Money arguments are integer minor units or ``Decimal`` — never ``float``.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .types import (
    CustodyModel,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderResult,
)


@runtime_checkable
class CapabilityPort(Protocol):
    """Common metadata every capability port exposes."""

    @property
    def provider(self) -> str: ...

    @property
    def capability(self) -> ProviderCapability: ...

    @property
    def custody_model(self) -> CustodyModel: ...

    @property
    def sandbox(self) -> bool: ...


@runtime_checkable
class CustodyPort(CapabilityPort, Protocol):
    """Key custody + signing (Turnkey, Circle, Privy, Fireblocks).

    Non-custodial: the port signs/derives on behalf of a wallet the user
    controls.  It never *initiates* a transfer on its own — the orchestrator
    supplies the already-authorized payload to sign.
    """

    async def get_address(self, wallet_ref: str, *, chain: str) -> str: ...

    async def sign_payload(
        self, wallet_ref: str, *, payload: dict[str, Any]
    ) -> ProviderResult:
        """Sign an already-authorized transaction/message payload."""
        ...


@runtime_checkable
class FiatAccountPort(CapabilityPort, Protocol):
    """Bank-rail fiat accounts (Lithic, Increase, Dakota, Column).

    Partner-custodied: a regulated partner holds the USD while ACH / wire /
    RTP / FedNow settle.  Amounts are integer minor units (cents).
    """

    async def create_account(
        self, *, owner_ref: str, currency: str = "USD", metadata: dict[str, Any] | None = None
    ) -> ProviderResult: ...

    async def get_balance(self, account_ref: str) -> tuple[MinorUnits, str]:
        """Return ``(available_minor_units, currency)``."""
        ...

    async def create_payout(
        self,
        *,
        account_ref: str,
        destination_ref: str,
        amount_minor: MinorUnits,
        currency: str = "USD",
        method: str = "ACH_NEXT_DAY",
        idempotency_key: str | None = None,
        memo: str | None = None,
    ) -> NormalizedTxn:
        """Execute an already-authorized bank payout (ACH/wire/RTP/FedNow)."""
        ...

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        """Verify a provider webhook signature.  Fail-closed (return False)."""
        ...


@runtime_checkable
class OnrampPort(CapabilityPort, Protocol):
    """Fiat -> crypto onramp session creation (Onramper, Transak, Daimo,
    Conduit, Turnkey native, Stripe).

    The port creates a session/quote the user funds; it does not move the
    user's money itself.
    """

    async def create_session(
        self,
        *,
        wallet_address: str,
        chain: str,
        crypto_currency: str = "usdc",
        fiat_currency: str = "USD",
        amount_minor: MinorUnits | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult: ...

    async def get_status(self, session_ref: str) -> ProviderResult: ...


@runtime_checkable
class OfframpPort(CapabilityPort, Protocol):
    """Crypto -> fiat payout to a bank (Onramper, Transak Stream, Coinbase
    Offramp, Bridge).

    Partner-custodied: the offramp partner takes custody of crypto and
    settles fiat to the destination bank account.
    """

    async def create_payout(
        self,
        *,
        source_chain: str,
        source_token: str,
        amount_minor: MinorUnits,
        destination_bank_ref: str,
        fiat_currency: str = "USD",
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NormalizedTxn: ...

    async def get_status(self, payout_ref: str) -> ProviderResult: ...


@runtime_checkable
class SwapPort(CapabilityPort, Protocol):
    """Same-chain / cross-token swap (LI.FI, 0x, Jupiter).

    Non-custodial: returns a quote and an executable (already-authorized)
    transaction; signing/broadcast goes through the CustodyPort + chain.
    """

    async def quote(
        self,
        *,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount_minor: MinorUnits,
    ) -> ProviderResult: ...

    async def build_execution(
        self, *, quote_ref: str, taker_address: str
    ) -> ProviderResult:
        """Return the calldata/tx the custody port should sign."""
        ...


@runtime_checkable
class BridgePort(CapabilityPort, Protocol):
    """Cross-chain bridge (Squid, CCTP v2).

    Non-custodial when canonical (CCTP burn/mint); the port returns the
    already-authorized messages to sign.
    """

    async def quote(
        self,
        *,
        from_chain: str,
        to_chain: str,
        token: str,
        amount_minor: MinorUnits,
    ) -> ProviderResult: ...

    async def build_execution(
        self, *, quote_ref: str, sender_address: str, recipient_address: str
    ) -> ProviderResult: ...


@runtime_checkable
class CardPort(CapabilityPort, Protocol):
    """Virtual card issuing + controls (Crossmint, Lithic, Stripe Issuing)."""

    async def issue_card(
        self,
        *,
        owner_ref: str,
        spend_limit_minor: MinorUnits | None = None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult: ...

    async def set_state(self, card_ref: str, *, state: str) -> ProviderResult:
        """Freeze/unfreeze/close a card (``state`` is a normalized verb)."""
        ...

    async def set_limit(
        self, card_ref: str, *, spend_limit_minor: MinorUnits, currency: str = "USD"
    ) -> ProviderResult: ...


@runtime_checkable
class KycPort(CapabilityPort, Protocol):
    """KYC / KYB identity verification (Didit)."""

    async def create_session(
        self,
        *,
        subject_ref: str,
        kind: str = "kyc",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult: ...

    async def get_status(self, session_ref: str) -> ProviderResult: ...

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool: ...


@runtime_checkable
class KytPort(CapabilityPort, Protocol):
    """AML / transaction screening (Didit, OpenSanctions, Elliptic).

    Returns a screening verdict; the orchestrator (moat) decides allow/deny.
    The port never decides — it only reports.
    """

    async def screen_address(
        self, *, address: str, chain: str | None = None
    ) -> ProviderResult: ...

    async def screen_counterparty(
        self, *, name: str, metadata: dict[str, Any] | None = None
    ) -> ProviderResult: ...
