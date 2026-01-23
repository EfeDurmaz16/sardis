"""Multi-chain stablecoin executor with MPC signing support."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate
from sardis_ledger.records import ChainReceipt

logger = logging.getLogger(__name__)


# Chain configurations
CHAIN_CONFIGS = {
    # Base
    "base_sepolia": {
        "chain_id": 84532,
        "rpc_url": "https://sepolia.base.org",
        "explorer": "https://sepolia.basescan.org",
        "native_token": "ETH",
        "block_time": 2,  # seconds
    },
    "base": {
        "chain_id": 8453,
        "rpc_url": "https://mainnet.base.org",
        "explorer": "https://basescan.org",
        "native_token": "ETH",
        "block_time": 2,
    },
    # Polygon
    "polygon_amoy": {
        "chain_id": 80002,
        "rpc_url": "https://rpc-amoy.polygon.technology",
        "explorer": "https://amoy.polygonscan.com",
        "native_token": "MATIC",
        "block_time": 2,
    },
    "polygon": {
        "chain_id": 137,
        "rpc_url": "https://polygon-rpc.com",
        "explorer": "https://polygonscan.com",
        "native_token": "MATIC",
        "block_time": 2,
    },
    # Ethereum
    "ethereum_sepolia": {
        "chain_id": 11155111,
        "rpc_url": "https://rpc.sepolia.org",
        "explorer": "https://sepolia.etherscan.io",
        "native_token": "ETH",
        "block_time": 12,
    },
    "ethereum": {
        "chain_id": 1,
        "rpc_url": "https://eth.llamarpc.com",
        "explorer": "https://etherscan.io",
        "native_token": "ETH",
        "block_time": 12,
    },
    # Arbitrum
    "arbitrum_sepolia": {
        "chain_id": 421614,
        "rpc_url": "https://sepolia-rollup.arbitrum.io/rpc",
        "explorer": "https://sepolia.arbiscan.io",
        "native_token": "ETH",
        "block_time": 1,
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpc_url": "https://arb1.arbitrum.io/rpc",
        "explorer": "https://arbiscan.io",
        "native_token": "ETH",
        "block_time": 1,
    },
    # Optimism
    "optimism_sepolia": {
        "chain_id": 11155420,
        "rpc_url": "https://sepolia.optimism.io",
        "explorer": "https://sepolia-optimism.etherscan.io",
        "native_token": "ETH",
        "block_time": 2,
    },
    "optimism": {
        "chain_id": 10,
        "rpc_url": "https://mainnet.optimism.io",
        "explorer": "https://optimistic.etherscan.io",
        "native_token": "ETH",
        "block_time": 2,
    },
    # Solana (different architecture - requires separate handling)
    # NOTE: Solana support is EXPERIMENTAL and NOT YET IMPLEMENTED
    # Requires Anchor programs instead of Solidity contracts
    "solana_devnet": {
        "chain_id": 0,  # Solana doesn't use chain IDs like EVM
        "rpc_url": "https://api.devnet.solana.com",
        "explorer": "https://explorer.solana.com/?cluster=devnet",
        "native_token": "SOL",
        "block_time": 0.4,
        "is_solana": True,
        "experimental": True,
        "not_implemented": True,
    },
    "solana": {
        "chain_id": 0,
        "rpc_url": "https://api.mainnet-beta.solana.com",
        "explorer": "https://explorer.solana.com",
        "native_token": "SOL",
        "block_time": 0.4,
        "is_solana": True,
        "experimental": True,
        "not_implemented": True,
    },
}

# Stablecoin contract addresses by chain
STABLECOIN_ADDRESSES = {
    # Base
    "base_sepolia": {
        "USDC": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    },
    "base": {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "EURC": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
    },
    # Polygon
    "polygon_amoy": {
        "USDC": "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",
    },
    "polygon": {
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "EURC": "0x9912af6da4F87Fc2b0Ae0B77A124e9B1B7Ba2F70",
    },
    # Ethereum
    "ethereum_sepolia": {
        "USDC": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    },
    "ethereum": {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "PYUSD": "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",
        "EURC": "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",
    },
    # Arbitrum
    "arbitrum_sepolia": {
        "USDC": "0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d",
    },
    "arbitrum": {
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        # NOTE: EURC not yet available on Arbitrum - will add when Circle deploys
    },
    # Optimism
    "optimism_sepolia": {
        "USDC": "0x5fd84259d66Cd46123540766Be93DFE6D43130D7",
    },
    "optimism": {
        "USDC": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
    },
    # Solana (SPL token addresses - different format)
    "solana_devnet": {
        "USDC": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",  # Devnet USDC
    },
    "solana": {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # Mainnet USDC
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # Mainnet USDT
        "PYUSD": "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",  # PYUSD on Solana
    },
}

# Sardis contract addresses by chain (populated after deployment)
# See docs/contracts-deployment.md for deployment instructions
#
# Environment variable overrides (format: SARDIS_{CHAIN}_{CONTRACT}_ADDRESS)
# Example: SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
#
# Deployment order:
#   1. Base Sepolia (primary testnet)
#   2. Polygon Amoy
#   3. Ethereum Sepolia
#   4. Arbitrum Sepolia
#   5. Optimism Sepolia
#
# After deployment, either:
#   a) Set environment variables for each chain, OR
#   b) Update the addresses in this file and redeploy
SARDIS_CONTRACTS = {
    # Testnets
    "base_sepolia": {
        "wallet_factory": "",  # Deploy with: forge script Deploy.s.sol --rpc-url base_sepolia
        "escrow": "",          # Contract addresses will be output after deployment
    },
    "polygon_amoy": {
        "wallet_factory": "",
        "escrow": "",
    },
    "ethereum_sepolia": {
        "wallet_factory": "",
        "escrow": "",
    },
    "arbitrum_sepolia": {
        "wallet_factory": "",
        "escrow": "",
    },
    "optimism_sepolia": {
        "wallet_factory": "",
        "escrow": "",
    },
    # Mainnets - requires audit before deployment
    "base": {
        "wallet_factory": "",
        "escrow": "",
    },
    "polygon": {
        "wallet_factory": "",
        "escrow": "",
    },
    "ethereum": {
        "wallet_factory": "",
        "escrow": "",
    },
    "arbitrum": {
        "wallet_factory": "",
        "escrow": "",
    },
    "optimism": {
        "wallet_factory": "",
        "escrow": "",
    },
    # Solana - requires different contract architecture (Anchor programs)
    # NOTE: Solana integration is EXPERIMENTAL and NOT IMPLEMENTED
    "solana_devnet": {
        "wallet_program": "",  # Solana uses programs, not contracts
        "escrow_program": "",
        "experimental": True,
        "not_implemented": True,
    },
    "solana": {
        "wallet_program": "",
        "escrow_program": "",
        "experimental": True,
        "not_implemented": True,
    },
}


def get_sardis_contract_address(chain: str, contract_type: str) -> str:
    """
    Get Sardis contract address for a chain with environment variable override.

    Environment variables take precedence over hardcoded addresses.
    Format: SARDIS_{CHAIN}_{CONTRACT}_ADDRESS

    Args:
        chain: Chain name (e.g., "base_sepolia", "polygon_amoy")
        contract_type: Contract type ("wallet_factory" or "escrow")

    Returns:
        Contract address or empty string if not configured

    Raises:
        ValueError: If chain is Solana (not implemented)

    Example:
        >>> os.environ["SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS"] = "0x123..."
        >>> get_sardis_contract_address("base_sepolia", "wallet_factory")
        '0x123...'
    """
    chain_config = SARDIS_CONTRACTS.get(chain, {})

    # Check if chain is experimental/not implemented
    if chain_config.get("not_implemented"):
        raise ValueError(f"Chain {chain} is not yet implemented")

    # Build environment variable name
    # e.g., SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS
    env_key = f"SARDIS_{chain.upper()}_{contract_type.upper()}_ADDRESS"

    # Environment variable takes precedence
    env_address = os.getenv(env_key, "")
    if env_address:
        return env_address

    # Fall back to hardcoded address
    return chain_config.get(contract_type, "")


def get_sardis_wallet_factory(chain: str) -> str:
    """Get SardisWalletFactory address for a chain."""
    return get_sardis_contract_address(chain, "wallet_factory")


def get_sardis_escrow(chain: str) -> str:
    """Get SardisEscrow address for a chain."""
    return get_sardis_contract_address(chain, "escrow")


def is_chain_configured(chain: str) -> bool:
    """
    Check if a chain has Sardis contracts configured.

    Returns True if either:
    - Environment variables are set for the chain, OR
    - Hardcoded addresses are present in SARDIS_CONTRACTS
    """
    if chain not in SARDIS_CONTRACTS:
        return False

    chain_config = SARDIS_CONTRACTS[chain]

    # Check if not implemented
    if chain_config.get("not_implemented"):
        return False

    # Check for wallet_factory (required)
    wallet_factory = get_sardis_wallet_factory(chain)
    return bool(wallet_factory)


class TransactionStatus(str, Enum):
    """Transaction status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class SubmittedTx:
    """A submitted transaction."""
    tx_hash: str
    chain: str
    audit_anchor: str
    status: TransactionStatus = TransactionStatus.SUBMITTED
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GasEstimate:
    """Gas estimation result."""
    gas_limit: int
    gas_price_gwei: Decimal
    max_fee_gwei: Decimal
    max_priority_fee_gwei: Decimal
    estimated_cost_wei: int
    estimated_cost_usd: Optional[Decimal] = None


