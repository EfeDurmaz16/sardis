
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from sardis_core.api.dependencies import get_payment_service, get_ledger, get_wallet_service
from sardis_core.config import settings

@pytest.mark.asyncio
async def test_payment_on_chain_integration():
    # Get services
    payment_service = get_payment_service()
    ledger = get_ledger()
    wallet_service = get_wallet_service()
    
    # Create a funded agent wallet
    agent, wallet = await wallet_service.register_agent("test_agent_onchain", "user1")
    await ledger.fund_wallet(wallet.wallet_id, Decimal("100.00"))
    
    # Mock blockchain service
    with patch("sardis_core.services.payment_service.blockchain_service") as mock_blockchain:
        mock_blockchain.transfer_token = AsyncMock(return_value="0xhash123")
        
        # Execute on-chain payment
        recipient_address = "0x1234567890123456789012345678901234567890"
        result = await payment_service.pay(
            agent_id=agent.agent_id,
            amount=Decimal("10.00"),
            recipient_wallet_id=recipient_address,
            execute_on_chain=True
        )
        
        # Verify result
        assert result.success
        assert result.transaction.status.value == "completed"
        assert result.transaction.to_wallet == settings.settlement_wallet_id
        
        assert len(result.transaction.on_chain_records) == 1
        record = result.transaction.on_chain_records[0]
        assert record.tx_hash == "0xhash123"
        assert record.to_address == recipient_address
        
        # Verify blockchain call
        mock_blockchain.transfer_token.assert_called_once()
        call_args = mock_blockchain.transfer_token.call_args
        assert call_args.kwargs["to_address"] == recipient_address
        assert call_args.kwargs["amount_units"] == 10000000 # 10.00 * 10^6
