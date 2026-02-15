"""Lithic treasury adapter.

USD-first at launch, but request/response models remain currency-aware.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

import httpx

logger = logging.getLogger(__name__)

_DIRECTION = Literal["COLLECTION", "PAYMENT"]
_METHOD = Literal["ACH_NEXT_DAY", "ACH_SAME_DAY"]
_SEC_CODE = Literal["CCD", "PPD", "WEB"]


def _mask(s: str | None, head: int = 4, tail: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= head + tail:
        return "*" * len(s)
    return f"{s[:head]}{'*' * (len(s) - head - tail)}{s[-tail:]}"


@dataclass
class LithicFinancialAccount:
    token: str
    account_token: Optional[str]
    account_type: str
    status: str
    currency: str = "USD"
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    nickname: Optional[str] = None
    raw: dict[str, Any] | None = None


@dataclass
class LithicExternalBankAccount:
    token: str
    financial_account_token: str
    verification_method: str
    verification_state: str
    state: str
    owner: str
    owner_type: str
    account_type: str
    last_four: str
    currency: str
    country: str
    raw: dict[str, Any] | None = None


@dataclass
class LithicPayment:
    token: str
    status: str
    result: str
    direction: str
    method: str
    currency: str
    pending_amount: int
    settled_amount: int
    financial_account_token: str
    external_bank_account_token: str
    user_defined_id: Optional[str]
    method_attributes: dict[str, Any]
    events: list[dict[str, Any]]
    raw: dict[str, Any] | None = None


@dataclass
class CreateExternalBankAccountRequest:
    financial_account_token: str
    verification_method: Literal["MICRO_DEPOSIT", "PRENOTE", "EXTERNALLY_VERIFIED"]
    owner_type: Literal["INDIVIDUAL", "BUSINESS"]
    owner: str
    account_type: Literal["CHECKING", "SAVINGS"]
    routing_number: str
    account_number: str
    name: Optional[str] = None
    currency: str = "USD"
    country: str = "USA"
    account_token: Optional[str] = None
    company_id: Optional[str] = None
    user_defined_id: Optional[str] = None
    address: Optional[dict[str, Any]] = None
    dob: Optional[str] = None
    doing_business_as: Optional[str] = None


@dataclass
class CreatePaymentRequest:
    financial_account_token: str
    external_bank_account_token: str
    payment_type: _DIRECTION
    amount: int
    method: _METHOD = "ACH_NEXT_DAY"
    sec_code: _SEC_CODE = "CCD"
    memo: Optional[str] = None
    idempotency_token: Optional[str] = None
    user_defined_id: Optional[str] = None


class LithicTreasuryClient:
    """HTTP adapter for Lithic financial accounts and ACH payments APIs."""

    def __init__(
        self,
        api_key: str,
        environment: str = "sandbox",
        timeout_seconds: float = 20.0,
        webhook_secret: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Lithic API key is required")
        env = (environment or "sandbox").strip().lower()
        self._api_key = api_key
        self._env = env
        self._timeout = timeout_seconds
        self._webhook_secret = webhook_secret or ""
        self._base_url = (
            "https://sandbox.lithic.com"
            if env in {"sandbox", "test", "development", "dev"}
            else "https://api.lithic.com"
        )
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        try:
            resp = await client.request(method, path, params=params, json=json)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            raise ValueError("Unexpected Lithic API response shape")
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000]
            logger.error(
                "Lithic API error method=%s path=%s status=%s body=%s",
                method,
                path,
                exc.response.status_code,
                body,
            )
            raise

    async def list_financial_accounts(self, account_token: Optional[str] = None) -> list[LithicFinancialAccount]:
        params: dict[str, Any] = {}
        if account_token:
            params["account_token"] = account_token
        data = await self._request("GET", "/v1/financial_accounts", params=params)
        records = data.get("data", [])
        out: list[LithicFinancialAccount] = []
        for r in records:
            out.append(
                LithicFinancialAccount(
                    token=str(r.get("token", "")),
                    account_token=r.get("account_token"),
                    account_type=str(r.get("type", "")),
                    status=str(r.get("status", "")),
                    currency=str(r.get("currency", "USD")),
                    routing_number=r.get("routing_number"),
                    account_number=r.get("account_number"),
                    nickname=r.get("nickname"),
                    raw=r,
                )
            )
        return out

    async def create_external_bank_account(
        self, request: CreateExternalBankAccountRequest
    ) -> LithicExternalBankAccount:
        payload: dict[str, Any] = {
            "financial_account_token": request.financial_account_token,
            "verification_method": request.verification_method,
            "owner_type": request.owner_type,
            "owner": request.owner,
            "type": request.account_type,
            "routing_number": request.routing_number,
            "account_number": request.account_number,
            "currency": request.currency,
            "country": request.country,
        }
        if request.name:
            payload["name"] = request.name
        if request.account_token:
            payload["account_token"] = request.account_token
        if request.company_id:
            payload["company_id"] = request.company_id
        if request.user_defined_id:
            payload["user_defined_id"] = request.user_defined_id
        if request.address:
            payload["address"] = request.address
        if request.dob:
            payload["dob"] = request.dob
        if request.doing_business_as:
            payload["doing_business_as"] = request.doing_business_as

        result = await self._request("POST", "/v1/external_bank_accounts", json=payload)
        return LithicExternalBankAccount(
            token=str(result.get("token", "")),
            financial_account_token=str(result.get("financial_account_token", request.financial_account_token)),
            verification_method=str(result.get("verification_method", request.verification_method)),
            verification_state=str(result.get("verification_state", "")),
            state=str(result.get("state", "")),
            owner=str(result.get("owner", "")),
            owner_type=str(result.get("owner_type", request.owner_type)),
            account_type=str(result.get("type", request.account_type)),
            last_four=str(result.get("last_four", "")),
            currency=str(result.get("currency", request.currency)),
            country=str(result.get("country", request.country)),
            raw=result,
        )

    async def verify_micro_deposits(
        self,
        external_bank_account_token: str,
        micro_deposits: list[str],
    ) -> LithicExternalBankAccount:
        payload = {"micro_deposits": micro_deposits}
        result = await self._request(
            "POST",
            f"/v1/external_bank_accounts/{external_bank_account_token}/micro_deposits",
            json=payload,
        )
        return LithicExternalBankAccount(
            token=str(result.get("token", external_bank_account_token)),
            financial_account_token=str(result.get("financial_account_token", "")),
            verification_method=str(result.get("verification_method", "")),
            verification_state=str(result.get("verification_state", "")),
            state=str(result.get("state", "")),
            owner=str(result.get("owner", "")),
            owner_type=str(result.get("owner_type", "")),
            account_type=str(result.get("type", "")),
            last_four=str(result.get("last_four", "")),
            currency=str(result.get("currency", "USD")),
            country=str(result.get("country", "USA")),
            raw=result,
        )

    async def create_payment(self, request: CreatePaymentRequest) -> LithicPayment:
        payload: dict[str, Any] = {
            "financial_account_token": request.financial_account_token,
            "external_bank_account_token": request.external_bank_account_token,
            "type": request.payment_type,
            "amount": request.amount,
            "method": request.method,
            "method_attributes": {
                "sec_code": request.sec_code,
            },
        }
        if request.memo:
            payload["memo"] = request.memo
        if request.idempotency_token:
            payload["token"] = request.idempotency_token
        if request.user_defined_id:
            payload["user_defined_id"] = request.user_defined_id

        result = await self._request("POST", "/v1/payments", json=payload)
        return self._to_payment(result)

    async def get_payment(self, payment_token: str) -> LithicPayment:
        result = await self._request("GET", f"/v1/payments/{payment_token}")
        return self._to_payment(result)

    async def list_payments(
        self,
        *,
        financial_account_token: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[str] = None,
        page_size: int = 100,
        starting_after: Optional[str] = None,
        ending_before: Optional[str] = None,
    ) -> list[LithicPayment]:
        params: dict[str, Any] = {"page_size": max(1, min(page_size, 100))}
        if financial_account_token:
            params["financial_account_token"] = financial_account_token
        if status:
            params["status"] = status
        if result:
            params["result"] = result
        if starting_after:
            params["starting_after"] = starting_after
        if ending_before:
            params["ending_before"] = ending_before

        data = await self._request("GET", "/v1/payments", params=params)
        return [self._to_payment(item) for item in data.get("data", [])]

    async def simulate_payment_action(
        self,
        payment_token: str,
        event_type: str,
        *,
        decline_reason: Optional[str] = None,
        return_reason_code: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": event_type,
            "decline_reason": decline_reason,
            "return_reason_code": return_reason_code,
        }
        return await self._request(
            "POST",
            f"/v1/simulate/payments/{payment_token}/action",
            json=payload,
        )

    async def simulate_payment_release(self, payment_token: str) -> dict[str, Any]:
        payload = {"payment_token": payment_token}
        return await self._request("POST", "/v1/simulate/payments/release", json=payload)

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            return False
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def _to_payment(self, payload: dict[str, Any]) -> LithicPayment:
        ext = str(payload.get("external_bank_account_token", ""))
        fa = str(payload.get("financial_account_token", ""))
        logger.debug(
            "Lithic payment token=%s ext=%s fin=%s status=%s",
            payload.get("token"),
            _mask(ext),
            _mask(fa),
            payload.get("status"),
        )
        return LithicPayment(
            token=str(payload.get("token", "")),
            status=str(payload.get("status", "")),
            result=str(payload.get("result", "")),
            direction=str(payload.get("direction", "")),
            method=str(payload.get("method", "")),
            currency=str(payload.get("currency", "USD")),
            pending_amount=int(payload.get("pending_amount", 0) or 0),
            settled_amount=int(payload.get("settled_amount", 0) or 0),
            financial_account_token=fa,
            external_bank_account_token=ext,
            user_defined_id=payload.get("user_defined_id"),
            method_attributes=payload.get("method_attributes", {}) or {},
            events=payload.get("events", []) or [],
            raw=payload,
        )

