"""Policies resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..models.policy import (
    ApplyPolicyFromNLResponse,
    ParsedPolicy,
    PolicyCheckResponse,
    PolicyExample,
    PolicyPreviewResponse,
)
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncPoliciesResource(AsyncBaseResource):
    async def parse(
        self,
        natural_language: str,
        agent_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> ParsedPolicy:
        payload: dict[str, Any] = {"natural_language": natural_language}
        if agent_id:
            payload["agent_id"] = agent_id
        data = await self._post("policies/parse", payload, timeout=timeout)
        return ParsedPolicy.model_validate(data)

    async def preview(
        self,
        natural_language: str,
        agent_id: str,
        timeout: float | TimeoutConfig | None = None,
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
        timeout: float | TimeoutConfig | None = None,
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
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        return await self._get(f"policies/{agent_id}", timeout=timeout)

    async def check(
        self,
        *,
        agent_id: str,
        amount: Decimal,
        currency: str = "USD",
        merchant_id: str | None = None,
        merchant_category: str | None = None,
        mcc_code: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> PolicyCheckResponse:
        payload: dict[str, Any] = {
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
        timeout: float | TimeoutConfig | None = None,
    ) -> list[PolicyExample]:
        data = await self._get("policies/examples", timeout=timeout)
        if isinstance(data, list):
            return [PolicyExample.model_validate(item) for item in data]
        return [PolicyExample.model_validate(item) for item in data.get("examples", [])]

    async def create_from_nl(
        self,
        agent_id: str,
        natural_language: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> ApplyPolicyFromNLResponse:
        """Create and immediately apply a policy from natural language."""
        data = await self._post(
            "policies/apply",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": True},
            timeout=timeout,
        )
        return ApplyPolicyFromNLResponse.model_validate(data)

    async def get_recommendations(
        self,
        agent_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get policy recommendations for an agent based on its transaction history."""
        return await self._get(f"policies/{agent_id}/recommendations", timeout=timeout)


class PoliciesResource(SyncBaseResource):
    def parse(
        self,
        natural_language: str,
        agent_id: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> ParsedPolicy:
        payload: dict[str, Any] = {"natural_language": natural_language}
        if agent_id:
            payload["agent_id"] = agent_id
        data = self._post("policies/parse", payload, timeout=timeout)
        return ParsedPolicy.model_validate(data)

    def preview(
        self,
        natural_language: str,
        agent_id: str,
        timeout: float | TimeoutConfig | None = None,
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
        timeout: float | TimeoutConfig | None = None,
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
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        return self._get(f"policies/{agent_id}", timeout=timeout)

    def check(
        self,
        *,
        agent_id: str,
        amount: Decimal,
        currency: str = "USD",
        merchant_id: str | None = None,
        merchant_category: str | None = None,
        mcc_code: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> PolicyCheckResponse:
        payload: dict[str, Any] = {
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
        timeout: float | TimeoutConfig | None = None,
    ) -> list[PolicyExample]:
        data = self._get("policies/examples", timeout=timeout)
        if isinstance(data, list):
            return [PolicyExample.model_validate(item) for item in data]
        return [PolicyExample.model_validate(item) for item in data.get("examples", [])]

    def create_from_nl(
        self,
        agent_id: str,
        natural_language: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> ApplyPolicyFromNLResponse:
        """Create and immediately apply a policy from natural language."""
        data = self._post(
            "policies/apply",
            {"natural_language": natural_language, "agent_id": agent_id, "confirm": True},
            timeout=timeout,
        )
        return ApplyPolicyFromNLResponse.model_validate(data)

    def get_recommendations(
        self,
        agent_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get policy recommendations for an agent based on its transaction history."""
        return self._get(f"policies/{agent_id}/recommendations", timeout=timeout)

