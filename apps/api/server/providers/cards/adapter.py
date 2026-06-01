""":class:`CardPort` adapters over the card-issuing clients.

Three adapters, one per provider:

* :class:`CrossmintCardAdapter` — Crossmint Agentic Cards (Rain-backed); the
  PRIMARY.  Non-custodial dual-key, agent-bound single-use virtual credentials;
  avoids a mandatory Stripe/Lithic relationship.
* :class:`LithicCardAdapter`    — Lithic, Sardis's own BIN; FALLBACK.
* :class:`StripeIssuingCardAdapter` — Stripe Issuing; FALLBACK.

Every adapter is **partner-custodied**: a regulated issuer holds the card
program / settlement relationship while Sardis stays non-custodial.  None of
them authorizes a transaction — each only issues a card / changes a card's state
/ sets a control that the orchestrator already authorized, then normalizes the
vendor response into the unified :class:`ProviderResult`.

A real PAN is NEVER surfaced: results carry only tokenized refs (card id, last
four, expiry, limit).  Money crosses the boundary as integer minor units (USD
cents); no float touches a money path.

``set_state`` accepts the normalized verbs ``active`` / ``freeze`` / ``frozen``
/ ``unfreeze`` / ``close`` / ``closed`` and maps them to each vendor's enum;
unknown verbs fail closed rather than guessing a state on a card.
"""

from __future__ import annotations

from typing import Any

from ..ports.types import (
    CustodyModel,
    MinorUnits,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)
from .client import (
    CrossmintCardClient,
    IssuedCard,
    LithicCardClient,
    StripeIssuingClient,
)

#: Normalize the caller's state verb to one of {active, frozen, closed}.  The
#: port contract says ``state`` is a normalized verb; we accept the common
#: synonyms and fail closed on anything else (never default to a state on a
#: card on a money path).
_STATE_VERBS = {
    "active": "active",
    "open": "active",
    "unfreeze": "active",
    "unpause": "active",
    "freeze": "frozen",
    "frozen": "frozen",
    "pause": "frozen",
    "paused": "frozen",
    "inactive": "frozen",
    "close": "closed",
    "closed": "closed",
    "cancel": "closed",
    "canceled": "closed",
    "revoke": "closed",
}


def _normalize_state_verb(state: str, *, provider: str) -> str:
    verb = _STATE_VERBS.get(state.strip().lower())
    if verb is None:
        raise ProviderError(
            f"unknown card state verb {state!r}; expected active/freeze/unfreeze/close",
            provider=provider,
            capability=ProviderCapability.CARD,
        )
    return verb


def _require_int_minor(amount_minor: MinorUnits, *, provider: str) -> int:
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool):
        raise ProviderError(
            "spend_limit_minor must be integer minor units (cents)",
            provider=provider,
            capability=ProviderCapability.CARD,
        )
    if amount_minor < 0:
        raise ProviderError(
            "spend_limit_minor must be non-negative",
            provider=provider,
            capability=ProviderCapability.CARD,
        )
    return amount_minor


class _CardAdapterBase:
    """Shared metadata + result normalization for the card adapters.

    All card issuers are partner-custodied: the issuer owns the card program /
    settlement; Sardis remains non-custodial.
    """

    capability = ProviderCapability.CARD

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    def _card_result(self, card: IssuedCard, *, ok: bool = True) -> ProviderResult:
        # TOKENIZED ONLY — never include a PAN.  ``raw`` is the vendor payload;
        # the vendor card-issue endpoints used here do not return a PAN (PAN
        # lives behind a separate PCI/elements surface), so this is safe.
        return ProviderResult(
            provider=self.provider,  # type: ignore[attr-defined]
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,  # type: ignore[attr-defined]
            ok=ok,
            reference=card.card_id or None,
            status=card.status,
            raw={
                "card_id": card.card_id,
                "status": card.status,
                "last_four": card.last_four,
                "expiration_month": card.expiration_month,
                "expiration_year": card.expiration_year,
                "spend_limit_minor": card.spend_limit_minor,
                "currency": card.currency,
            },
        )


