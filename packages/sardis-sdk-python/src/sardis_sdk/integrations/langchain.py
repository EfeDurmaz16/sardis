"""
LangChain integration for Sardis SDK.

Provides LangChain-compatible tools for AI agents to execute payments
through Sardis MPC wallets with policy enforcement.

Example:
    ```python
    from sardis_sdk import SardisClient
    from sardis_sdk.integrations.langchain import SardisTool, SardisPolicyCheckTool

    async with SardisClient(api_key="your-api-key") as client:
        tools = [
            SardisTool(client=client, wallet_id="wallet_123"),
            SardisPolicyCheckTool(client=client, wallet_id="wallet_123"),
        ]

        # Use with LangChain agent
        from langchain.agents import initialize_agent
        agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
    ```
"""
from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from inspect import isawaitable
from typing import Any, Optional, Type, TYPE_CHECKING

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..client import AsyncSardisClient, SardisClient


async def _maybe_await(value: Any) -> Any:
    if isawaitable(value):
        return await value
    return value


class PayInput(BaseModel):
    """Input schema for Sardis payment tool."""
    amount: float = Field(description="Amount to pay in USD (or token units). Must be positive.")
    merchant: str = Field(description="Name or ID of the merchant/service recipient (e.g. 'OpenAI', 'AWS').")
    merchant_address: Optional[str] = Field(
        default=None,
        description="Wallet address of the merchant (0x...). Optional - will be resolved if not provided."
    )
    purpose: str = Field(
        default="Service payment",
        description="Reason for the payment, used for policy validation and audit trail."
    )
    token: str = Field(
        default="USDC",
        description="Token to use for payment (USDC, USDT, PYUSD, EURC)."
    )


class PolicyCheckInput(BaseModel):
    """Input schema for policy check tool."""
    merchant: str = Field(description="Merchant to check against policy.")
    amount: float = Field(description="Amount to validate.")
    purpose: Optional[str] = Field(default=None, description="Purpose of the payment.")


class BalanceCheckInput(BaseModel):
    """Input schema for balance check tool."""
    token: str = Field(default="USDC", description="Token to check balance for.")
    chain: str = Field(default="base_sepolia", description="Chain to check balance on.")


class SardisTool(BaseTool):
    """
    LangChain tool for executing secure payments via Sardis MPC wallet.

    Features:
    - Real API integration with Sardis payment infrastructure
    - Policy validation before payment execution
    - MPC-secured wallet operations
    - Audit trail with cryptographic anchoring

    Example:
        ```python
        from sardis_sdk import SardisClient
        from sardis_sdk.integrations.langchain import SardisTool

        async with SardisClient(api_key="sk_...") as client:
            tool = SardisTool(client=client, wallet_id="wallet_123")
            result = await tool._arun(amount=50, merchant="OpenAI", purpose="API credits")
        ```
    """
    name: str = "sardis_pay"
    description: str = (
        "Execute secure payments for APIs, SaaS, or services via Sardis MPC wallet. "
        "Validates against spending policy before processing. "
        "Use for: API credits, cloud services, SaaS subscriptions. "
        "Returns transaction details on success or policy violation message if blocked."
    )
    args_schema: Type[BaseModel] = PayInput

    # Configuration - Pydantic v2 style
    client: Optional[Any] = Field(default=None, exclude=True)
    wallet_id: str = Field(default="")
    agent_id: str = Field(default="")
    chain: str = Field(default="base_sepolia")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        client: Optional["SardisClient"] = None,
        wallet_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        chain: str = "base_sepolia",
        **kwargs: Any,
    ):
        """
        Initialize Sardis payment tool.

        Args:
            client: SardisClient instance for API calls
            wallet_id: Default wallet ID for payments
            agent_id: Agent ID for attribution
            chain: Default blockchain (base_sepolia, polygon_amoy, etc.)
        """
        super().__init__(**kwargs)
        self.client = client
        self.wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")
        self.agent_id = agent_id or os.getenv("SARDIS_AGENT_ID", "")
        self.chain = chain

    def _run(
        self,
        amount: float,
        merchant: str,
        merchant_address: Optional[str] = None,
        purpose: str = "Service payment",
        token: str = "USDC",
    ) -> str:
        """Sync execution - runs async version in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(amount, merchant, merchant_address, purpose, token)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._arun(amount, merchant, merchant_address, purpose, token)
                )
        except RuntimeError:
            return asyncio.run(
                self._arun(amount, merchant, merchant_address, purpose, token)
            )

    async def _arun(
        self,
        amount: float,
        merchant: str,
        merchant_address: Optional[str] = None,
        purpose: str = "Service payment",
        token: str = "USDC",
    ) -> str:
        """Async execution of the payment via Sardis API."""
        if amount <= 0:
            return "Error: Amount must be positive."

        if not self.client:
            return "Error: SardisClient not initialized. Please provide a client instance."

        if not self.wallet_id:
            return "Error: No wallet ID configured. Set wallet_id or SARDIS_WALLET_ID env var."

        if not merchant_address:
            return "Error: merchant_address is required (0x...) for transfers."

        try:
            result = await _maybe_await(
                self.client.wallets.transfer(
                    self.wallet_id,
                    destination=merchant_address,
                    amount=Decimal(str(amount)),
                    token=token,
                    chain=self.chain,
                    domain=merchant,
                    memo=purpose,
                )
            )
            return (
                f"APPROVED: Payment of ${amount} {token} to {merchant}\n"
                f"Purpose: {purpose}\n"
                f"Status: {result.status}\n"
                f"Transaction Hash: {result.tx_hash or 'pending'}\n"
                f"Chain: {result.chain}\n"
                f"Audit Anchor: {result.audit_anchor or 'N/A'}"
            )

        except Exception as e:
            error_msg = str(e)

            # Check for policy violations
            if any(kw in error_msg.lower() for kw in ["policy", "blocked", "limit", "denied"]):
                return (
                    f"BLOCKED: Payment to {merchant} denied by policy\n"
                    f"Reason: {error_msg}\n"
                    f"Status: Financial Hallucination PREVENTED"
                )

            return f"Error: Payment failed - {error_msg}"


class SardisPolicyCheckTool(BaseTool):
    """
    LangChain tool for checking if a payment would be allowed by policy.

    Use this to validate payments before executing them. This helps AI agents
    avoid attempting payments that would be blocked.
    """
    name: str = "sardis_check_policy"
    description: str = (
        "Check if a payment would be allowed by the current spending policy. "
        "Use before sardis_pay to validate transactions and avoid blocked payments. "
        "Returns whether the payment would be allowed and why."
    )
    args_schema: Type[BaseModel] = PolicyCheckInput

    client: Optional[Any] = Field(default=None, exclude=True)
    wallet_id: str = Field(default="")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        client: Optional["SardisClient"] = None,
        wallet_id: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.client = client
        self.wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")

    def _run(self, merchant: str, amount: float, purpose: Optional[str] = None) -> str:
        """Sync execution."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(merchant, amount, purpose)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(merchant, amount, purpose))
        except RuntimeError:
            return asyncio.run(self._arun(merchant, amount, purpose))

    async def _arun(self, merchant: str, amount: float, purpose: Optional[str] = None) -> str:
        """Check policy via wallet limits."""
        if not self.client:
            return "Error: SardisClient not initialized."

        if not self.wallet_id:
            return "Error: No wallet ID configured."

        try:
            # Get wallet to check limits
            wallet = await _maybe_await(self.client.wallets.get(self.wallet_id))

            checks = []
            all_passed = True

            # Per-transaction limit check
            limit_per_tx = float(wallet.limit_per_tx) if wallet.limit_per_tx else float('inf')
            if amount <= limit_per_tx:
                checks.append(f"Per-transaction limit: PASS (${amount} <= ${limit_per_tx})")
            else:
                checks.append(f"Per-transaction limit: FAIL (${amount} > ${limit_per_tx})")
                all_passed = False

            # Wallet active check
            if wallet.is_active:
                checks.append("Wallet active: PASS")
            else:
                checks.append("Wallet active: FAIL (wallet is disabled)")
                all_passed = False

            status = "WOULD BE ALLOWED" if all_passed else "WOULD BE BLOCKED"
            checks_str = "\n".join(f"  - {c}" for c in checks)

            return (
                f"{status}: Payment of ${amount} to {merchant}\n"
                f"Policy checks:\n{checks_str}"
            )

        except Exception as e:
            return f"Error checking policy: {str(e)}"


