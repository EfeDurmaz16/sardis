"""
LlamaIndex Integration for Sardis SDK.

Provides LlamaIndex-compatible tools for AI agents to execute payments
through Sardis MPC wallets with policy enforcement.

Example:
    ```python
    from llama_index.core.agent import ReActAgent
    from llama_index.llms.openai import OpenAI
    from sardis_sdk import SardisClient
    from sardis_sdk.integrations.llamaindex import create_sardis_tools

    async with SardisClient(api_key="sk_...") as client:
        tools = create_sardis_tools(client, wallet_id="wallet_123")
        llm = OpenAI(model="gpt-4")
        agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)
        response = agent.chat("Pay $50 to OpenAI for API credits")
    ```
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

try:
    from llama_index.core.tools import FunctionTool, AsyncBaseTool, ToolMetadata
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    FunctionTool = None
    AsyncBaseTool = None
    ToolMetadata = None
    LLAMA_INDEX_AVAILABLE = False

if TYPE_CHECKING:
    from ..client import SardisClient


def _generate_mandate_id() -> str:
    """Generate a unique mandate ID."""
    timestamp = hex(int(datetime.now(timezone.utc).timestamp() * 1000))[2:]
    random_part = uuid.uuid4().hex[:8]
    return f"mnd_{timestamp}{random_part}"


def _create_audit_hash(data: str) -> str:
    """Create SHA-256 hash for audit purposes."""
    return hashlib.sha256(data.encode()).hexdigest()


class SardisPaymentTool:
    """
    LlamaIndex tool for executing payments via Sardis MPC wallet.

    This class wraps the payment functionality and maintains state
    (client reference, wallet_id, etc.) across calls.
    """

    def __init__(
        self,
        client: "SardisClient",
        wallet_id: str,
        agent_id: Optional[str] = None,
        chain: str = "base_sepolia",
    ):
        self.client = client
        self.wallet_id = wallet_id
        self.agent_id = agent_id or os.getenv("SARDIS_AGENT_ID", "")
        self.chain = chain

    def pay_vendor(
        self,
        amount: float,
        merchant: str,
        purpose: str = "Service payment",
        merchant_address: Optional[str] = None,
        token: str = "USDC",
    ) -> str:
        """
        Execute a payment via Sardis MPC wallet.

        Args:
            amount: Amount to pay in USD (or token units)
            merchant: Name of the merchant/service provider
            purpose: Reason for the payment
            merchant_address: Optional wallet address of merchant
            token: Token to use (USDC, USDT, PYUSD, EURC)

        Returns:
            String describing the result
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._async_pay(amount, merchant, purpose, merchant_address, token)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._async_pay(amount, merchant, purpose, merchant_address, token)
                )
        except RuntimeError:
            return asyncio.run(
                self._async_pay(amount, merchant, purpose, merchant_address, token)
            )

    async def _async_pay(
        self,
        amount: float,
        merchant: str,
        purpose: str,
        merchant_address: Optional[str],
        token: str,
    ) -> str:
        """Async implementation of payment."""
        if amount <= 0:
            return "Error: Amount must be positive."

        if not self.wallet_id:
            return "Error: No wallet ID configured."

        try:
            mandate_id = _generate_mandate_id()
            timestamp = datetime.now(timezone.utc).isoformat()
            amount_minor = str(int(amount * 1_000_000))

            audit_data = f"{mandate_id}:{self.wallet_id}:{merchant_address or merchant}:{amount_minor}:{token}:{timestamp}"
            audit_hash = _create_audit_hash(audit_data)

            mandate = {
                "mandate_id": mandate_id,
                "subject": self.wallet_id,
                "destination": merchant_address or f"pending:{merchant}",
                "amount_minor": amount_minor,
                "token": token,
                "chain": self.chain,
                "purpose": purpose,
                "vendor_name": merchant,
                "agent_id": self.agent_id,
                "timestamp": timestamp,
                "audit_hash": audit_hash,
                "metadata": {
                    "vendor": merchant,
                    "category": "saas",
                    "initiated_by": "ai_agent",
                    "tool": "llamaindex",
                },
            }

            result = await self.client.payments.execute_mandate(mandate)

            return (
                f"APPROVED: Payment of ${amount} {token} to {merchant}\n"
                f"Purpose: {purpose}\n"
                f"Payment ID: {result.payment_id}\n"
                f"Status: {result.status}\n"
                f"Transaction Hash: {result.tx_hash or 'pending'}\n"
                f"Chain: {result.chain}"
            )

        except Exception as e:
            error_msg = str(e)
            if any(kw in error_msg.lower() for kw in ["policy", "blocked", "limit", "denied"]):
                return (
                    f"BLOCKED: Payment to {merchant} denied by policy\n"
                    f"Reason: {error_msg}\n"
                    f"Status: Financial Hallucination PREVENTED"
                )
            return f"Error: Payment failed - {error_msg}"

    def check_balance(self, token: str = "USDC", chain: Optional[str] = None) -> str:
        """
        Check wallet balance.

        Args:
            token: Token to check (USDC, USDT, etc.)
            chain: Chain to check balance on

        Returns:
            String with balance information
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._async_check_balance(token, chain or self.chain)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._async_check_balance(token, chain or self.chain)
                )
        except RuntimeError:
            return asyncio.run(self._async_check_balance(token, chain or self.chain))

    async def _async_check_balance(self, token: str, chain: str) -> str:
        """Async implementation of balance check."""
        if not self.wallet_id:
            return "Error: No wallet ID configured."

        try:
            balance = await self.client.wallets.get_balance(self.wallet_id, chain, token)
            return (
                f"Wallet Balance:\n"
                f"  Token: {balance.token}\n"
                f"  Chain: {balance.chain}\n"
                f"  Balance: {balance.balance}\n"
                f"  Address: {balance.address}"
            )
        except Exception as e:
            return f"Error checking balance: {str(e)}"

    def check_policy(self, amount: float, merchant: str) -> str:
        """
        Check if a payment would be allowed by policy.

        Args:
            amount: Amount to check
            merchant: Merchant name

        Returns:
            String describing policy check result
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._async_check_policy(amount, merchant)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self._async_check_policy(amount, merchant))
        except RuntimeError:
            return asyncio.run(self._async_check_policy(amount, merchant))

    async def _async_check_policy(self, amount: float, merchant: str) -> str:
        """Async implementation of policy check."""
        if not self.wallet_id:
            return "Error: No wallet ID configured."

        try:
            wallet = await self.client.wallets.get(self.wallet_id)
            limit_per_tx = float(wallet.limit_per_tx) if wallet.limit_per_tx else float('inf')

            checks = []
            all_passed = True

            if amount <= limit_per_tx:
                checks.append(f"Per-transaction limit: PASS (${amount} <= ${limit_per_tx})")
            else:
                checks.append(f"Per-transaction limit: FAIL (${amount} > ${limit_per_tx})")
                all_passed = False

            if wallet.is_active:
                checks.append("Wallet active: PASS")
            else:
                checks.append("Wallet active: FAIL")
                all_passed = False

            status = "WOULD BE ALLOWED" if all_passed else "WOULD BE BLOCKED"
            checks_str = "\n".join(f"  - {c}" for c in checks)

            return f"{status}: Payment of ${amount} to {merchant}\nPolicy checks:\n{checks_str}"

        except Exception as e:
            return f"Error checking policy: {str(e)}"