class CrossmintCardAdapter(_CardAdapterBase):
    """:class:`CardPort` over Crossmint Agentic Cards (Rain-backed). PRIMARY."""

    def __init__(self, client: CrossmintCardClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "crossmint"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def issue_card(
        self,
        *,
        owner_ref: str,
        spend_limit_minor: MinorUnits | None = None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        limit = (
            _require_int_minor(spend_limit_minor, provider=self.provider)
            if spend_limit_minor is not None
            else None
        )
        display_name = (metadata or {}).get("display_name") or f"agent:{owner_ref}"
        frequency = (metadata or {}).get("frequency", "allTime")
        try:
            card = await self._client.issue_card(
                user_ref=owner_ref,
                display_name=str(display_name),
                spend_limit_minor=limit,
                frequency=str(frequency),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"crossmint_issue_card_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_state(self, card_ref: str, *, state: str) -> ProviderResult:
        verb = _normalize_state_verb(state, provider=self.provider)
        try:
            card = await self._client.update_card(card_id=card_ref, status=verb)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"crossmint_set_state_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_limit(
        self, card_ref: str, *, spend_limit_minor: MinorUnits, currency: str = "USD"
    ) -> ProviderResult:
        limit = _require_int_minor(spend_limit_minor, provider=self.provider)
        try:
            card = await self._client.update_card(card_id=card_ref, spend_limit_minor=limit)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"crossmint_set_limit_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)


class LithicCardAdapter(_CardAdapterBase):
    """:class:`CardPort` over Lithic (own BIN). FALLBACK."""

    def __init__(self, client: LithicCardClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "lithic"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def issue_card(
        self,
        *,
        owner_ref: str,
        spend_limit_minor: MinorUnits | None = None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        limit = (
            _require_int_minor(spend_limit_minor, provider=self.provider)
            if spend_limit_minor is not None
            else None
        )
        duration = (metadata or {}).get("spend_limit_duration", "MONTHLY")
        memo = (metadata or {}).get("memo") or f"agent:{owner_ref}"
        try:
            card = await self._client.issue_card(
                memo=str(memo),
                spend_limit_minor=limit,
                spend_limit_duration=str(duration),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lithic_issue_card_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_state(self, card_ref: str, *, state: str) -> ProviderResult:
        verb = _normalize_state_verb(state, provider=self.provider)
        try:
            card = await self._client.set_state(card_id=card_ref, state_verb=verb)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lithic_set_state_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_limit(
        self, card_ref: str, *, spend_limit_minor: MinorUnits, currency: str = "USD"
    ) -> ProviderResult:
        limit = _require_int_minor(spend_limit_minor, provider=self.provider)
        try:
            card = await self._client.set_limit(card_id=card_ref, spend_limit_minor=limit)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"lithic_set_limit_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)


class StripeIssuingCardAdapter(_CardAdapterBase):
    """:class:`CardPort` over Stripe Issuing. FALLBACK."""

    def __init__(self, client: StripeIssuingClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "stripe_issuing"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    async def issue_card(
        self,
        *,
        owner_ref: str,
        spend_limit_minor: MinorUnits | None = None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        limit = (
            _require_int_minor(spend_limit_minor, provider=self.provider)
            if spend_limit_minor is not None
            else None
        )
        interval = (metadata or {}).get("interval", "monthly")
        # Stripe requires a cardholder id; owner_ref IS the cardholder
        # (provisioned out-of-band — an adapter mints no identity).
        try:
            card = await self._client.issue_card(
                cardholder=owner_ref,
                spend_limit_minor=limit,
                currency=currency,
                interval=str(interval),
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"stripe_issue_card_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_state(self, card_ref: str, *, state: str) -> ProviderResult:
        verb = _normalize_state_verb(state, provider=self.provider)
        try:
            card = await self._client.set_status(card_id=card_ref, state_verb=verb)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"stripe_set_state_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)

    async def set_limit(
        self, card_ref: str, *, spend_limit_minor: MinorUnits, currency: str = "USD"
    ) -> ProviderResult:
        limit = _require_int_minor(spend_limit_minor, provider=self.provider)
        try:
            card = await self._client.set_limit(card_id=card_ref, spend_limit_minor=limit)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"stripe_set_limit_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return self._card_result(card)