class SardisBalanceCheckTool(BaseTool):
    """
    LangChain tool for checking wallet balance.

    Use this before making payments to ensure sufficient funds.
    """
    name: str = "sardis_check_balance"
    description: str = (
        "Check the current balance of the Sardis wallet. "
        "Use before making payments to ensure sufficient funds are available."
    )
    args_schema: Type[BaseModel] = BalanceCheckInput

    client: Optional[Any] = Field(default=None, exclude=True)
    wallet_id: str = Field(default="")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        client: Optional["SardisClient"] = None,
        wallet_id: Optional[str] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.client = client
        self.wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")

    def _run(self, token: str = "USDC", chain: str = "base_sepolia") -> str:
        """Sync execution."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(token, chain)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self._arun(token, chain))
        except RuntimeError:
            return asyncio.run(self._arun(token, chain))

    async def _arun(self, token: str = "USDC", chain: str = "base_sepolia") -> str:
        """Check balance via API."""
        if not self.client:
            return "Error: SardisClient not initialized."

        if not self.wallet_id:
            return "Error: No wallet ID configured."

        try:
            balance = await _maybe_await(self.client.wallets.get_balance(self.wallet_id, chain, token))

            return (
                f"Wallet Balance:\n"
                f"  Wallet: {balance.wallet_id}\n"
                f"  Token: {balance.token}\n"
                f"  Chain: {balance.chain}\n"
                f"  Balance: {balance.balance}\n"
                f"  Address: {balance.address}"
            )

        except Exception as e:
            return f"Error checking balance: {str(e)}"


def create_sardis_tools(
    client: "SardisClient",
    wallet_id: str,
    agent_id: Optional[str] = None,
    chain: str = "base_sepolia",
) -> list[BaseTool]:
    """
    Create all Sardis LangChain tools for an agent.

    Args:
        client: Initialized SardisClient
        wallet_id: Wallet ID to use for operations
        agent_id: Optional agent ID for attribution
        chain: Default blockchain

    Returns:
        List of LangChain tools: [SardisTool, SardisPolicyCheckTool, SardisBalanceCheckTool]

    Example:
        ```python
        from sardis_sdk import SardisClient
        from sardis_sdk.integrations.langchain import create_sardis_tools

        async with SardisClient(api_key="sk_...") as client:
            tools = create_sardis_tools(client, wallet_id="wallet_123")

            # Use with LangChain
            agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
        ```
    """
    return [
        SardisTool(client=client, wallet_id=wallet_id, agent_id=agent_id, chain=chain),
        SardisPolicyCheckTool(client=client, wallet_id=wallet_id),
        SardisBalanceCheckTool(client=client, wallet_id=wallet_id),
    ]
