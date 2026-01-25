"""
Production-grade RPC client with failover and health checking.

Features:
- Multi-RPC endpoint support with automatic failover
- Chain ID validation on connection (security)
- Health-based endpoint selection
- Latency-based prioritization
- Request timeout handling
- Comprehensive error handling and logging
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    ChainConfig,
    RPCEndpointConfig,
    get_chain_config,
    validate_chain_id,
    CHAIN_ID_MAP,
)

logger = logging.getLogger(__name__)


class EndpointStatus(str, Enum):
    """Health status of an RPC endpoint."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # High latency but working
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class EndpointHealth:
    """Health tracking for an RPC endpoint."""
    url: str
    status: EndpointStatus = EndpointStatus.UNKNOWN
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_requests: int = 0
    total_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    last_error: Optional[str] = None
    chain_id_verified: bool = False

    # Thresholds
    max_consecutive_failures: int = 3
    degraded_latency_ms: float = 5000.0  # 5 seconds
    health_check_interval_seconds: float = 60.0

    def record_success(self, latency_ms: float) -> None:
        """Record a successful request."""
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.total_requests += 1
        self.last_success = datetime.now(timezone.utc)
        self.last_latency_ms = latency_ms

        # Update rolling average
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            # Exponential moving average
            self.avg_latency_ms = 0.9 * self.avg_latency_ms + 0.1 * latency_ms

        # Update status
        if latency_ms > self.degraded_latency_ms:
            self.status = EndpointStatus.DEGRADED
        else:
            self.status = EndpointStatus.HEALTHY

    def record_failure(self, error: str) -> None:
        """Record a failed request."""
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.total_requests += 1
        self.total_failures += 1
        self.last_failure = datetime.now(timezone.utc)
        self.last_error = error

        if self.consecutive_failures >= self.max_consecutive_failures:
            self.status = EndpointStatus.UNHEALTHY

    def needs_health_check(self) -> bool:
        """Check if endpoint needs a health check."""
        if self.status == EndpointStatus.UNKNOWN:
            return True
        if self.status == EndpointStatus.UNHEALTHY:
            if self.last_failure is None:
                return True
            elapsed = (datetime.now(timezone.utc) - self.last_failure).total_seconds()
            return elapsed >= self.health_check_interval_seconds
        return False

    def get_priority_score(self, base_priority: int) -> float:
        """
        Calculate priority score for endpoint selection.
        Lower score = higher priority.
        """
        score = float(base_priority * 100)

        # Heavily penalize unhealthy endpoints
        if self.status == EndpointStatus.UNHEALTHY:
            score += 10000
        elif self.status == EndpointStatus.DEGRADED:
            score += 1000
        elif self.status == EndpointStatus.UNKNOWN:
            score += 500

        # Add latency component (normalized)
        score += self.avg_latency_ms / 10.0

        # Penalize recent failures
        score += self.consecutive_failures * 100

        return score


class ChainIDMismatchError(Exception):
    """Raised when chain ID doesn't match expected value."""

    def __init__(self, chain: str, expected: int, received: int):
        self.chain = chain
        self.expected = expected
        self.received = received
        super().__init__(
            f"Chain ID mismatch for {chain}: expected {expected}, got {received}. "
            f"SECURITY: This could indicate connecting to wrong network!"
        )


class RPCError(Exception):
    """Base exception for RPC errors."""

    def __init__(self, message: str, code: Optional[int] = None, data: Any = None):
        self.code = code
        self.data = data
        super().__init__(message)


class AllEndpointsFailedError(Exception):
    """Raised when all RPC endpoints have failed."""

    def __init__(self, chain: str, errors: List[Tuple[str, str]]):
        self.chain = chain
        self.errors = errors
        error_summary = "; ".join([f"{url}: {err}" for url, err in errors[:3]])
        super().__init__(
            f"All RPC endpoints failed for {chain}. Errors: {error_summary}"
        )


