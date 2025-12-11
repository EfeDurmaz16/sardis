"""
Off-ramp provider integration for stablecoin to fiat conversion.

Supports conversion from stablecoins (USDC, USDT) to fiat (USD)
for funding virtual cards.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OfframpStatus(str, Enum):
    """Status of an off-ramp transaction."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class OfframpProvider(str, Enum):
    """Supported off-ramp providers."""
    BRIDGE = "bridge"        # Bridge.xyz
    ZERO_HASH = "zero_hash"  # Zero Hash
    MOCK = "mock"            # For testing


@dataclass
class OfframpQuote:
    """A quote for converting stablecoin to fiat."""
    quote_id: str
    provider: OfframpProvider
    input_token: str
    input_amount_minor: int
    input_chain: str
    output_currency: str
    output_amount_cents: int
    exchange_rate: Decimal
    fee_cents: int
    expires_at: datetime
    
    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class OfframpTransaction:
    """An off-ramp transaction."""
    transaction_id: str
    quote_id: str
    provider: OfframpProvider
    input_token: str
    input_amount_minor: int
    input_chain: str
    input_tx_hash: Optional[str] = None
    output_currency: str = "USD"
    output_amount_cents: int = 0
    destination_account: str = ""  # Bank account or Lithic funding account
    status: OfframpStatus = OfframpStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    provider_reference: Optional[str] = None


class OfframpProviderBase(ABC):
    """Abstract base class for off-ramp providers."""
    
    @abstractmethod
    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str,
        output_currency: str = "USD",
    ) -> OfframpQuote:
        """Get a quote for converting stablecoin to fiat."""
        pass
    
    @abstractmethod
    async def execute_offramp(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
    ) -> OfframpTransaction:
        """Execute an off-ramp transaction."""
        pass
    
    @abstractmethod
    async def get_transaction_status(
        self,
        transaction_id: str,
    ) -> OfframpTransaction:
        """Get the status of an off-ramp transaction."""
        pass
    
    @abstractmethod
    async def get_deposit_address(
        self,
        chain: str,
        token: str,
    ) -> str:
        """Get the deposit address for a chain/token pair."""
        pass