@dataclass
class TransactionRequest:
    """A transaction to be signed and submitted."""
    chain: str
    to_address: str
    value: int = 0  # Native token value in wei
    data: bytes = b""
    gas_limit: Optional[int] = None
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    nonce: Optional[int] = None


class MPCSignerPort(ABC):
    """Abstract interface for MPC signing providers."""

    @abstractmethod
    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign a transaction and return the signed tx hex."""
        pass

    @abstractmethod
    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get the wallet address for a chain."""
        pass


class SimulatedMPCSigner(MPCSignerPort):
    """Simulated MPC signer for development."""

    def __init__(self):
        self._wallets: Dict[str, str] = {}

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Simulate signing - returns a mock signed transaction."""
        # In simulation, we just return a mock tx hash
        return "0x" + secrets.token_hex(32)

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get or generate a simulated address."""
        key = f"{wallet_id}:{chain}"
        if key not in self._wallets:
            self._wallets[key] = "0x" + secrets.token_hex(20)
        return self._wallets[key]


class TurnkeyMPCSigner(MPCSignerPort):
    """
    Turnkey MPC signing integration with proper Ed25519 API authentication.
    
    Turnkey uses a stamp-based authentication where each request is signed
    with the API private key (Ed25519) and includes the public key + timestamp + signature.
    
    Environment variables required:
    - TURNKEY_ORGANIZATION_ID: Your Turnkey organization ID
    - TURNKEY_API_PUBLIC_KEY: Hex-encoded Ed25519 public key
    - TURNKEY_API_PRIVATE_KEY: Hex-encoded Ed25519 private key (or path to PEM file)
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    # Activity polling configuration
    ACTIVITY_POLL_INTERVAL = 0.5  # seconds
    ACTIVITY_TIMEOUT = 30  # seconds

    def __init__(
        self,
        api_base: str,
        organization_id: str,
        api_public_key: str,
        api_private_key: str,
    ):
        self._api_base = api_base.rstrip("/")
        self._org_id = organization_id
        self._api_public_key = api_public_key
        self._api_private_key = api_private_key
        self._http_client = None
        self._signing_key = None
        
        # Initialize signing key
        self._init_signing_key()
    
    def _init_signing_key(self):
        """Initialize P256 (ECDSA) signing key from Turnkey API credentials.
        
        Uses cryptography library exactly like Turnkey's official Python stamper.
        """
        if not self._api_private_key:
            logger.warning("No Turnkey API private key provided")
            return
        
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            
            # Derive private key from hex string (as integer)
            # Turnkey's stamper.py: ec.derive_private_key(int(API_PRIVATE_KEY, 16), ec.SECP256R1())
            private_key_int = int(self._api_private_key, 16)
            self._signing_key = ec.derive_private_key(private_key_int, ec.SECP256R1())
            
            logger.info("Turnkey P256 signing key initialized successfully (using cryptography library)")
                
        except ImportError:
            logger.error("cryptography library not installed. Install with: pip install cryptography")
        except Exception as e:
            logger.error(f"Failed to initialize Turnkey signing key: {e}")
    
    def _create_stamp(self, body: str) -> str:
        """
        Create Turnkey API stamp for request authentication using P256/ECDSA.
        
        Uses cryptography library exactly like Turnkey's official Python stamper.
        
        Reference: https://github.com/tkhq/python-sdk
        """
        import base64
        import json
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        
        if not self._signing_key:
            raise ValueError("Turnkey signing key not initialized")
        
        # Sign payload with ECDSA SHA256 (exactly like Turnkey's stamper.py)
        signature = self._signing_key.sign(body.encode(), ec.ECDSA(hashes.SHA256()))
        
        # Create stamp payload
        stamp_payload = {
            "publicKey": self._api_public_key,
            "scheme": "SIGNATURE_SCHEME_TK_API_P256",
            "signature": signature.hex(),
        }
        
        # Base64URL encode the stamp (without padding)
        stamp_json = json.dumps(stamp_payload)
        stamp_b64 = base64.urlsafe_b64encode(stamp_json.encode()).decode().rstrip("=")
        
        return stamp_b64

    async def _get_client(self):
        """Get or create HTTP client with retry configuration."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._http_client

    async def _make_request(
        self,
        method: str,
        path: str,
        body: Dict[str, Any],
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make authenticated request to Turnkey API with retry logic."""
        import json
        
        body_str = json.dumps(body, separators=(",", ":"))
        
        headers = {
            "Content-Type": "application/json",
            "X-Stamp": self._create_stamp(body_str),
        }
        
        client = await self._get_client()
        url = f"{self._api_base}{path}"
        
        try:
            if method.upper() == "POST":
                response = await client.post(url, content=body_str, headers=headers)
            else:
                response = await client.get(url, headers=headers)
            
            if response.status_code == 429:  # Rate limited
                if retry_count < self.MAX_RETRIES:
                    await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                    return await self._make_request(method, path, body, retry_count + 1)
                raise Exception("Rate limited by Turnkey API")
            
            # Log detailed error for 4xx responses
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    logger.error(f"Turnkey API error {response.status_code}: {error_body}")
                except:
                    logger.error(f"Turnkey API error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Turnkey request failed (attempt {retry_count + 1}): {e}")
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._make_request(method, path, body, retry_count + 1)
            raise

    async def _poll_activity(self, activity_id: str) -> Dict[str, Any]:
        """Poll for activity completion."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < self.ACTIVITY_TIMEOUT:
            result = await self._make_request(
                "POST",
                "/public/v1/query/get_activity",
                {
                    "organizationId": self._org_id,
                    "activityId": activity_id,
                },
            )
            
            activity = result.get("activity", {})
            status = activity.get("status", "")
            
            if status == "ACTIVITY_STATUS_COMPLETED":
                return activity
            elif status == "ACTIVITY_STATUS_FAILED":
                failure_reason = activity.get("result", {}).get("failureReason", "Unknown")
                raise Exception(f"Turnkey activity failed: {failure_reason}")
            elif status == "ACTIVITY_STATUS_REJECTED":
                raise Exception("Turnkey activity was rejected")
            
            await asyncio.sleep(self.ACTIVITY_POLL_INTERVAL)
        
        raise TimeoutError(f"Turnkey activity {activity_id} timed out")

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign transaction via Turnkey API.
        
        Turnkey expects unsigned transaction as RLP-encoded hex string.
        """
        import rlp
        
        chain_config = CHAIN_CONFIGS.get(tx.chain, {})
        chain_id = chain_config.get("chain_id", 1)
        
        # Build EIP-1559 transaction (Type 2)
        # Format: 0x02 || rlp([chainId, nonce, maxPriorityFeePerGas, maxFeePerGas, gasLimit, to, value, data, accessList])
        nonce = tx.nonce if tx.nonce is not None else 0
        max_priority_fee = tx.max_priority_fee_per_gas or 1_000_000_000  # 1 gwei
        max_fee = tx.max_fee_per_gas or 50_000_000_000  # 50 gwei
        gas_limit = tx.gas_limit or 100000
        to_address = bytes.fromhex(tx.to_address[2:]) if tx.to_address.startswith("0x") else bytes.fromhex(tx.to_address)
        value = tx.value
        data = tx.data or b""
        access_list = []  # Empty access list for now
        
        # RLP encode the transaction fields (without signature)
        tx_fields = [
            chain_id,
            nonce,
            max_priority_fee,
            max_fee,
            gas_limit,
            to_address,
            value,
            data,
            access_list,
        ]
        
        # Encode with EIP-1559 type prefix
        rlp_encoded = rlp.encode(tx_fields)
        unsigned_tx_hex = "02" + rlp_encoded.hex()  # 0x02 prefix for EIP-1559
        
        # Create sign transaction activity
        activity_body = {
            "type": "ACTIVITY_TYPE_SIGN_TRANSACTION_V2",
            "organizationId": self._org_id,
            "timestampMs": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            "parameters": {
                "signWith": wallet_id,
                "type": "TRANSACTION_TYPE_ETHEREUM",
                "unsignedTransaction": unsigned_tx_hex,
            },
        }
        
        logger.info(f"Submitting sign transaction activity for wallet {wallet_id}")
        
        # Submit the activity
        result = await self._make_request(
            "POST",
            "/public/v1/submit/sign_transaction",
            activity_body,
        )
        
        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        status = activity.get("status", "")
        
        # If not immediately completed, poll for completion
        if status != "ACTIVITY_STATUS_COMPLETED":
            logger.info(f"Polling for activity {activity_id} completion")
            activity = await self._poll_activity(activity_id)
        
        # Extract signed transaction (Turnkey returns in signTransactionResult)
        sign_result = activity.get("result", {}).get("signTransactionResult", {})
        signed_tx = sign_result.get("signedTransaction", "")
        
        if not signed_tx:
            # Fallback to old path
            signed_tx = activity.get("result", {}).get("signedTransaction", "")
        
        if not signed_tx:
            raise Exception("No signed transaction returned from Turnkey")
        
        logger.info(f"Transaction signed successfully")
        return signed_tx

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get wallet address from Turnkey."""
        result = await self._make_request(
            "POST",
            "/public/v1/query/list_wallet_accounts",
            {
                "organizationId": self._org_id,
                "walletId": wallet_id,
            },
        )
        
        # Extract address from accounts list
        accounts = result.get("accounts", [])
        for account in accounts:
            address_format = account.get("addressFormat", "")
            if address_format == "ADDRESS_FORMAT_ETHEREUM":
                return account.get("address", "")
        
        raise ValueError(f"No Ethereum address found for wallet {wallet_id}")

    async def create_wallet(self, wallet_name: str) -> Dict[str, str]:
        """
        Create a new wallet in Turnkey.
        
        Returns:
            Dict with 'wallet_id' and 'address' keys
        """
        activity_body = {
            "type": "ACTIVITY_TYPE_CREATE_WALLET",
            "organizationId": self._org_id,
            "timestampMs": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            "parameters": {
                "walletName": wallet_name,
                "accounts": [
                    {
                        "curve": "CURVE_SECP256K1",
                        "pathFormat": "PATH_FORMAT_BIP32",
                        "path": "m/44'/60'/0'/0/0",
                        "addressFormat": "ADDRESS_FORMAT_ETHEREUM",
                    }
                ],
            },
        }
        
        logger.info(f"Creating new Turnkey wallet: {wallet_name}")
        
        result = await self._make_request(
            "POST",
            "/public/v1/submit/create_wallet",
            activity_body,
        )
        
        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        status = activity.get("status", "")
        
        if status != "ACTIVITY_STATUS_COMPLETED":
            activity = await self._poll_activity(activity_id)
        
        wallet_result = activity.get("result", {}).get("createWalletResult", {})
        wallet_id = wallet_result.get("walletId", "")
        addresses = wallet_result.get("addresses", [])
        
        address = addresses[0] if addresses else ""
        
        logger.info(f"Created wallet {wallet_id} with address {address}")
        
        return {
            "wallet_id": wallet_id,
            "address": address,
        }

    async def list_wallets(self) -> List[Dict[str, Any]]:
        """List all wallets in the organization."""
        result = await self._make_request(
            "POST",
            "/public/v1/query/list_wallets",
            {
                "organizationId": self._org_id,
            },
        )
        
        return result.get("wallets", [])

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class LocalAccountSigner(MPCSignerPort):
    """Local EOA signer for MVP/demo without MPC."""

    def __init__(self, private_key: str, address: str | None = None):
        from web3 import Web3
        from eth_account import Account

        if not private_key:
            raise ValueError("SARDIS_EOA_PRIVATE_KEY is required for local signer")
        self._w3 = Web3()
        self._account = Account.from_key(private_key)
        self._address = address or self._account.address

    async def sign_transaction(self, wallet_id: str, tx: TransactionRequest) -> str:
        tx_dict = {
            "to": tx.to_address,
            "value": tx.value,
            "data": tx.data if isinstance(tx.data, bytes) else bytes(tx.data or b""),
            "gas": tx.gas_limit or 120000,
            "maxFeePerGas": tx.max_fee_per_gas or 50_000_000_000,
            "maxPriorityFeePerGas": tx.max_priority_fee_per_gas or 1_000_000_000,
            "nonce": tx.nonce or 0,
            "chainId": CHAIN_CONFIGS.get(tx.chain, {}).get("chain_id", 84532),
            "type": 2,
        }
        signed = self._w3.eth.account.sign_transaction(tx_dict, self._account.key)
        return signed.rawTransaction.hex()

    async def get_address(self, wallet_id: str, chain: str) -> str:  # noqa: ARG002
        return self._address


@dataclass
class RPCEndpoint:
    """An RPC endpoint with health tracking."""
    url: str
    priority: int = 0  # Lower is higher priority
    healthy: bool = True
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failure_count: int = 0
    latency_ms: float = 0.0
    
    # Health thresholds
    MAX_FAILURES = 3
    HEALTH_CHECK_INTERVAL = 60  # seconds
    
    def mark_success(self, latency_ms: float) -> None:
        """Mark endpoint as healthy after successful call."""
        self.healthy = True
        self.failure_count = 0
        self.latency_ms = latency_ms
        self.last_check = datetime.now(timezone.utc)
    
    def mark_failure(self) -> None:
        """Mark endpoint as potentially unhealthy after failure."""
        self.failure_count += 1
        if self.failure_count >= self.MAX_FAILURES:
            self.healthy = False
        self.last_check = datetime.now(timezone.utc)
    
    def needs_health_check(self) -> bool:
        """Check if this endpoint needs a health check."""
        if self.healthy:
            return False
        elapsed = (datetime.now(timezone.utc) - self.last_check).total_seconds()
        return elapsed >= self.HEALTH_CHECK_INTERVAL


# Additional fallback RPC URLs for each chain
FALLBACK_RPC_URLS = {
    "base_sepolia": [
        "https://sepolia.base.org",
        "https://base-sepolia-rpc.publicnode.com",
    ],
    "base": [
        "https://mainnet.base.org",
        "https://base-mainnet.public.blastapi.io",
    ],
    "polygon": [
        "https://polygon-rpc.com",
        "https://polygon-mainnet.public.blastapi.io",
    ],
    "polygon_amoy": [
        "https://rpc-amoy.polygon.technology",
    ],
    "ethereum": [
        "https://eth.llamarpc.com",
        "https://ethereum-rpc.publicnode.com",
    ],
    "ethereum_sepolia": [
        "https://rpc.sepolia.org",
        "https://ethereum-sepolia-rpc.publicnode.com",
    ],
    "arbitrum": [
        "https://arb1.arbitrum.io/rpc",
        "https://arbitrum-one-rpc.publicnode.com",
    ],
    "arbitrum_sepolia": [
        "https://sepolia-rollup.arbitrum.io/rpc",
    ],
    "optimism": [
        "https://mainnet.optimism.io",
        "https://optimism-rpc.publicnode.com",
    ],
    "optimism_sepolia": [
        "https://sepolia.optimism.io",
    ],
}


class ChainRPCClient:
    """
    JSON-RPC client with fallback RPC providers and health checking.
    
    Features:
    - Multiple RPC endpoints per chain
    - Automatic failover on errors
    - Health-based endpoint selection
    - Latency-based prioritization
    """

    def __init__(self, rpc_url: str, chain: str = ""):
        self._chain = chain
        self._request_id = 0
        self._http_client = None
        
        # Initialize endpoints with primary and fallbacks
        self._endpoints: List[RPCEndpoint] = [
            RPCEndpoint(url=rpc_url, priority=0)
        ]
        
        # Add fallback endpoints
        if chain in FALLBACK_RPC_URLS:
            for i, url in enumerate(FALLBACK_RPC_URLS[chain]):
                if url != rpc_url:  # Don't duplicate primary
                    self._endpoints.append(RPCEndpoint(url=url, priority=i + 1))

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client
    
    def _get_healthy_endpoint(self) -> RPCEndpoint:
        """Get the best healthy endpoint based on priority and latency."""
        healthy = [e for e in self._endpoints if e.healthy]
        if not healthy:
            # All unhealthy, return lowest priority one and hope for the best
            return min(self._endpoints, key=lambda e: e.priority)
        
        # Sort by priority, then by latency
        return min(healthy, key=lambda e: (e.priority, e.latency_ms))

    async def _call(self, method: str, params: List[Any] = None) -> Any:
        """Make JSON-RPC call with automatic failover."""
        import time
        
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }
        
        # Try endpoints in order of health/priority
        last_error = None
        tried_endpoints = set()
        
        for attempt in range(len(self._endpoints)):
            endpoint = self._get_healthy_endpoint()
            
            # Skip if we've already tried this endpoint
            if endpoint.url in tried_endpoints:
                # Try any untried endpoint
                untried = [e for e in self._endpoints if e.url not in tried_endpoints]
                if not untried:
                    break
                endpoint = untried[0]
            
            tried_endpoints.add(endpoint.url)
            
            try:
                client = await self._get_client()
                start_time = time.time()
                
                response = await client.post(
                    endpoint.url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                latency_ms = (time.time() - start_time) * 1000
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    endpoint.mark_failure()
                    last_error = Exception(f"RPC error: {result['error']}")
                    continue
                
                # Success!
                endpoint.mark_success(latency_ms)
                return result.get("result")
                
            except Exception as e:
                endpoint.mark_failure()
                last_error = e
                logger.warning(f"RPC call to {endpoint.url} failed: {e}")
                continue
        
        # All endpoints failed
        raise last_error or Exception("All RPC endpoints failed")
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all endpoints."""
        results = {}
        
        for endpoint in self._endpoints:
            try:
                # Simple block number check
                await self._call_endpoint(endpoint, "eth_blockNumber", [])
                endpoint.healthy = True
                endpoint.failure_count = 0
                results[endpoint.url] = True
            except Exception:
                endpoint.healthy = False
                results[endpoint.url] = False
        
        return results
    
    async def _call_endpoint(self, endpoint: RPCEndpoint, method: str, params: List[Any]) -> Any:
        """Make a call to a specific endpoint."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        
        client = await self._get_client()
        response = await client.post(
            endpoint.url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            raise Exception(f"RPC error: {result['error']}")
        
        return result.get("result")
    
    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all endpoints."""
        return [
            {
                "url": e.url,
                "priority": e.priority,
                "healthy": e.healthy,
                "failure_count": e.failure_count,
                "latency_ms": e.latency_ms,
            }
            for e in self._endpoints
        ]

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        result = await self._call("eth_gasPrice")
        return int(result, 16)

    async def get_max_priority_fee(self) -> int:
        """Get max priority fee for EIP-1559."""
        try:
            result = await self._call("eth_maxPriorityFeePerGas")
            return int(result, 16)
        except Exception:
            # Fallback for chains that don't support this
            return 1_000_000_000  # 1 gwei

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas for a transaction."""
        result = await self._call("eth_estimateGas", [tx])
        return int(result, 16)

    async def get_nonce(self, address: str) -> int:
        """Get transaction count (nonce) for address."""
        result = await self._call("eth_getTransactionCount", [address, "pending"])
        return int(result, 16)

    async def get_balance(self, address: str) -> int:
        """Get ETH balance for address in wei."""
        result = await self._call("eth_getBalance", [address, "latest"])
        return int(result, 16)

    async def send_raw_transaction(self, signed_tx: str) -> str:
        """Broadcast signed transaction."""
        # Ensure hex prefix
        if not signed_tx.startswith("0x"):
            signed_tx = "0x" + signed_tx
        result = await self._call("eth_sendRawTransaction", [signed_tx])
        return result

    # Alias for backwards compatibility
    async def broadcast_transaction(self, signed_tx: str) -> str:
        """Broadcast signed transaction (alias for send_raw_transaction)."""
        return await self.send_raw_transaction(signed_tx)

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt."""
        return await self._call("eth_getTransactionReceipt", [tx_hash])

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self._call("eth_blockNumber")
        return int(result, 16)

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def encode_erc20_transfer(to_address: str, amount: int) -> bytes:
    """Encode ERC20 transfer function call."""
    # transfer(address,uint256) selector: 0xa9059cbb
    selector = bytes.fromhex("a9059cbb")
    
    # Pad address to 32 bytes
    to_bytes = bytes.fromhex(to_address[2:].lower().zfill(64))
    
    # Pad amount to 32 bytes
    amount_bytes = amount.to_bytes(32, "big")
    
    return selector + to_bytes + amount_bytes


class ChainExecutor:
    """
    Production-ready chain executor with MPC signing support.

    Features:
    - Multi-chain support (Base, Polygon, Ethereum)
    - MPC signing via Turnkey or Fireblocks
    - Gas estimation with EIP-1559 support
    - Transaction confirmation polling
    - Simulated mode for development
    - Pre-execution compliance checks (fail-closed)
    """

    # Confirmation requirements
    CONFIRMATIONS_REQUIRED = 1
    CONFIRMATION_TIMEOUT = 120  # seconds
    POLL_INTERVAL = 2  # seconds

    def __init__(self, settings: SardisSettings):
        self._settings = settings
        self._rpc_clients: Dict[str, ChainRPCClient] = {}
        self._mpc_signer: Optional[MPCSignerPort] = None
        self._simulated = settings.chain_mode == "simulated"

        # Compliance services (fail-closed: None means block all)
        self._compliance_engine = None
        self._sanctions_service = None
        self._init_compliance()

        # Initialize MPC signer based on settings
        if not self._simulated:
            self._init_mpc_signer()

    def _init_compliance(self):
        """Initialize compliance services for pre-execution checks."""
        try:
            from sardis_compliance import ComplianceEngine, create_sanctions_service

            self._compliance_engine = ComplianceEngine(self._settings)

            # Initialize sanctions service from environment
            elliptic_api_key = os.getenv("ELLIPTIC_API_KEY")
            elliptic_api_secret = os.getenv("ELLIPTIC_API_SECRET")
            self._sanctions_service = create_sanctions_service(
                api_key=elliptic_api_key,
                api_secret=elliptic_api_secret,
            )
            logger.info("Compliance services initialized successfully")
        except ImportError:
            logger.warning("sardis_compliance not available, compliance checks will fail-closed")
        except Exception as e:
            logger.error(f"Failed to initialize compliance services: {e}")

    def _init_mpc_signer(self):
        """Initialize MPC signer based on configuration."""
        mpc_config = self._settings.mpc

        # Local EOA signer for MVP (no MPC dependency)
        eoa_private_key = os.getenv("SARDIS_EOA_PRIVATE_KEY", "")
        eoa_address = os.getenv("SARDIS_EOA_ADDRESS", "")
        if mpc_config.name == "local" or eoa_private_key:
            try:
                self._mpc_signer = LocalAccountSigner(private_key=eoa_private_key, address=eoa_address)
                logger.info("Initialized local EOA signer for chain execution")
                return
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Local signer initialization failed, falling back to simulated: {exc}")

        if mpc_config.name == "turnkey":
            self._mpc_signer = TurnkeyMPCSigner(
                api_base=mpc_config.api_base or "https://api.turnkey.com",
                organization_id=mpc_config.credential_id,
                api_public_key=os.getenv("TURNKEY_API_PUBLIC_KEY", ""),
                api_private_key=os.getenv("TURNKEY_API_PRIVATE_KEY", ""),
            )
        elif mpc_config.name == "fireblocks":
            # TODO: Implement Fireblocks signer
            logger.warning("Fireblocks not yet implemented, using simulated")
            self._mpc_signer = SimulatedMPCSigner()
        else:
            self._mpc_signer = SimulatedMPCSigner()

    def _get_rpc_client(self, chain: str) -> ChainRPCClient:
        """Get or create RPC client for chain."""
        if chain not in self._rpc_clients:
            config = CHAIN_CONFIGS.get(chain)
            if not config:
                raise ValueError(f"Unknown chain: {chain}")
            
            # Check for custom RPC URL in settings
            rpc_url = config["rpc_url"]
            for chain_config in self._settings.chains:
                if chain_config.name == chain and chain_config.rpc_url:
                    rpc_url = chain_config.rpc_url
                    break
            
            self._rpc_clients[chain] = ChainRPCClient(rpc_url, chain=chain)
        
        return self._rpc_clients[chain]

    async def estimate_gas(self, mandate: PaymentMandate) -> GasEstimate:
        """Estimate gas for a payment mandate."""
        chain = mandate.chain or "base_sepolia"
        rpc = self._get_rpc_client(chain)
        from_address = None
        if not self._simulated and self._mpc_signer:
            try:
                from_address = await self._mpc_signer.get_address(mandate.subject, chain)
            except Exception:  # noqa: BLE001
                from_address = None
        
        # Get token contract address
        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        token_address = token_addresses.get(mandate.token, "")
        
        if not token_address:
            raise ValueError(f"Token {mandate.token} not supported on {chain}")
        
        # Encode transfer data
        amount_minor = int(mandate.amount_minor)
        transfer_data = encode_erc20_transfer(mandate.destination, amount_minor)
        
        # Estimate gas
        tx_params = {
            "to": token_address,
            "data": "0x" + transfer_data.hex(),
        }
        if from_address:
            tx_params["from"] = from_address
        
        try:
            gas_limit = await rpc.estimate_gas(tx_params)
            gas_limit = int(gas_limit * 1.2)  # Add 20% buffer
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}, using default")
            gas_limit = 100000
        
        # Get gas prices
        gas_price = await rpc.get_gas_price()
        max_priority_fee = await rpc.get_max_priority_fee()
        max_fee = gas_price + max_priority_fee
        
        estimated_cost = gas_limit * max_fee
        
        return GasEstimate(
            gas_limit=gas_limit,
            gas_price_gwei=Decimal(gas_price) / Decimal(10**9),
            max_fee_gwei=Decimal(max_fee) / Decimal(10**9),
            max_priority_fee_gwei=Decimal(max_priority_fee) / Decimal(10**9),
            estimated_cost_wei=estimated_cost,
        )

    async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt:
        """
        Execute a payment mandate on-chain.

        IMPORTANT: This method enforces a fail-closed compliance policy.
        Transactions are ONLY executed if:
        1. Compliance preflight check passes
        2. Sanctions screening passes for destination address

        In simulated mode, returns a mock receipt (compliance still checked).
        In live mode, signs and broadcasts the transaction.

        Raises:
            ComplianceError: If compliance check fails
            SanctionsError: If destination is sanctioned
        """
        chain = mandate.chain or "base_sepolia"
        audit_anchor = f"merkle::{mandate.audit_hash}"

        # === PRE-EXECUTION COMPLIANCE GATE (FAIL-CLOSED) ===

        # Step 1: Run compliance preflight check
        await self._check_compliance_preflight(mandate)

        # Step 2: Run sanctions screening on destination
        await self._check_sanctions(mandate.destination, chain)

        # === COMPLIANCE PASSED - PROCEED WITH EXECUTION ===

        if self._simulated:
            # Simulated mode - return mock receipt
            tx_hash = f"0x{secrets.token_hex(32)}"
            logger.info(f"[SIMULATED] Payment {mandate.mandate_id} -> {tx_hash}")
            return ChainReceipt(
                tx_hash=tx_hash,
                chain=chain,
                block_number=0,
                audit_anchor=audit_anchor,
            )

        # Live mode - execute real transaction
        return await self._execute_live_payment(mandate, chain, audit_anchor)

    async def _check_compliance_preflight(self, mandate: PaymentMandate) -> None:
        """
        Run compliance preflight check. Fail-closed policy.

        Raises:
            RuntimeError: If compliance check fails or service unavailable
        """
        if self._compliance_engine is None:
            # Fail-closed: no compliance service = block all
            logger.error(f"Compliance service unavailable, blocking mandate {mandate.mandate_id}")
            raise RuntimeError("Compliance service unavailable - transaction blocked (fail-closed policy)")

        result = self._compliance_engine.preflight(mandate)

        if not result.allowed:
            logger.warning(
                f"Compliance check FAILED for mandate {mandate.mandate_id}: "
                f"reason={result.reason}, rule={result.rule_id}"
            )
            raise RuntimeError(
                f"Compliance check failed: {result.reason} (rule: {result.rule_id})"
            )

        logger.info(f"Compliance check PASSED for mandate {mandate.mandate_id}")

    async def _check_sanctions(self, address: str, chain: str) -> None:
        """
        Run sanctions screening on an address. Fail-closed policy.

        Raises:
            RuntimeError: If address is sanctioned or service unavailable
        """
        if self._sanctions_service is None:
            # Fail-closed: no sanctions service = block all
            logger.error(f"Sanctions service unavailable, blocking address {address}")
            raise RuntimeError("Sanctions service unavailable - transaction blocked (fail-closed policy)")

        result = await self._sanctions_service.screen_address(address, chain)

        if result.should_block:
            logger.warning(
                f"Sanctions check BLOCKED address {address}: "
                f"risk={result.risk_level}, sanctioned={result.is_sanctioned}, "
                f"reason={result.reason}"
            )
            raise RuntimeError(
                f"Sanctions check failed: address {address} is blocked "
                f"(risk: {result.risk_level}, reason: {result.reason})"
            )

        logger.info(f"Sanctions check PASSED for address {address} (risk: {result.risk_level})")

    async def _execute_live_payment(
        self,
        mandate: PaymentMandate,
        chain: str,
        audit_anchor: str,
    ) -> ChainReceipt:
        """Execute a live payment on-chain."""
        rpc = self._get_rpc_client(chain)
        if not self._mpc_signer:
            raise RuntimeError("No signer configured. Provide SARDIS_EOA_PRIVATE_KEY or configure MPC.")
        
        # Get token contract address
        token_addresses = STABLECOIN_ADDRESSES.get(chain, {})
        token_address = token_addresses.get(mandate.token, "")
        
        if not token_address:
            raise ValueError(f"Token {mandate.token} not supported on {chain}")
        
        # Encode transfer data
        amount_minor = int(mandate.amount_minor)
        transfer_data = encode_erc20_transfer(mandate.destination, amount_minor)
        
        # Get gas estimates
        gas_estimate = await self.estimate_gas(mandate)
        
        # Get sender address and nonce
        wallet_id = mandate.subject  # Use subject as wallet ID
        sender_address = await self._mpc_signer.get_address(wallet_id, chain)
        nonce = await rpc.get_nonce(sender_address)
        
        # Build transaction request
        tx_request = TransactionRequest(
            chain=chain,
            to_address=token_address,
            value=0,
            data=transfer_data,
            gas_limit=gas_estimate.gas_limit,
            max_fee_per_gas=int(gas_estimate.max_fee_gwei * 10**9),
            max_priority_fee_per_gas=int(gas_estimate.max_priority_fee_gwei * 10**9),
            nonce=nonce,
        )
        
        # Sign transaction via MPC
        logger.info(f"Signing transaction for mandate {mandate.mandate_id}")
        signed_tx = await self._mpc_signer.sign_transaction(wallet_id, tx_request)
        
        # Broadcast transaction
        logger.info(f"Broadcasting transaction for mandate {mandate.mandate_id}")
        tx_hash = await rpc.send_raw_transaction(signed_tx)
        
        logger.info(f"Transaction submitted: {tx_hash}")
        
        # Wait for confirmation
        receipt = await self._wait_for_confirmation(rpc, tx_hash, chain)
        
        return ChainReceipt(
            tx_hash=tx_hash,
            chain=chain,
            block_number=int(receipt.get("blockNumber", "0x0"), 16) if isinstance(receipt.get("blockNumber"), str) else receipt.get("blockNumber", 0),
            audit_anchor=audit_anchor,
        )

    async def _wait_for_confirmation(
        self,
        rpc: ChainRPCClient,
        tx_hash: str,
        chain: str,
    ) -> Dict[str, Any]:
        """Wait for transaction confirmation."""
        chain_config = CHAIN_CONFIGS.get(chain, {})
        block_time = chain_config.get("block_time", 2)
        
        start_time = asyncio.get_event_loop().time()
        timeout = self.CONFIRMATION_TIMEOUT
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Transaction {tx_hash} not confirmed after {timeout}s")
            
            receipt = await rpc.get_transaction_receipt(tx_hash)
            
            if receipt:
                # Check if transaction succeeded
                status = int(receipt.get("status", "0x0"), 16)
                if status == 0:
                    raise Exception(f"Transaction {tx_hash} failed on-chain")
                
                # Check confirmations
                tx_block = int(receipt.get("blockNumber", "0x0"), 16)
                current_block = await rpc.get_block_number()
                confirmations = current_block - tx_block + 1
                
                if confirmations >= self.CONFIRMATIONS_REQUIRED:
                    logger.info(f"Transaction {tx_hash} confirmed with {confirmations} confirmations")
                    return receipt
                
                logger.debug(f"Transaction {tx_hash} has {confirmations} confirmations, waiting for {self.CONFIRMATIONS_REQUIRED}")
            
            await asyncio.sleep(self.POLL_INTERVAL)

    async def get_transaction_status(self, tx_hash: str, chain: str) -> TransactionStatus:
        """Get the status of a transaction."""
        rpc = self._get_rpc_client(chain)
        
        receipt = await rpc.get_transaction_receipt(tx_hash)
        
        if not receipt:
            return TransactionStatus.PENDING
        
        status = int(receipt.get("status", "0x0"), 16)
        if status == 0:
            return TransactionStatus.FAILED
        
        tx_block = int(receipt.get("blockNumber", "0x0"), 16)
        current_block = await rpc.get_block_number()
        confirmations = current_block - tx_block + 1
        
        if confirmations >= self.CONFIRMATIONS_REQUIRED:
            return TransactionStatus.CONFIRMED
        
        return TransactionStatus.CONFIRMING

    async def close(self):
        """Close all connections."""
        for client in self._rpc_clients.values():
            await client.close()
        
        if hasattr(self._mpc_signer, "close"):
            await self._mpc_signer.close()