def create_sardis_tools(
    client: "SardisClient",
    wallet_id: str,
    agent_id: Optional[str] = None,
    chain: str = "base_sepolia",
) -> list[Any]:
    """
    Create LlamaIndex tools for Sardis payments.

    Args:
        client: Initialized SardisClient
        wallet_id: Wallet ID to use for operations
        agent_id: Optional agent ID for attribution
        chain: Default blockchain

    Returns:
        List of LlamaIndex FunctionTools

    Raises:
        ImportError: If llama-index-core is not installed

    Example:
        ```python
        from llama_index.core.agent import ReActAgent
        from sardis_sdk import SardisClient
        from sardis_sdk.integrations.llamaindex import create_sardis_tools

        async with SardisClient(api_key="sk_...") as client:
            tools = create_sardis_tools(client, wallet_id="wallet_123")
            agent = ReActAgent.from_tools(tools, llm=llm)
        ```
    """
    if not LLAMA_INDEX_AVAILABLE:
        raise ImportError(
            "llama-index-core is required to use this integration. "
            "Install with: pip install llama-index-core"
        )

    tool_instance = SardisPaymentTool(
        client=client,
        wallet_id=wallet_id,
        agent_id=agent_id,
        chain=chain,
    )

    return [
        FunctionTool.from_defaults(
            fn=tool_instance.pay_vendor,
            name="sardis_pay",
            description=(
                "Execute a secure payment using Sardis MPC wallet. "
                "Validates against spending policy before processing. "
                "Use for: API credits, cloud services, SaaS subscriptions. "
                "Args: amount (float), merchant (str), purpose (str, optional), "
                "merchant_address (str, optional), token (str, optional: USDC/USDT/PYUSD/EURC)"
            ),
        ),
        FunctionTool.from_defaults(
            fn=tool_instance.check_balance,
            name="sardis_check_balance",
            description=(
                "Check the current balance of the Sardis wallet. "
                "Use before making payments to ensure sufficient funds. "
                "Args: token (str, optional: USDC/USDT), chain (str, optional)"
            ),
        ),
        FunctionTool.from_defaults(
            fn=tool_instance.check_policy,
            name="sardis_check_policy",
            description=(
                "Check if a payment would be allowed by the spending policy "
                "without executing it. Use to validate before payment. "
                "Args: amount (float), merchant (str)"
            ),
        ),
    ]


def get_llamaindex_tool(
    client: Optional["SardisClient"] = None,
    wallet_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    chain: str = "base_sepolia",
) -> Any:
    """
    Returns a single LlamaIndex FunctionTool for Sardis payments.

    This is a convenience function for simple use cases where only
    the payment tool is needed.

    Args:
        client: SardisClient instance (required for real operations)
        wallet_id: Wallet ID to use
        agent_id: Agent ID for attribution
        chain: Default blockchain

    Returns:
        LlamaIndex FunctionTool for payments

    Raises:
        ImportError: If llama-index-core is not installed
    """
    if not LLAMA_INDEX_AVAILABLE:
        raise ImportError(
            "llama-index-core is required to use this integration. "
            "Install with: pip install llama-index-core"
        )

    if client is None:
        # Fallback to a simple function for demo/testing
        def _demo_pay(amount: float, merchant: str, purpose: str = "Service payment") -> str:
            return (
                f"DEMO MODE: Payment of ${amount} to {merchant} for '{purpose}' "
                f"would be executed. Provide a SardisClient for real operations."
            )

        return FunctionTool.from_defaults(
            fn=_demo_pay,
            name="sardis_pay",
            description="Execute payments via Sardis (demo mode - provide client for real ops)",
        )

    wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID", "")
    tools = create_sardis_tools(client, wallet_id, agent_id, chain)
    return tools[0]  # Return just the payment tool
