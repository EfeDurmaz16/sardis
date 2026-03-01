"""Bridge transfer skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class BridgeTransferSkill(OpenClawSkill):
    """Bridge stablecoins between supported chains via CCTP."""

    @property
    def name(self) -> str:
        return "bridge_transfer"

    @property
    def description(self) -> str:
        return "Bridge stablecoins between supported chains via CCTP"

    @property
    def parameters(self) -> list[str]:
        return ["source_chain", "dest_chain", "amount", "token"]

    @property
    def required_permissions(self) -> list[str]:
        return ["wallet:write", "bridge:execute"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{context.base_url}/bridge/transfer",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "wallet_id": context.wallet_id,
                    "agent_id": context.agent_id,
                    "source_chain": params["source_chain"],
                    "dest_chain": params["dest_chain"],
                    "amount": str(params["amount"]),
                    "token": params["token"],
                },
                timeout=60.0,
            )
            if resp.status_code != 200:
                return SkillResult(success=False, error=f"API error: {resp.status_code}")
            return SkillResult(success=True, data=resp.json())
