
import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

from sardis_core.config import settings
from sardis_core.services.wallet_service import WalletService
from sardis_core.services.payment_service import PaymentService
from sardis_core.ai.prompts import SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class AgentService:
    """
    Service for AI agents to process natural language instructions.
    """
    
    def __init__(
        self,
        wallet_service: WalletService,
        payment_service: PaymentService
    ):
        self._wallet_service = wallet_service
        self._payment_service = payment_service
        
        # Initialize OpenAI client
        self._client = None
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            
    async def process_instruction(self, agent_id: str, instruction: str) -> Dict[str, Any]:
        """
        Process a natural language instruction for an agent.
        
        Args:
            agent_id: The agent executing the instruction
            instruction: The user's natural language command
            
        Returns:
            Dict containing the execution result or response
        """
        if not self._client:
            return {"error": "AI service not configured (missing API key)"}
            
        # 1. Build Context
        context = await self._build_context(agent_id)
        if not context:
            return {"error": f"Agent {agent_id} not found"}
            
        # 2. Call LLM
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            agent_name=context["agent_name"],
            owner_id=context["owner_id"],
            balances=json.dumps(context["balances"], default=str),
            recent_transactions=json.dumps(context["recent_transactions"], default=str)
        )
        
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": instruction}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            if not content:
                return {"error": "Empty response from AI"}
                
            parsed_response = json.loads(content)
            
            # 3. Execute Tool Call (if any)
            if "tool_call" in parsed_response:
                return await self._execute_tool_call(agent_id, parsed_response["tool_call"])
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return {"error": str(e)}

    async def _build_context(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Gather context for the agent."""
        agent = self._wallet_service.get_agent(agent_id)
        if not agent:
            return None
            
        wallet = await self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return None
            
        # Get recent transactions (mock for now, or fetch from ledger if available)
        # We can add list_transactions to WalletService or Ledger later
        recent_transactions = [] 
        
        return {
            "agent_name": agent.name,
            "owner_id": agent.owner_id,
            "balances": wallet.get_all_balances(),
            "recent_transactions": recent_transactions
        }

    async def _execute_tool_call(self, agent_id: str, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool requested by the AI."""
        name = tool_call.get("name")
        args = tool_call.get("arguments", {})
        
        if name == "pay_merchant":
            return await self._tool_pay_merchant(agent_id, args)
        elif name == "check_balance":
            return await self._tool_check_balance(agent_id, args)
        elif name == "list_merchants":
            return await self._tool_list_merchants()
        else:
            return {"error": f"Unknown tool: {name}"}

    async def _tool_pay_merchant(self, agent_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Pay a merchant."""
        merchant_name = args.get("merchant_name")
        amount_str = args.get("amount")
        currency = args.get("currency", "USDC")
        purpose = args.get("purpose", "Payment")
        
        if not merchant_name or not amount_str:
            return {"error": "Missing merchant_name or amount"}
            
        # Find merchant by name (simple search)
        merchants = self._wallet_service.list_merchants()
        target_merchant = next((m for m in merchants if m.name.lower() == merchant_name.lower()), None)
        
        if not target_merchant:
            return {"error": f"Merchant '{merchant_name}' not found"}
            
        # Execute payment
        try:
            result = await self._payment_service.pay(
                agent_id=agent_id,
                amount=Decimal(amount_str),
                recipient_wallet_id=target_merchant.wallet_id,
                currency=currency,
                purpose=purpose
            )
            
            if result.success:
                return {
                    "response": f"Successfully paid {amount_str} {currency} to {merchant_name}.",
                    "tx_id": result.transaction.tx_id
                }
            else:
                return {"error": f"Payment failed: {result.error}"}
                
        except Exception as e:
            return {"error": f"Payment error: {str(e)}"}

    async def _tool_check_balance(self, agent_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Check balance."""
        currency = args.get("currency", "USDC")
        wallet = await self._wallet_service.get_agent_wallet(agent_id)
        if not wallet:
            return {"error": "Wallet not found"}
            
        balance = wallet.get_balance(currency)
        return {"response": f"Your balance is {balance} {currency}."}

    async def _tool_list_merchants(self) -> Dict[str, Any]:
        """Tool: List merchants."""
        merchants = self._wallet_service.list_merchants()
        names = [m.name for m in merchants]
        return {"response": f"Available merchants: {', '.join(names)}"}
