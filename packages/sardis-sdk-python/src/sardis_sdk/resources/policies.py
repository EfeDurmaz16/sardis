"""Policies resource for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from ..models.policy import (
    ParsedPolicy,
    PolicyPreviewResponse,
    ApplyPolicyFromNLResponse,
    PolicyCheckResponse,
    PolicyExample,
)
from .base import AsyncBaseResource, SyncBaseResource

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncPoliciesResource(AsyncBaseResource):
    async def parse(
        self,
        natural_language: str,
        agent_id: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ParsedPolicy:
        payload: Dict[str, Any] = {"natural_language": natural_language}
        if agent_id:
            payload["agent_id"] = agent_id
        data = await self._post("policies/parse", payload, timeout=timeout)
        return ParsedPolicy.model_validate(data)

    async def preview(
        self,
        natural_language: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> PolicyPreviewResponse:
        data = await self._post(
            "policies/preview",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": False},
            timeout=timeout,
        )
        return PolicyPreviewResponse.model_validate(data)

    async def apply(
        self,
        natural_language: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ApplyPolicyFromNLResponse:
        data = await self._post(
            "policies/apply",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": True},
            timeout=timeout,
        )
        return ApplyPolicyFromNLResponse.model_validate(data)

    async def get(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        return await self._get(f"policies/{agent_id}", timeout=timeout)

    async def check(
        self,
        *,
        agent_id: str,
        amount: Decimal,
        currency: str = "USD",
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        mcc_code: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> PolicyCheckResponse:
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
            "merchant_id": merchant_id,
            "merchant_category": merchant_category,
            "mcc_code": mcc_code,
        }
        data = await self._post("policies/check", payload, timeout=timeout)
        return PolicyCheckResponse.model_validate(data)

    async def examples(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[PolicyExample]:
        data = await self._get("policies/examples", timeout=timeout)
        if isinstance(data, list):
            return [PolicyExample.model_validate(item) for item in data]
        return [PolicyExample.model_validate(item) for item in data.get("examples", [])]


class PoliciesResource(SyncBaseResource):
    def parse(
        self,
        natural_language: str,
        agent_id: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ParsedPolicy:
        payload: Dict[str, Any] = {"natural_language": natural_language}
        if agent_id:
            payload["agent_id"] = agent_id
        data = self._post("policies/parse", payload, timeout=timeout)
        return ParsedPolicy.model_validate(data)

    def preview(
        self,
        natural_language: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> PolicyPreviewResponse:
        data = self._post(
            "policies/preview",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": False},
            timeout=timeout,
        )
        return PolicyPreviewResponse.model_validate(data)

    def apply(
        self,
        natural_language: str,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> ApplyPolicyFromNLResponse:
        data = self._post(
            "policies/apply",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": True},
            timeout=timeout,
        )
        return ApplyPolicyFromNLResponse.model_validate(data)

    def get(
        self,
        agent_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        return self._get(f"policies/{agent_id}", timeout=timeout)

    def check(
        self,
        *,
        agent_id: str,
        amount: Decimal,
        currency: str = "USD",
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        mcc_code: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> PolicyCheckResponse:
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "amount": str(amount),
            "currency": currency,
            "merchant_id": merchant_id,
            "merchant_category": merchant_category,
            "mcc_code": mcc_code,
        }
        data = self._post("policies/check", payload, timeout=timeout)
        return PolicyCheckResponse.model_validate(data)

    def examples(
        self,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[PolicyExample]:
        data = self._get("policies/examples", timeout=timeout)
        if isinstance(data, list):
            return [PolicyExample.model_validate(item) for item in data]
        return [PolicyExample.model_validate(item) for item in data.get("examples", [])]

