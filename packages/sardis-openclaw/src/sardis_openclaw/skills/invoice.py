"""Create invoice skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class CreateInvoiceSkill(OpenClawSkill):
    """Create a payment invoice for incoming funds."""

    @property
    def name(self) -> str:
        return "create_invoice"

    @property
    def description(self) -> str:
        return "Create a payment invoice for incoming funds"

    @property
    def parameters(self) -> list[str]:
        return ["amount", "currency", "description"]

    @property
    def required_permissions(self) -> list[str]:
        return ["invoice:create"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{context.base_url}/invoices",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "wallet_id": context.wallet_id,
                    "agent_id": context.agent_id,
                    "amount": str(params["amount"]),
                    "currency": params["currency"],
                    "description": params["description"],
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
