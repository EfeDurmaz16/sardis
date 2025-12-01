
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from sardis_core.config import settings
from typing import Optional, Dict

class BlockchainService:
    def __init__(self):
        self.providers: Dict[str, Web3] = {}
        self._init_providers()

    def _init_providers(self):
        """Initialize Web3 providers for supported chains."""
        chains = {
            "base": settings.base_rpc_url,
            "polygon": settings.polygon_rpc_url,
            "ethereum": settings.ethereum_rpc_url
        }
        
        for name, url in chains.items():
            try:
                w3 = Web3(Web3.HTTPProvider(url))
                # Add PoA middleware for Polygon/Base if needed
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                self.providers[name] = w3
            except Exception as e:
                print(f"Failed to connect to {name}: {e}")

    def get_provider(self, chain: str) -> Optional[Web3]:
        return self.providers.get(chain)

    async def get_balance(self, chain: str, address: str) -> str:
        """Get native token balance (ETH/MATIC) in wei."""
        w3 = self.get_provider(chain)
        if not w3:
            raise ValueError(f"Chain {chain} not supported")
        
        if not w3.is_connected():
             raise ConnectionError(f"Not connected to {chain}")

        balance = w3.eth.get_balance(address)
        return str(balance)

    async def get_token_balance(self, chain: str, token_address: str, wallet_address: str) -> str:
        """Get ERC-20 token balance."""
        w3 = self.get_provider(chain)
        if not w3:
            raise ValueError(f"Chain {chain} not supported")

        # Minimal ERC-20 ABI
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            }
        ]
        
        contract = w3.eth.contract(address=token_address, abi=abi)
        balance = contract.functions.balanceOf(wallet_address).call()
        return str(balance)

blockchain_service = BlockchainService()