class ProductionRPCClient:
    """
    Production-grade JSON-RPC client with failover and health checking.

    Features:
    - Multi-endpoint support with automatic failover
    - Chain ID validation on first connection (security)
    - Health-based endpoint selection
    - Latency tracking and prioritization
    - Comprehensive error handling
    - Request timeout handling
    """

    def __init__(
        self,
        chain: str,
        chain_config: Optional[ChainConfig] = None,
        validate_chain_id_on_connect: bool = True,
    ):
        self._chain = chain
        self._config = chain_config or get_chain_config(chain)
        self._validate_chain_id = validate_chain_id_on_connect
        self._request_id = 0
        self._http_client = None
        self._connected = False
        self._verified_chain_id: Optional[int] = None

        # Initialize endpoint health tracking
        self._endpoints: List[Tuple[RPCEndpointConfig, EndpointHealth]] = []
        for endpoint_config in self._config.rpc_endpoints:
            health = EndpointHealth(
                url=endpoint_config.url,
                max_consecutive_failures=endpoint_config.max_consecutive_failures,
                health_check_interval_seconds=endpoint_config.health_check_interval_seconds,
            )
            self._endpoints.append((endpoint_config, health))

        if not self._endpoints:
            raise ValueError(f"No RPC endpoints configured for chain {chain}")

        logger.info(
            f"Initialized RPC client for {chain} with {len(self._endpoints)} endpoints"
        )

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self._config.rpc_endpoints[0].timeout_seconds if self._config.rpc_endpoints else 30.0,
                    connect=10.0,
                ),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http_client

    async def connect(self) -> None:
        """
        Connect to RPC and validate chain ID.

        SECURITY: Chain ID validation prevents connecting to wrong networks
        which could result in loss of funds.
        """
        if self._connected:
            return

        if self._validate_chain_id:
            chain_id = await self._fetch_chain_id()
            expected_chain_id = self._config.chain_id

            if chain_id != expected_chain_id:
                raise ChainIDMismatchError(
                    chain=self._chain,
                    expected=expected_chain_id,
                    received=chain_id,
                )

            self._verified_chain_id = chain_id
            logger.info(
                f"Chain ID validated for {self._chain}: {chain_id}"
            )

        self._connected = True

    async def _fetch_chain_id(self) -> int:
        """Fetch chain ID from RPC."""
        result = await self._call_internal("eth_chainId", [], skip_chain_validation=True)
        return int(result, 16)

    def _select_endpoint(self) -> Tuple[RPCEndpointConfig, EndpointHealth]:
        """Select the best endpoint based on health and priority."""
        # Calculate scores for all endpoints
        scored = [
            (config, health, health.get_priority_score(config.priority))
            for config, health in self._endpoints
        ]

        # Sort by score (lower is better)
        scored.sort(key=lambda x: x[2])

        # Return best endpoint
        config, health, _ = scored[0]
        return config, health

    async def _call_internal(
        self,
        method: str,
        params: List[Any],
        skip_chain_validation: bool = False,
    ) -> Any:
        """Internal call implementation with endpoint selection and failover."""
        if not skip_chain_validation and self._validate_chain_id and not self._connected:
            await self.connect()

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        errors: List[Tuple[str, str]] = []
        tried_endpoints: set = set()

        # Try endpoints in priority order with failover
        max_attempts = len(self._endpoints)
        for attempt in range(max_attempts):
            config, health = self._select_endpoint()

            # Skip already tried endpoints
            if config.url in tried_endpoints:
                # Find next untried endpoint
                for c, h in self._endpoints:
                    if c.url not in tried_endpoints:
                        config, health = c, h
                        break
                else:
                    break  # All endpoints tried

            tried_endpoints.add(config.url)
            start_time = time.time()

            try:
                client = await self._get_client()
                response = await client.post(
                    config.url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=config.timeout_seconds,
                )

                latency_ms = (time.time() - start_time) * 1000
                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    error_msg = str(result["error"])
                    health.record_failure(error_msg)
                    errors.append((config.url, error_msg))

                    # Check if error is retryable
                    error_code = result["error"].get("code", 0)
                    if error_code in (-32000, -32005):  # Server errors, rate limits
                        logger.warning(
                            f"RPC error from {config.url}: {error_msg}, trying next endpoint"
                        )
                        continue

                    # Non-retryable errors
                    raise RPCError(
                        message=result["error"].get("message", error_msg),
                        code=error_code,
                        data=result["error"].get("data"),
                    )

                # Success!
                health.record_success(latency_ms)
                health.chain_id_verified = True

                logger.debug(
                    f"RPC call {method} to {config.url} succeeded in {latency_ms:.0f}ms"
                )

                return result.get("result")

            except RPCError:
                raise  # Re-raise non-retryable RPC errors
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                health.record_failure(error_msg)
                errors.append((config.url, error_msg))

                logger.warning(
                    f"RPC call to {config.url} failed after {latency_ms:.0f}ms: {e}"
                )
                continue

        # All endpoints failed
        raise AllEndpointsFailedError(chain=self._chain, errors=errors)

    async def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """
        Make a JSON-RPC call with automatic failover.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            RPC result

        Raises:
            ChainIDMismatchError: If chain ID validation fails
            RPCError: If RPC returns an error
            AllEndpointsFailedError: If all endpoints fail
        """
        return await self._call_internal(method, params or [])

    async def get_chain_id(self) -> int:
        """Get chain ID (cached after first fetch)."""
        if self._verified_chain_id is not None:
            return self._verified_chain_id

        chain_id = await self._fetch_chain_id()
        self._verified_chain_id = chain_id
        return chain_id

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self.call("eth_blockNumber")
        return int(result, 16)

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        result = await self.call("eth_gasPrice")
        return int(result, 16)

    async def get_max_priority_fee(self) -> int:
        """Get max priority fee for EIP-1559."""
        try:
            result = await self.call("eth_maxPriorityFeePerGas")
            return int(result, 16)
        except (RPCError, AllEndpointsFailedError):
            # Fallback for chains that don't support this
            return 1_500_000_000  # 1.5 gwei

    async def get_base_fee(self) -> Optional[int]:
        """Get current base fee from latest block."""
        try:
            block = await self.call("eth_getBlockByNumber", ["latest", False])
            if block and "baseFeePerGas" in block:
                return int(block["baseFeePerGas"], 16)
            return None
        except Exception:
            return None

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas for a transaction."""
        result = await self.call("eth_estimateGas", [tx])
        return int(result, 16)

    async def get_nonce(self, address: str, block: str = "pending") -> int:
        """Get transaction count (nonce) for address."""
        result = await self.call("eth_getTransactionCount", [address, block])
        return int(result, 16)

    async def get_balance(self, address: str, block: str = "latest") -> int:
        """Get native token balance for address in wei."""
        result = await self.call("eth_getBalance", [address, block])
        return int(result, 16)

    async def send_raw_transaction(self, signed_tx: str) -> str:
        """Broadcast signed transaction."""
        if not signed_tx.startswith("0x"):
            signed_tx = "0x" + signed_tx
        return await self.call("eth_sendRawTransaction", [signed_tx])

    async def get_transaction_receipt(
        self, tx_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get transaction receipt."""
        return await self.call("eth_getTransactionReceipt", [tx_hash])

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction by hash."""
        return await self.call("eth_getTransactionByHash", [tx_hash])

    async def get_block(
        self,
        block_number: int | str,
        include_transactions: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get block by number."""
        if isinstance(block_number, int):
            block_number = hex(block_number)
        return await self.call("eth_getBlockByNumber", [block_number, include_transactions])

    async def get_logs(
        self,
        filter_params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get logs matching filter."""
        return await self.call("eth_getLogs", [filter_params]) or []

    async def eth_call(
        self,
        tx: Dict[str, Any],
        block: str = "latest",
    ) -> str:
        """Execute a call without creating a transaction."""
        return await self.call("eth_call", [tx, block])

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all endpoints.

        Returns:
            Dictionary with endpoint health status
        """
        results = {
            "chain": self._chain,
            "chain_id_verified": self._verified_chain_id is not None,
            "endpoints": [],
        }

        for config, health in self._endpoints:
            try:
                start_time = time.time()
                client = await self._get_client()
                response = await client.post(
                    config.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_blockNumber",
                        "params": [],
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10.0,
                )
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        health.record_success(latency_ms)
                        results["endpoints"].append({
                            "url": config.url,
                            "status": health.status.value,
                            "latency_ms": latency_ms,
                            "healthy": True,
                        })
                        continue

                health.record_failure(f"Status {response.status_code}")
                results["endpoints"].append({
                    "url": config.url,
                    "status": health.status.value,
                    "healthy": False,
                    "error": f"Status {response.status_code}",
                })

            except Exception as e:
                health.record_failure(str(e))
                results["endpoints"].append({
                    "url": config.url,
                    "status": health.status.value,
                    "healthy": False,
                    "error": str(e),
                })

        return results

    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all endpoints."""
        return [
            {
                "url": config.url,
                "priority": config.priority,
                "status": health.status.value,
                "consecutive_failures": health.consecutive_failures,
                "total_requests": health.total_requests,
                "total_failures": health.total_failures,
                "avg_latency_ms": round(health.avg_latency_ms, 2),
                "last_latency_ms": round(health.last_latency_ms, 2),
                "chain_id_verified": health.chain_id_verified,
                "last_error": health.last_error,
            }
            for config, health in self._endpoints
        ]

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    async def __aenter__(self) -> "ProductionRPCClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Factory function for creating RPC clients
_rpc_clients: Dict[str, ProductionRPCClient] = {}


def get_rpc_client(
    chain: str,
    chain_config: Optional[ChainConfig] = None,
    validate_chain_id: bool = True,
) -> ProductionRPCClient:
    """
    Get or create an RPC client for a chain.

    Args:
        chain: Chain name
        chain_config: Optional chain configuration
        validate_chain_id: Whether to validate chain ID on connect

    Returns:
        ProductionRPCClient instance
    """
    if chain not in _rpc_clients:
        _rpc_clients[chain] = ProductionRPCClient(
            chain=chain,
            chain_config=chain_config,
            validate_chain_id_on_connect=validate_chain_id,
        )
    return _rpc_clients[chain]


async def close_all_clients() -> None:
    """Close all RPC clients."""
    for client in _rpc_clients.values():
        await client.close()
    _rpc_clients.clear()