class MockOfframpProvider(OfframpProviderBase):
    """Mock off-ramp provider for development/testing."""
    
    def __init__(self):
        self._transactions: Dict[str, OfframpTransaction] = {}
        self._quote_counter = 0
        self._tx_counter = 0
    
    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str,
        output_currency: str = "USD",
    ) -> OfframpQuote:
        """Get a mock quote."""
        import secrets
        from datetime import timedelta
        
        self._quote_counter += 1
        
        # Simulate 0.5% fee
        fee_bps = 50
        fee_amount = input_amount_minor * fee_bps // 10000
        output_amount = input_amount_minor - fee_amount
        
        return OfframpQuote(
            quote_id=f"mock_quote_{self._quote_counter}_{secrets.token_hex(4)}",
            provider=OfframpProvider.MOCK,
            input_token=input_token,
            input_amount_minor=input_amount_minor,
            input_chain=input_chain,
            output_currency=output_currency,
            output_amount_cents=output_amount,
            exchange_rate=Decimal("1.0"),
            fee_cents=fee_amount,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    
    async def execute_offramp(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
    ) -> OfframpTransaction:
        """Execute a mock off-ramp."""
        import secrets
        
        self._tx_counter += 1
        
        tx = OfframpTransaction(
            transaction_id=f"mock_tx_{self._tx_counter}_{secrets.token_hex(4)}",
            quote_id=quote.quote_id,
            provider=OfframpProvider.MOCK,
            input_token=quote.input_token,
            input_amount_minor=quote.input_amount_minor,
            input_chain=quote.input_chain,
            output_currency=quote.output_currency,
            output_amount_cents=quote.output_amount_cents,
            destination_account=destination_account,
            status=OfframpStatus.PROCESSING,
            provider_reference=f"mock_ref_{secrets.token_hex(8)}",
        )
        
        self._transactions[tx.transaction_id] = tx
        
        # Simulate immediate completion for mock
        asyncio.create_task(self._simulate_completion(tx.transaction_id))
        
        return tx
    
    async def _simulate_completion(self, transaction_id: str):
        """Simulate transaction completion after a delay."""
        await asyncio.sleep(2)
        tx = self._transactions.get(transaction_id)
        if tx:
            tx.status = OfframpStatus.COMPLETED
            tx.completed_at = datetime.now(timezone.utc)
    
    async def get_transaction_status(
        self,
        transaction_id: str,
    ) -> OfframpTransaction:
        """Get mock transaction status."""
        tx = self._transactions.get(transaction_id)
        if not tx:
            raise ValueError(f"Transaction not found: {transaction_id}")
        return tx
    
    async def get_deposit_address(
        self,
        chain: str,
        token: str,
    ) -> str:
        """Get a mock deposit address."""
        import secrets
        return f"0x{secrets.token_hex(20)}"


class BridgeOfframpProvider(OfframpProviderBase):
    """
    Bridge.xyz off-ramp provider integration.
    
    Bridge provides stablecoin to fiat conversion with direct 
    bank account or card funding capabilities.
    """
    
    API_BASE = "https://api.bridge.xyz"
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        environment: str = "sandbox",
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._environment = environment
        self._http_client = None
        
        if environment == "sandbox":
            self.API_BASE = "https://api.sandbox.bridge.xyz"
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client
    
    def _sign_request(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate HMAC signature for API request."""
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self._api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature
    
    async def _make_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Bridge API."""
        import json
        
        client = await self._get_client()
        timestamp = str(int(time.time()))
        body_str = json.dumps(body) if body else ""
        
        signature = self._sign_request(timestamp, method, path, body_str)
        
        headers = {
            "Content-Type": "application/json",
            "Api-Key": self._api_key,
            "Api-Timestamp": timestamp,
            "Api-Signature": signature,
        }
        
        url = f"{self.API_BASE}{path}"
        
        if method == "GET":
            response = await client.get(url, headers=headers)
        else:
            response = await client.post(url, content=body_str, headers=headers)
        
        response.raise_for_status()
        return response.json()
    
    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str,
        output_currency: str = "USD",
    ) -> OfframpQuote:
        """Get a quote from Bridge."""
        from datetime import timedelta
        
        result = await self._make_request(
            "POST",
            "/v0/quotes",
            {
                "source_currency": input_token.upper(),
                "source_amount": str(input_amount_minor / 1_000_000),  # Convert to decimal
                "source_chain": input_chain,
                "destination_currency": output_currency,
                "destination_payment_rail": "ach",  # Or "wire" for larger amounts
            },
        )
        
        return OfframpQuote(
            quote_id=result["quote_id"],
            provider=OfframpProvider.BRIDGE,
            input_token=input_token,
            input_amount_minor=input_amount_minor,
            input_chain=input_chain,
            output_currency=output_currency,
            output_amount_cents=int(float(result["destination_amount"]) * 100),
            exchange_rate=Decimal(result.get("exchange_rate", "1.0")),
            fee_cents=int(float(result.get("fee", "0")) * 100),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    
    async def execute_offramp(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
    ) -> OfframpTransaction:
        """Execute off-ramp via Bridge."""
        result = await self._make_request(
            "POST",
            "/v0/transfers",
            {
                "quote_id": quote.quote_id,
                "source_address": source_address,
                "destination_account_id": destination_account,
            },
        )
        
        return OfframpTransaction(
            transaction_id=result["transfer_id"],
            quote_id=quote.quote_id,
            provider=OfframpProvider.BRIDGE,
            input_token=quote.input_token,
            input_amount_minor=quote.input_amount_minor,
            input_chain=quote.input_chain,
            output_currency=quote.output_currency,
            output_amount_cents=quote.output_amount_cents,
            destination_account=destination_account,
            status=OfframpStatus.PROCESSING,
            provider_reference=result.get("reference"),
        )
    
    async def get_transaction_status(
        self,
        transaction_id: str,
    ) -> OfframpTransaction:
        """Get transaction status from Bridge."""
        result = await self._make_request("GET", f"/v0/transfers/{transaction_id}")
        
        status_map = {
            "pending": OfframpStatus.PENDING,
            "processing": OfframpStatus.PROCESSING,
            "completed": OfframpStatus.COMPLETED,
            "failed": OfframpStatus.FAILED,
        }
        
        return OfframpTransaction(
            transaction_id=result["transfer_id"],
            quote_id=result.get("quote_id", ""),
            provider=OfframpProvider.BRIDGE,
            input_token=result.get("source_currency", "USDC"),
            input_amount_minor=int(float(result.get("source_amount", "0")) * 1_000_000),
            input_chain=result.get("source_chain", ""),
            output_currency=result.get("destination_currency", "USD"),
            output_amount_cents=int(float(result.get("destination_amount", "0")) * 100),
            destination_account=result.get("destination_account_id", ""),
            status=status_map.get(result["status"], OfframpStatus.PENDING),
            provider_reference=result.get("reference"),
        )
    
    async def get_deposit_address(
        self,
        chain: str,
        token: str,
    ) -> str:
        """Get Bridge deposit address."""
        result = await self._make_request(
            "POST",
            "/v0/deposit-addresses",
            {
                "chain": chain,
                "currency": token.upper(),
            },
        )
        return result["address"]
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class OfframpService:
    """
    High-level off-ramp service for Sardis.
    
    Manages off-ramp operations with automatic provider selection
    and status tracking.
    """
    
    def __init__(
        self,
        provider: Optional[OfframpProviderBase] = None,
    ):
        self._provider = provider or MockOfframpProvider()
        self._transactions: Dict[str, OfframpTransaction] = {}
    
    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str = "base",
        output_currency: str = "USD",
    ) -> OfframpQuote:
        """Get a quote for off-ramp."""
        return await self._provider.get_quote(
            input_token=input_token,
            input_amount_minor=input_amount_minor,
            input_chain=input_chain,
            output_currency=output_currency,
        )
    
    async def execute(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
    ) -> OfframpTransaction:
        """Execute off-ramp and track transaction."""
        tx = await self._provider.execute_offramp(
            quote=quote,
            source_address=source_address,
            destination_account=destination_account,
        )
        self._transactions[tx.transaction_id] = tx
        return tx
    
    async def get_status(self, transaction_id: str) -> OfframpTransaction:
        """Get transaction status."""
        if transaction_id in self._transactions:
            # Refresh from provider
            tx = await self._provider.get_transaction_status(transaction_id)
            self._transactions[transaction_id] = tx
            return tx
        return await self._provider.get_transaction_status(transaction_id)
    
    async def wait_for_completion(
        self,
        transaction_id: str,
        timeout_seconds: float = 300,
        poll_interval: float = 5,
    ) -> OfframpTransaction:
        """Wait for transaction to complete."""
        import time
        
        start = time.time()
        while time.time() - start < timeout_seconds:
            tx = await self.get_status(transaction_id)
            
            if tx.status == OfframpStatus.COMPLETED:
                return tx
            elif tx.status == OfframpStatus.FAILED:
                raise Exception(f"Off-ramp failed: {tx.failure_reason}")
            
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Off-ramp timed out after {timeout_seconds}s")
    
    def get_pending_transactions(self) -> List[OfframpTransaction]:
        """Get all pending transactions."""
        return [
            tx for tx in self._transactions.values()
            if tx.status in (OfframpStatus.PENDING, OfframpStatus.PROCESSING)
        ]


