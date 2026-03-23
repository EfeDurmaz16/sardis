"""Sardis action provider for Coinbase AgentKit.

Enables any AgentKit-powered agent to make policy-enforced payments via Sardis.

Actions:
    - sardis_create_agent: Create AI agent with MPC wallet
    - sardis_set_policy: Set natural language spending policy
    - sardis_send_payment: Execute policy-enforced payment
    - sardis_check_balance: Check wallet balance

Usage:
    from sardis_agentkit import sardis_action_provider
    from coinbase_agentkit import AgentKit, AgentKitConfig

    agentkit = AgentKit(AgentKitConfig(
        action_providers=[sardis_action_provider(api_key="sk_test_...")]
    ))
"""
from __future__ import annotations

import os
from typing import Any

import httpx

try:
    from coinbase_agentkit import ActionProvider, WalletProvider, create_action
    from coinbase_agentkit.network import Network

    _HAS_AGENTKIT = True
except ImportError:
    _HAS_AGENTKIT = False

    # Stubs for when agentkit is not installed
    class ActionProvider:  # type: ignore[no-redef]
        def __init__(self, name: str, sub_providers: list) -> None:
            pass

    class WalletProvider:  # type: ignore[no-redef]
        pass

    class Network:  # type: ignore[no-redef]
        pass

    def create_action(**kwargs: Any):  # type: ignore[no-redef]
        def decorator(func: Any) -> Any:
            return func
        return decorator

from .schemas import CheckBalanceSchema, CreateAgentSchema, SendPaymentSchema, SetPolicySchema


class SardisActionProvider(ActionProvider):
    """AgentKit action provider for Sardis policy-enforced payments.

    All actions are network-agnostic — Sardis handles chain routing internally
    based on the agent's API key (sk_test_ → testnet, sk_live_ → mainnet).
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = "https://api.sardis.sh",
    ) -> None:
        self._api_key = api_key or os.getenv("SARDIS_API_KEY", "")
        self._api_url = api_url.rstrip("/")
        self._client: httpx.Client | None = None
        super().__init__("sardis", [])

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._api_url,
                headers={"X-API-Key": self._api_key, "Content-Type": "application/json"},
                timeout=30,
            )
        return self._client

    @create_action(
        name="create_agent",
        description=(
            "Create a new AI agent with a non-custodial MPC wallet on Sardis. "
            "Returns agent_id and wallet_id. Use before setting policies or sending payments."
        ),
        schema=CreateAgentSchema,
    )
    def create_agent(self, args: dict[str, Any]) -> str:
        try:
            v = CreateAgentSchema(**args)
            resp = self._get_client().post(
                "/api/v2/agents",
                json={"name": v.name, "description": v.description},
            )
            resp.raise_for_status()
            data = resp.json()
            return (
                f"Created agent '{v.name}' — "
                f"agent_id={data.get('agent_id')}, wallet_id={data.get('wallet_id')}"
            )
        except Exception as e:
            return f"Error creating agent: {e}"

    @create_action(
        name="set_policy",
        description=(
            "Set a spending policy for a Sardis agent using natural language. "
            "Examples: 'Max $500/day', 'Only AWS and GitHub', 'No single transaction over $200'. "
            "Sardis enforces the policy automatically on every payment."
        ),
        schema=SetPolicySchema,
    )
    def set_policy(self, args: dict[str, Any]) -> str:
        try:
            v = SetPolicySchema(**args)
            resp = self._get_client().post(
                "/api/v2/policies",
                json={"agent_id": v.agent_id, "policy_text": v.policy_text},
            )
            resp.raise_for_status()
            data = resp.json()
            return f"Policy set for agent {v.agent_id}: {v.policy_text} (policy_id={data.get('policy_id')})"
        except Exception as e:
            return f"Error setting policy: {e}"

    @create_action(
        name="send_payment",
        description=(
            "Execute a policy-enforced payment from a Sardis agent wallet. "
            "The payment is checked against the agent's spending policy before execution. "
            "If the policy rejects it, the payment will not go through and you'll see why."
        ),
        schema=SendPaymentSchema,
    )
    def send_payment(self, args: dict[str, Any]) -> str:
        try:
            v = SendPaymentSchema(**args)
            resp = self._get_client().post(
                "/api/v2/payments",
                json={
                    "agent_id": v.agent_id,
                    "amount": v.amount,
                    "currency": v.currency,
                    "recipient": v.recipient,
                    "memo": v.memo,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return (
                f"Payment of {v.amount} {v.currency} to {v.recipient} — "
                f"tx_hash={data.get('tx_hash', 'pending')}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                detail = e.response.json().get("detail", "Policy violation")
                return f"Payment BLOCKED by policy: {detail}"
            return f"Payment failed ({e.response.status_code}): {e.response.text[:200]}"
        except Exception as e:
            return f"Error sending payment: {e}"

    @create_action(
        name="check_balance",
        description="Check the wallet balance for a Sardis agent across all supported tokens.",
        schema=CheckBalanceSchema,
    )
    def check_balance(self, args: dict[str, Any]) -> str:
        try:
            v = CheckBalanceSchema(**args)
            resp = self._get_client().get(f"/api/v2/wallets/{v.wallet_id}/balance")
            resp.raise_for_status()
            data = resp.json()
            balances = data.get("balances", {})
            if not balances:
                return f"Wallet {v.wallet_id} has no token balances."
            lines = [f"  {token}: {amt}" for token, amt in balances.items()]
            return f"Wallet {v.wallet_id} balances:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error checking balance: {e}"

    def supports_network(self, network: "Network") -> bool:
        """Sardis is network-agnostic — policy layer sits above chain execution."""
        return True


def sardis_action_provider(
    api_key: str | None = None,
    api_url: str = "https://api.sardis.sh",
) -> SardisActionProvider:
    """Factory function to create a Sardis action provider."""
    return SardisActionProvider(api_key=api_key, api_url=api_url)
