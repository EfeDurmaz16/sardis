"""Create wallet skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class CreateWalletSkill(OpenClawSkill):
    """Create a non-custodial MPC wallet for an AI agent."""

    @property
    def name(self) -> str:
        return "create_wallet"

    @property
    def description(self) -> str:
        return "Create a non-custodial MPC wallet for an AI agent"

    @property
    def parameters(self) -> list[str]:
        return ["agent_id"]

    @property
    def required_permissions(self) -> list[str]:
        return ["wallet:create"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        agent_id = params["agent_id"]
        provider = params.get("provider", "turnkey")
        chain = params.get("chain", "base")
        label = params.get("label", f"Agent wallet ({agent_id})")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{context.base_url}/wallets",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "agent_id": agent_id,
                    "provider": provider,
                    "chain": chain,
                    "wallet_name": label,
                },
                timeout=30.0,
            )
            if resp.status_code not in (200, 201):
                return SkillResult(success=False, error=f"API error: {resp.status_code} {resp.text}")
            return SkillResult(success=True, data=resp.json())
