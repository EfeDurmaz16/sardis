"""Send payment skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class SendPaymentSkill(OpenClawSkill):
    """Send a stablecoin payment via mandate."""

    @property
    def name(self) -> str:
        return "send_payment"

    @property
    def description(self) -> str:
        return "Send a stablecoin payment via mandate"

    @property
    def parameters(self) -> list[str]:
        return ["recipient", "amount", "currency", "chain"]

    @property
    def required_permissions(self) -> list[str]:
        return ["wallet:write", "mandate:create"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{context.base_url}/payments/send",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "wallet_id": context.wallet_id,
                    "agent_id": context.agent_id,
                    "recipient": params["recipient"],
                    "amount": str(params["amount"]),
                    "currency": params["currency"],
                    "chain": params["chain"],
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
