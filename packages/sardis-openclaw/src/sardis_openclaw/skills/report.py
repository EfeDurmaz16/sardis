"""Spending report skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class SpendingReportSkill(OpenClawSkill):
    """Generate spending analytics report for an agent."""

    @property
    def name(self) -> str:
        return "spending_report"

    @property
    def description(self) -> str:
        return "Generate spending analytics report for an agent"

    @property
    def parameters(self) -> list[str]:
        return ["agent_id", "period_days"]

    @property
    def required_permissions(self) -> list[str]:
        return ["analytics:read"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        agent_id = params["agent_id"]
        period = params["period_days"]
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{context.base_url}/analytics/spending",
                headers={"Authorization": f"Bearer {context.api_key}"},
                params={"agent_id": agent_id, "period_days": period},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
