"""
LangChain integration for Sardis SDK.

Provides SardisTool for use with LangChain agents.
"""

from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Mock policy engine for demo
ALLOWED_CATEGORIES = ["SaaS", "DevTools", "Cloud", "API"]
BLOCKED_MERCHANTS = ["amazon", "ebay", "aliexpress"]
MAX_TRANSACTION = 100


class PayInput(BaseModel):
    """Input schema for Sardis payment tool."""
    amount: float = Field(description="Amount to pay in USD. Must be positive.")
    merchant: str = Field(description="Name or ID of the merchant/service recipient (e.g. 'OpenAI', 'AWS').")
    purpose: str = Field(
        description="Reason for the payment, used for policy validation.",
        default="Service payment"
    )


class PolicyCheckInput(BaseModel):
    """Input schema for policy check tool."""
    merchant: str = Field(description="Merchant to check against policy.")
    amount: float = Field(description="Amount to validate.")


def _check_policy(merchant: str, amount: float) -> dict:
    """Check if payment would be allowed by policy."""
    normalized = merchant.lower().strip()

    # Check blocked merchants
    for blocked in BLOCKED_MERCHANTS:
        if blocked in normalized:
            return {
                "allowed": False,
                "reason": f"Merchant '{merchant}' is not in approved vendor list",
                "prevention": "Financial Hallucination PREVENTED"
            }

    # Check amount
    if amount > MAX_TRANSACTION:
        return {
            "allowed": False,
            "reason": f"Amount ${amount} exceeds limit of ${MAX_TRANSACTION}",
            "prevention": "Financial Hallucination PREVENTED"
        }

    # Check if known SaaS
    saas_vendors = ["openai", "anthropic", "aws", "gcp", "azure", "vercel", "supabase", "stripe", "github"]
    if any(v in normalized for v in saas_vendors):
        return {"allowed": True, "reason": "Vendor in SaaS allowlist"}

    return {
        "allowed": False,
        "reason": f"Vendor '{merchant}' requires explicit approval",
        "prevention": "Financial Hallucination PREVENTED"
    }


class SardisTool(BaseTool):
    """
    LangChain tool for executing secure payments via Sardis MPC wallet.

    Features:
    - Policy validation before payment
    - Financial Hallucination Prevention
    - Virtual card issuance

    Example:
        from sardis_sdk.integrations import SardisTool
        from langchain.agents import initialize_agent

        tools = [SardisTool()]
        agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
    """
    name: str = "sardis_pay"
    description: str = (
        "Execute secure payments for APIs, SaaS, or services via Sardis MPC wallet. "
        "Validates against spending policy before processing. "
        "Use for: API credits, cloud services, SaaS subscriptions."
    )
    args_schema: Type[BaseModel] = PayInput

    def _run(self, amount: float, merchant: str, purpose: str = "Service payment") -> str:
        """Execute the payment with policy validation."""
        if amount <= 0:
            return "Error: Amount must be positive."

        # Check policy first
        policy_result = _check_policy(merchant, amount)

        if not policy_result["allowed"]:
            return (
                f"BLOCKED: {policy_result['reason']}\n"
                f"Status: {policy_result.get('prevention', 'Policy violation')}"
            )

        # Payment approved - return success with mock card
        import random
        card_suffix = random.randint(1000, 9999)
        cvv = random.randint(100, 999)
        tx_id = f"tx_{random.randint(100000, 999999)}"

        return (
            f"APPROVED: Payment of ${amount} to {merchant} for '{purpose}'\n"
            f"Card: 4242 **** **** {card_suffix}\n"
            f"CVV: {cvv}\n"
            f"Transaction ID: {tx_id}"
        )

    async def _arun(self, amount: float, merchant: str, purpose: str = "Service payment") -> str:
        """Async execution of the payment."""
        return self._run(amount, merchant, purpose)


class SardisPolicyCheckTool(BaseTool):
    """
    LangChain tool for checking if a payment would be allowed.

    Use this to validate payments before executing them.
    """
    name: str = "sardis_check_policy"
    description: str = (
        "Check if a payment would be allowed by the current spending policy. "
        "Use before sardis_pay to validate transactions."
    )
    args_schema: Type[BaseModel] = PolicyCheckInput

    def _run(self, merchant: str, amount: float) -> str:
        """Check policy without executing payment."""
        result = _check_policy(merchant, amount)
        status = "WOULD BE ALLOWED" if result["allowed"] else "WOULD BE BLOCKED"
        return f"{status}: {result['reason']}"

    async def _arun(self, merchant: str, amount: float) -> str:
        return self._run(merchant, amount)
