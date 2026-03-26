"""Send payment skill."""
from __future__ import annotations

from typing import Any

import httpx

from sardis_openclaw.base import OpenClawSkill, SkillContext, SkillResult


class SendPaymentSkill(OpenClawSkill):
    """Send a stablecoin payment with policy enforcement."""

    @property
    def name(self) -> str:
        return "send_payment"

    @property
    def description(self) -> str:
        return "Send a stablecoin payment with automatic policy enforcement"

    @property
    def parameters(self) -> list[str]:
        return ["recipient", "amount"]

    @property
    def required_permissions(self) -> list[str]:
        return ["wallet:write", "mandate:create"]

    async def execute(self, params: dict[str, Any], context: SkillContext) -> SkillResult:
        err = self.validate_params(params)
        if err:
            return SkillResult(success=False, error=err)

        currency = params.get("currency", "USDC")
        chain = params.get("chain", "base")

        # Step 1: Policy dry-run check before execution
        async with httpx.AsyncClient() as client:
            check_resp = await client.post(
                f"{context.base_url}/policies/check",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "agent_id": context.agent_id,
                    "amount": str(params["amount"]),
                    "recipient": params["recipient"],
                    "token": currency,
                    "chain": chain,
                },
                timeout=15.0,
            )
            if check_resp.status_code == 200:
                check_data = check_resp.json()
                if not check_data.get("allowed", True):
                    return SkillResult(
                        success=False,
                        data=check_data,
                        error=f"Policy violation: {check_data.get('reason', 'blocked by spending policy')}",
                    )

            # Step 2: Execute transfer
            resp = await client.post(
                f"{context.base_url}/wallets/{context.wallet_id}/transfer",
                headers={"Authorization": f"Bearer {context.api_key}"},
                json={
                    "to": params["recipient"],
                    "amount": str(params["amount"]),
                    "token": currency,
                    "chain": chain,
                    "agent_id": context.agent_id,
                },
                timeout=30.0,
            )
            if resp.status_code not in (200, 201):
                return SkillResult(success=False, error=f"API error: {resp.status_code} {resp.text}")
            return SkillResult(success=True, data=resp.json())
