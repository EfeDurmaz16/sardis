"""Compliance check skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class ComplianceCheckSkill(OpenClawSkill):
    """Run compliance preflight on a transaction."""

    @property
    def name(self) -> str:
        return "check_compliance"

    @property
    def description(self) -> str:
        return "Run compliance preflight on a transaction"

    @property
    def parameters(self) -> list[str]:
        return ["recipient_address", "amount"]

    @property
    def required_permissions(self) -> list[str]:
        return ["compliance:read"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{context.base_url}/compliance/preflight",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "recipient_address": params["recipient_address"],
                    "amount": str(params["amount"]),
                    "agent_id": context.agent_id,
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
