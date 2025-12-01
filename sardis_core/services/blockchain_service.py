
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

    async def transfer_native(self, chain: str, to_address: str, amount_wei: int, private_key: str) -> str:
        """Send native currency (ETH/MATIC). Returns tx hash."""
        w3 = self.get_provider(chain)
        if not w3:
            raise ValueError(f"Chain {chain} not supported")
            
        account = w3.eth.account.from_key(private_key)
        nonce = w3.eth.get_transaction_count(account.address)
        
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id
        }
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return w3.to_hex(tx_hash)

    async def transfer_token(self, chain: str, token_address: str, to_address: str, amount_units: int, private_key: str) -> str:
        """Send ERC-20 token. Returns tx hash."""
        w3 = self.get_provider(chain)
        if not w3:
            raise ValueError(f"Chain {chain} not supported")

        account = w3.eth.account.from_key(private_key)
        
        # ERC-20 Transfer ABI
        abi = [{
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }]
        
        contract = w3.eth.contract(address=token_address, abi=abi)
        
        # Build transaction
        tx = contract.functions.transfer(to_address, amount_units).build_transaction({
            'chainId': w3.eth.chain_id,
            'gas': 100000, # Simple estimation
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return w3.to_hex(tx_hash)

blockchain_service = BlockchainService()
