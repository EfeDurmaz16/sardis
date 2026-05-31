""":class:`KycPort` and :class:`KytPort` adapters over the compliance clients.

Two providers:

* :class:`DiditKycAdapter`  — Didit identity verification (KYC + KYB w/ UBOs)
  behind :class:`KycPort`; session create + decision status + HMAC webhook
  verification.
* :class:`DiditKytAdapter`  — Didit AML screening behind :class:`KytPort`;
  named-counterparty screening via ``/v3/aml/``.
* :class:`OpenSanctionsKytAdapter` — OpenSanctions sanctions/PEP/watchlist
  screening behind :class:`KytPort`; on-chain *address* + counterparty.

None of these adapters authorizes/initiates/settles money.  A KYC adapter only
*creates an identity session* and *reports its status*; a KYT adapter only
*reports a screening verdict*.  The orchestrator (the moat) decides allow/deny —
the port never decides.  On a screening transport/auth failure the adapter
raises :class:`ProviderError`, which the orchestrator turns into a fail-CLOSED
deny (the brief's "fail-CLOSED on screening failure").

Custody model: ``PARTNER_CUSTODIED`` — a regulated verification partner performs
the verification/screening of record.  No funds are ever held on these paths;
Sardis stays non-custodial.
"""

from __future__ import annotations

from typing import Any

from ..ports.types import (
    CustodyModel,
    ProviderCapability,
    ProviderError,
    ProviderResult,
)
from .client import DiditClient, OpenSanctionsClient, ScreeningResult


def _screening_result(
    *,
    provider: str,
    sandbox: bool,
    result: ScreeningResult,
) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        capability=ProviderCapability.KYT,
        custody_model=CustodyModel.PARTNER_CUSTODIED,
        sandbox=sandbox,
        ok=True,
        reference=result.reference,
        status=result.status,
        raw={
            "status": result.status,
            "total_hits": result.total_hits,
            "hits": [
                {
                    "id": h.hit_id,
                    "caption": h.caption,
                    "score": h.score,
                    "match": h.match,
                    "datasets": h.datasets,
                    "topics": h.topics,
                }
                for h in result.hits
            ],
        },
    )


# =========================================================================
# Didit — KycPort (KYC + KYB)
# =========================================================================


class DiditKycAdapter:
    """:class:`KycPort` over Didit identity verification (KYC + KYB)."""

    capability = ProviderCapability.KYC

    def __init__(self, client: DiditClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "didit"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    async def create_session(
        self,
        *,
        subject_ref: str,
        kind: str = "kyc",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        try:
            session = await self._client.create_session(
                subject_ref=subject_ref, kind=kind, metadata=metadata
            )
        except ValueError as exc:
            # Misconfiguration (e.g. missing workflow id) — fail closed, not retryable.
            raise ProviderError(
                f"didit_create_session_misconfigured: {exc}",
                provider=self.provider,
                capability=self.capability,
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"didit_create_session_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=session.session_id or None,
            status=session.status,
            raw={
                "session_id": session.session_id,
                "status": session.status,
                "kind": session.kind,
                "verification_url": session.verification_url,
                "session_token": session.session_token,
            },
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        try:
            session = await self._client.get_decision(session_ref)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise ProviderError(
                f"didit_get_status_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return ProviderResult(
            provider=self.provider,
            capability=self.capability,
            custody_model=self.custody_model,
            sandbox=self.sandbox,
            reference=session.session_id or None,
            status=session.status,
            raw={
                "session_id": session.session_id,
                "status": session.status,
                "kind": session.kind,
            },
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        # Fail-closed verification lives in the client.
        return self._client.verify_webhook(body=body, headers=headers)


# =========================================================================
# Didit — KytPort (AML screening of a named counterparty)
# =========================================================================


class DiditKytAdapter:
    """:class:`KytPort` over Didit AML screening (``/v3/aml/``).

    Didit's documented ``/v3/`` surface has no native on-chain *address*
    primitive, so :meth:`screen_address` screens the address *as a name* (a
    sanctioned wallet is frequently listed by its address string); raw-address
    coverage is better served by OpenSanctions, which the registry prefers for
    KYT when its key is set.  Counterparty screening uses the AML endpoint
    directly.
    """

    capability = ProviderCapability.KYT

    def __init__(self, client: DiditClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "didit"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    async def screen_address(self, *, address: str, chain: str | None = None) -> ProviderResult:
        return await self._screen(name=address, entity_type="person", chain=chain)

    async def screen_counterparty(
        self, *, name: str, metadata: dict[str, Any] | None = None
    ) -> ProviderResult:
        entity_type = (metadata or {}).get("entity_type", "person")
        return await self._screen(name=name, entity_type=str(entity_type))

    async def _screen(
        self, *, name: str, entity_type: str, chain: str | None = None
    ) -> ProviderResult:
        try:
            result = await self._client.screen_aml(name=name, entity_type=entity_type)
        except Exception as exc:  # noqa: BLE001 - normalized; fail-closed at moat
            raise ProviderError(
                f"didit_aml_screen_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return _screening_result(provider=self.provider, sandbox=self.sandbox, result=result)


# =========================================================================
# OpenSanctions — KytPort (sanctions / PEP / watchlist)
# =========================================================================


class OpenSanctionsKytAdapter:
    """:class:`KytPort` over OpenSanctions ``POST /match/{scope}``."""

    capability = ProviderCapability.KYT

    def __init__(self, client: OpenSanctionsClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "opensanctions"

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.PARTNER_CUSTODIED

    async def screen_address(self, *, address: str, chain: str | None = None) -> ProviderResult:
        # FollowTheMoney has a CryptoWallet schema; screen the address both as a
        # wallet property and (fallback) as the entity name so a sanctioned
        # wallet listed by address is surfaced.
        properties: dict[str, list[str]] = {
            "publicKey": [address],
            "name": [address],
        }
        try:
            result = await self._client.match(
                properties=properties, schema="CryptoWallet", query_id="addr"
            )
        except Exception as exc:  # noqa: BLE001 - normalized; fail-closed at moat
            raise ProviderError(
                f"opensanctions_screen_address_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return _screening_result(provider=self.provider, sandbox=self.sandbox, result=result)

    async def screen_counterparty(
        self, *, name: str, metadata: dict[str, Any] | None = None
    ) -> ProviderResult:
        schema = (metadata or {}).get("schema", "Person")
        properties: dict[str, list[str]] = {"name": [name]}
        # Allow extra FollowTheMoney properties (birthDate, nationality, country)
        # from metadata without leaking anything the caller did not supply.
        for key in ("birthDate", "nationality", "country", "registrationNumber"):
            val = (metadata or {}).get(key)
            if val:
                properties[key] = [str(val)] if isinstance(val, str) else list(val)
        try:
            result = await self._client.match(
                properties=properties, schema=str(schema), query_id="cp"
            )
        except Exception as exc:  # noqa: BLE001 - normalized; fail-closed at moat
            raise ProviderError(
                f"opensanctions_screen_counterparty_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc
        return _screening_result(provider=self.provider, sandbox=self.sandbox, result=result)
