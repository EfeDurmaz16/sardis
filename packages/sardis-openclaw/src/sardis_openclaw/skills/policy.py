"""Policy update skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class PolicyUpdateSkill(OpenClawSkill):
    """Update spending policy for an agent wallet."""

    @property
    def name(self) -> str:
        return "policy_update"

    @property
    def description(self) -> str:
        return "Update spending policy for an agent wallet"

    @property
    def parameters(self) -> list[str]:
        return ["agent_id", "policy_rules"]

    @property
    def required_permissions(self) -> list[str]:
        return ["policy:write"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        agent_id = params["agent_id"]
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{context.base_url}/policies/{agent_id}",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "agent_id": agent_id,
                    "policy_rules": params["policy_rules"],
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
