
import pytest
from unittest.mock import MagicMock, patch
from sardis_core.services.blockchain_service import BlockchainService

class TestBlockchainService:
    @pytest.fixture
    def mock_web3(self):
        with patch("sardis_core.services.blockchain_service.Web3") as MockWeb3:
            mock_w3_instance = MagicMock()
            MockWeb3.return_value = mock_w3_instance
            MockWeb3.HTTPProvider.return_value = MagicMock()
            yield mock_w3_instance

    def test_init_providers(self, mock_web3):
        service = BlockchainService()
        assert "base" in service.providers
        assert "polygon" in service.providers
        assert "ethereum" in service.providers

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_web3):
        service = BlockchainService()
        
        # Setup mock
        mock_web3.is_connected.return_value = True
        mock_web3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        
        balance = await service.get_balance("ethereum", "0x123")
        assert balance == "1000000000000000000"
        mock_web3.eth.get_balance.assert_called_with("0x123")

    @pytest.mark.asyncio
    async def test_get_token_balance(self, mock_web3):
        service = BlockchainService()
        
        # Setup mock contract
        mock_contract = MagicMock()
        mock_web3.eth.contract.return_value = mock_contract
        mock_contract.functions.balanceOf.return_value.call.return_value = 5000000  # 5 USDC
        
        balance = await service.get_token_balance("base", "0xtoken", "0xwallet")
        assert balance == "5000000"
        mock_web3.eth.contract.assert_called()
