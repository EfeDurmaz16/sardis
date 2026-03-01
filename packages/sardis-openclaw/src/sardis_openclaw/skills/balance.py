"""Balance check skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class BalanceCheckSkill(OpenClawSkill):
    """Check wallet balance across supported chains."""

    @property
    def name(self) -> str:
        return "balance_check"

    @property
    def description(self) -> str:
        return "Check wallet balance across supported chains"

    @property
    def parameters(self) -> list[str]:
        return ["wallet_id"]

    @property
    def required_permissions(self) -> list[str]:
        return ["wallet:read"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        wallet_id = params["wallet_id"]
        chain = params.get("chain")
        url = f"{context.base_url}/wallets/{wallet_id}/balance"
        if chain:
            url += f"?chain={chain}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {context.api_key}"},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
