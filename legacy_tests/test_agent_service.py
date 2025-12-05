
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from sardis_core.services.agent_service import AgentService
from sardis_core.models.agent import Agent
from sardis_core.models.wallet import Wallet
from sardis_core.models.merchant import Merchant

@pytest.mark.asyncio
async def test_agent_process_instruction_pay_merchant():
    # Mock services
    mock_wallet_service = MagicMock()
    mock_payment_service = MagicMock()
    
    # Setup mock data
    agent = Agent(agent_id="agent1", name="Test Agent", owner_id="user1")
    wallet = Wallet(agent_id="agent1", balance=Decimal("100.00"))
    merchant = Merchant(merchant_id="m1", name="Amazon", wallet_id="w_m1")
    
    mock_wallet_service.get_agent.return_value = agent
    mock_wallet_service.get_agent_wallet = AsyncMock(return_value=wallet)
    mock_wallet_service.list_merchants.return_value = [merchant]
    
    mock_payment_service.pay = AsyncMock()
    mock_payment_service.pay.return_value.success = True
    mock_payment_service.pay.return_value.transaction.tx_id = "tx_123"
    
    # Mock OpenAI client
    with patch("sardis_core.services.agent_service.AsyncOpenAI") as MockOpenAI:
        mock_client = AsyncMock()
        MockOpenAI.return_value = mock_client
        
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"tool_call": {"name": "pay_merchant", "arguments": {"merchant_name": "Amazon", "amount": "50.00"}}}'
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize service (triggers client init)
        with patch("sardis_core.config.settings.openai_api_key", "sk-test"):
            service = AgentService(mock_wallet_service, mock_payment_service)
            
            # Execute
            result = await service.process_instruction("agent1", "Pay Amazon 50 dollars")
            
            # Verify
            assert "response" in result
            assert "Successfully paid 50.00 USDC to Amazon" in result["response"]
            assert result["tx_id"] == "tx_123"
            
            # Verify payment call
            mock_payment_service.pay.assert_called_once()
            call_args = mock_payment_service.pay.call_args
            assert call_args.kwargs["amount"] == Decimal("50.00")
            assert call_args.kwargs["recipient_wallet_id"] == "w_m1"
