"""
Transaction simulation and gas estimation.

Features:
- Pre-execution transaction simulation via eth_call
- Comprehensive gas estimation with safety margins
- Revert reason extraction
- EIP-1559 gas price calculation
- Gas spike protection integration
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from .config import GasEstimationConfig, TransactionSimulationConfig, get_config

logger = logging.getLogger(__name__)


class SimulationResult(str, Enum):
    """Result of transaction simulation."""
    SUCCESS = "success"
    REVERTED = "reverted"
    OUT_OF_GAS = "out_of_gas"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_NONCE = "invalid_nonce"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class SimulationOutput:
    """Output from transaction simulation."""
    result: SimulationResult
    return_data: Optional[str] = None  # Hex return data
    gas_used: Optional[int] = None
    revert_reason: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        """Check if simulation was successful."""
        return self.result == SimulationResult.SUCCESS

    @property
    def will_succeed(self) -> bool:
        """Check if the real transaction is likely to succeed."""
        return self.result == SimulationResult.SUCCESS


@dataclass
class GasEstimation:
    """Comprehensive gas estimation result."""
    gas_limit: int
    base_fee_gwei: Decimal
    priority_fee_gwei: Decimal
    max_fee_gwei: Decimal
    estimated_cost_wei: int
    estimated_cost_eth: Decimal
    estimated_cost_usd: Optional[Decimal] = None

    # Raw values in wei
    base_fee_wei: int = 0
    priority_fee_wei: int = 0
    max_fee_wei: int = 0

    # Safety margins applied
    gas_buffer_percent: int = 20
    base_fee_buffer_percent: int = 25

    # Price context
    eth_price_usd: Optional[Decimal] = None
    is_gas_price_capped: bool = False
    original_max_fee_gwei: Optional[Decimal] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gas_limit": self.gas_limit,
            "base_fee_gwei": float(self.base_fee_gwei),
            "priority_fee_gwei": float(self.priority_fee_gwei),
            "max_fee_gwei": float(self.max_fee_gwei),
            "estimated_cost_eth": float(self.estimated_cost_eth),
            "estimated_cost_usd": float(self.estimated_cost_usd) if self.estimated_cost_usd else None,
            "gas_buffer_percent": self.gas_buffer_percent,
            "is_gas_price_capped": self.is_gas_price_capped,
        }


class SimulationError(Exception):
    """Error during transaction simulation."""

    def __init__(
        self,
        message: str,
        simulation_output: Optional[SimulationOutput] = None,
    ):
        self.simulation_output = simulation_output
        super().__init__(message)


class GasEstimationError(Exception):
    """Error during gas estimation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class TransactionSimulator:
    """
    Transaction simulator for pre-execution validation.

    SECURITY: Simulation prevents:
    - Executing transactions that will fail (wasting gas)
    - Unexpected contract behavior
    - Revert conditions

    Uses eth_call to simulate transaction execution without actually
    submitting to the blockchain.
    """

    def __init__(
        self,
        config: Optional[TransactionSimulationConfig] = None,
    ):
        self._config = config or get_config().simulation

    async def simulate(
        self,
        rpc_client: Any,  # ProductionRPCClient
        tx_params: Dict[str, Any],
        block: str = "latest",
    ) -> SimulationOutput:
        """
        Simulate a transaction using eth_call.

        Args:
            rpc_client: RPC client
            tx_params: Transaction parameters (from, to, data, value, gas)
            block: Block number or tag for simulation

        Returns:
            SimulationOutput with result and details
        """
        if not self._config.enabled:
            logger.debug("Simulation disabled, skipping")
            return SimulationOutput(result=SimulationResult.SUCCESS)

        try:
            # Set timeout for simulation
            async with asyncio.timeout(self._config.timeout_seconds):
                return await self._execute_simulation(rpc_client, tx_params, block)

        except asyncio.TimeoutError:
            logger.warning(f"Simulation timed out after {self._config.timeout_seconds}s")
            if self._config.allow_simulation_timeout:
                return SimulationOutput(
                    result=SimulationResult.TIMEOUT,
                    error_message="Simulation timed out",
                )
            raise SimulationError(
                "Transaction simulation timed out",
                SimulationOutput(result=SimulationResult.TIMEOUT),
            )

    async def _execute_simulation(
        self,
        rpc_client: Any,
        tx_params: Dict[str, Any],
        block: str,
    ) -> SimulationOutput:
        """Execute the actual simulation."""
        try:
            # Prepare call parameters
            call_params = {
                "to": tx_params.get("to"),
                "data": tx_params.get("data") or tx_params.get("input", "0x"),
            }

            if tx_params.get("from"):
                call_params["from"] = tx_params["from"]
            if tx_params.get("value"):
                call_params["value"] = tx_params["value"]
            if tx_params.get("gas"):
                call_params["gas"] = tx_params["gas"]

            # Execute eth_call
            result = await rpc_client.eth_call(call_params, block)

            # Successful simulation
            return SimulationOutput(
                result=SimulationResult.SUCCESS,
                return_data=result,
            )

        except Exception as e:
            return self._parse_simulation_error(e)

    def _parse_simulation_error(self, error: Exception) -> SimulationOutput:
        """Parse simulation error and extract details."""
        error_str = str(error).lower()

        # Check for common revert patterns
        if "revert" in error_str or "execution reverted" in error_str:
            revert_reason = self._extract_revert_reason(str(error))
            return SimulationOutput(
                result=SimulationResult.REVERTED,
                revert_reason=revert_reason,
                error_message=str(error),
            )

        if "out of gas" in error_str or "gas required exceeds" in error_str:
            return SimulationOutput(
                result=SimulationResult.OUT_OF_GAS,
                error_message=str(error),
            )

        if "insufficient funds" in error_str or "insufficient balance" in error_str:
            return SimulationOutput(
                result=SimulationResult.INSUFFICIENT_FUNDS,
                error_message=str(error),
            )

        if "nonce" in error_str:
            return SimulationOutput(
                result=SimulationResult.INVALID_NONCE,
                error_message=str(error),
            )

        # Generic error
        return SimulationOutput(
            result=SimulationResult.ERROR,
            error_message=str(error),
        )

    def _extract_revert_reason(self, error_message: str) -> Optional[str]:
        """Extract human-readable revert reason from error message."""
        # Common patterns for revert reasons

        # Pattern: "execution reverted: <reason>"
        if "execution reverted:" in error_message.lower():
            idx = error_message.lower().find("execution reverted:")
            return error_message[idx + len("execution reverted:"):].strip()

        # Pattern: "Error(string)" selector (0x08c379a0)
        if "0x08c379a0" in error_message:
            return self._decode_error_string(error_message)

        # Pattern: "Panic(uint256)" selector (0x4e487b71)
        if "0x4e487b71" in error_message:
            return "Panic: assertion failed or arithmetic error"

        return None

    @staticmethod
    def _decode_error_string(error_message: str) -> str:
        """Decode ABI-encoded Error(string) revert reason.

        The ABI encoding for Error(string) is:
        - 4 bytes selector (0x08c379a0)
        - 32 bytes offset to string data
        - 32 bytes string length
        - N bytes UTF-8 string (padded to 32-byte boundary)
        """
        try:
            # Find the hex data after the selector
            idx = error_message.find("0x08c379a0")
            if idx == -1:
                return error_message
            hex_data = error_message[idx + 2:]  # skip "0x"
            # Remove any non-hex chars (quotes, whitespace, etc.)
            hex_data = "".join(c for c in hex_data if c in "0123456789abcdefABCDEF")
            if len(hex_data) < 8 + 64 + 64:  # selector + offset + length minimum
                return error_message
            # Skip selector (8 hex chars) and offset (64 hex chars)
            length_hex = hex_data[8 + 64 : 8 + 64 + 64]
            string_length = int(length_hex, 16)
            string_start = 8 + 64 + 64
            string_hex = hex_data[string_start : string_start + string_length * 2]
            return bytes.fromhex(string_hex).decode("utf-8", errors="replace")
        except Exception:
            return error_message

    async def simulate_and_validate(
        self,
        rpc_client: Any,
        tx_params: Dict[str, Any],
        block: str = "latest",
    ) -> SimulationOutput:
        """
        Simulate transaction and raise error if it would fail.

        Args:
            rpc_client: RPC client
            tx_params: Transaction parameters
            block: Block for simulation

        Returns:
            SimulationOutput if successful

        Raises:
            SimulationError: If simulation indicates transaction will fail
        """
        output = await self.simulate(rpc_client, tx_params, block)

        if not output.will_succeed and self._config.block_on_simulation_failure:
            raise SimulationError(
                f"Transaction simulation failed: {output.result.value} - "
                f"{output.revert_reason or output.error_message}",
                output,
            )

        return output


class GasEstimator:
    """
    Comprehensive gas estimator with safety margins.

    Features:
    - EIP-1559 support with base fee prediction
    - Configurable safety margins
    - Gas price spike detection
    - Cost estimation in USD
    """

    def __init__(
        self,
        config: Optional[GasEstimationConfig] = None,
    ):
        self._config = config or get_config().gas_estimation
        self._eth_price_cache: Optional[Decimal] = None
        self._eth_price_timestamp: float = 0
        self._price_cache_ttl: int = 300  # 5 minutes

    async def estimate(
        self,
        rpc_client: Any,  # ProductionRPCClient
        tx_params: Dict[str, Any],
        chain: str,
        apply_safety_margins: bool = True,
    ) -> GasEstimation:
        """
        Estimate gas for a transaction with safety margins.

        Args:
            rpc_client: RPC client
            tx_params: Transaction parameters
            chain: Chain name (for price caps)
            apply_safety_margins: Whether to add safety buffers

        Returns:
            GasEstimation with all details
        """
        # Estimate gas limit
        gas_limit = await self._estimate_gas_limit(rpc_client, tx_params)

        # Apply buffer
        if apply_safety_margins:
            buffered_gas_limit = int(
                gas_limit * (1 + self._config.gas_limit_buffer_percent / 100)
            )
        else:
            buffered_gas_limit = gas_limit

        # Get current gas prices
        base_fee_wei, priority_fee_wei = await self._get_gas_prices(rpc_client)

        # Apply base fee buffer for volatility
        if apply_safety_margins:
            buffered_base_fee_wei = int(
                base_fee_wei * (1 + self._config.base_fee_buffer_percent / 100)
            )
        else:
            buffered_base_fee_wei = base_fee_wei

        # Calculate max fee (base fee + priority fee)
        max_fee_wei = buffered_base_fee_wei + priority_fee_wei

        # Calculate cost
        estimated_cost_wei = buffered_gas_limit * max_fee_wei
        estimated_cost_eth = Decimal(estimated_cost_wei) / Decimal(10**18)

        # Get USD cost estimate
        eth_price = await self._get_eth_price()
        estimated_cost_usd = estimated_cost_eth * eth_price if eth_price else None

        return GasEstimation(
            gas_limit=buffered_gas_limit,
            base_fee_gwei=Decimal(buffered_base_fee_wei) / Decimal(10**9),
            priority_fee_gwei=Decimal(priority_fee_wei) / Decimal(10**9),
            max_fee_gwei=Decimal(max_fee_wei) / Decimal(10**9),
            estimated_cost_wei=estimated_cost_wei,
            estimated_cost_eth=estimated_cost_eth,
            estimated_cost_usd=estimated_cost_usd,
            base_fee_wei=buffered_base_fee_wei,
            priority_fee_wei=priority_fee_wei,
            max_fee_wei=max_fee_wei,
            gas_buffer_percent=self._config.gas_limit_buffer_percent if apply_safety_margins else 0,
            base_fee_buffer_percent=self._config.base_fee_buffer_percent if apply_safety_margins else 0,
            eth_price_usd=eth_price,
        )

    async def _estimate_gas_limit(
        self,
        rpc_client: Any,
        tx_params: Dict[str, Any],
    ) -> int:
        """Estimate gas limit for transaction."""
        try:
            # Prepare params for estimation
            estimate_params = {
                "to": tx_params.get("to"),
                "data": tx_params.get("data") or tx_params.get("input", "0x"),
            }

            if tx_params.get("from"):
                estimate_params["from"] = tx_params["from"]
            if tx_params.get("value"):
                estimate_params["value"] = tx_params["value"]

            gas_limit = await rpc_client.estimate_gas(estimate_params)

            logger.debug(f"Estimated gas limit: {gas_limit}")
            return gas_limit

        except Exception as e:
            logger.warning(
                f"Gas estimation failed, using default: {e}"
            )
            return self._config.default_gas_limit

    async def _get_gas_prices(
        self,
        rpc_client: Any,
    ) -> tuple[int, int]:
        """Get current base fee and priority fee."""
        # Try to get base fee from latest block
        base_fee_wei = await rpc_client.get_base_fee()

        if base_fee_wei is None:
            # Fallback to gas price
            gas_price = await rpc_client.get_gas_price()
            base_fee_wei = int(gas_price * 0.8)  # Assume 80% is base fee

        # Get priority fee
        try:
            priority_fee_wei = await rpc_client.get_max_priority_fee()
        except Exception:
            # Fallback to default
            priority_fee_wei = int(
                self._config.default_priority_fee_gwei * Decimal(10**9)
            )

        return base_fee_wei, priority_fee_wei

    async def _get_eth_price(self) -> Optional[Decimal]:
        """Get ETH price in USD with caching."""
        import time
        import os

        now = time.time()
        if (
            self._eth_price_cache is not None
            and now - self._eth_price_timestamp < self._price_cache_ttl
        ):
            return self._eth_price_cache

        # Try environment variable
        price_str = os.getenv("ETH_PRICE_USD")
        if price_str:
            try:
                self._eth_price_cache = Decimal(price_str)
                self._eth_price_timestamp = now
                return self._eth_price_cache
            except Exception:
                pass

        # Fallback to conservative estimate
        # In production, this should integrate with a price oracle
        self._eth_price_cache = Decimal("2000")
        self._eth_price_timestamp = now

        logger.debug(
            "Using fallback ETH price. Set ETH_PRICE_USD for accurate estimates."
        )
        return self._eth_price_cache

    def apply_gas_cap(
        self,
        estimation: GasEstimation,
        max_gas_price_gwei: Decimal,
        max_priority_fee_gwei: Decimal,
    ) -> GasEstimation:
        """
        Apply gas price caps to an estimation.

        Args:
            estimation: Original gas estimation
            max_gas_price_gwei: Maximum allowed max fee
            max_priority_fee_gwei: Maximum allowed priority fee

        Returns:
            New GasEstimation with capped values
        """
        capped_max_fee = min(estimation.max_fee_gwei, max_gas_price_gwei)
        capped_priority_fee = min(estimation.priority_fee_gwei, max_priority_fee_gwei)

        is_capped = (
            capped_max_fee < estimation.max_fee_gwei
            or capped_priority_fee < estimation.priority_fee_gwei
        )

        if is_capped:
            logger.info(
                f"Gas prices capped: max_fee {estimation.max_fee_gwei} -> {capped_max_fee}, "
                f"priority_fee {estimation.priority_fee_gwei} -> {capped_priority_fee}"
            )

        # Recalculate costs with capped values
        capped_max_fee_wei = int(capped_max_fee * Decimal(10**9))
        capped_priority_fee_wei = int(capped_priority_fee * Decimal(10**9))
        capped_cost_wei = estimation.gas_limit * capped_max_fee_wei
        capped_cost_eth = Decimal(capped_cost_wei) / Decimal(10**18)
        capped_cost_usd = (
            capped_cost_eth * estimation.eth_price_usd
            if estimation.eth_price_usd
            else None
        )

        return GasEstimation(
            gas_limit=estimation.gas_limit,
            base_fee_gwei=estimation.base_fee_gwei,
            priority_fee_gwei=capped_priority_fee,
            max_fee_gwei=capped_max_fee,
            estimated_cost_wei=capped_cost_wei,
            estimated_cost_eth=capped_cost_eth,
            estimated_cost_usd=capped_cost_usd,
            base_fee_wei=estimation.base_fee_wei,
            priority_fee_wei=capped_priority_fee_wei,
            max_fee_wei=capped_max_fee_wei,
            gas_buffer_percent=estimation.gas_buffer_percent,
            base_fee_buffer_percent=estimation.base_fee_buffer_percent,
            eth_price_usd=estimation.eth_price_usd,
            is_gas_price_capped=is_capped,
            original_max_fee_gwei=estimation.max_fee_gwei if is_capped else None,
        )


class SimulationAndEstimation:
    """
    Combined simulation and gas estimation service.

    Provides a single interface for pre-execution validation
    and comprehensive gas estimation.
    """

    def __init__(
        self,
        simulation_config: Optional[TransactionSimulationConfig] = None,
        gas_config: Optional[GasEstimationConfig] = None,
    ):
        self._simulator = TransactionSimulator(simulation_config)
        self._estimator = GasEstimator(gas_config)

    async def prepare_transaction(
        self,
        rpc_client: Any,
        tx_params: Dict[str, Any],
        chain: str,
        validate: bool = True,
    ) -> tuple[SimulationOutput, GasEstimation]:
        """
        Prepare a transaction by simulating and estimating gas.

        Args:
            rpc_client: RPC client
            tx_params: Transaction parameters
            chain: Chain name
            validate: Whether to validate simulation success

        Returns:
            Tuple of (SimulationOutput, GasEstimation)

        Raises:
            SimulationError: If simulation fails and validation enabled
        """
        # Run simulation and estimation in parallel
        simulation_task = self._simulator.simulate(rpc_client, tx_params)
        estimation_task = self._estimator.estimate(rpc_client, tx_params, chain)

        simulation_output, gas_estimation = await asyncio.gather(
            simulation_task,
            estimation_task,
        )

        # Validate simulation if requested
        if validate and not simulation_output.will_succeed:
            raise SimulationError(
                f"Transaction simulation failed: {simulation_output.result.value}",
                simulation_output,
            )

        return simulation_output, gas_estimation

    @property
    def simulator(self) -> TransactionSimulator:
        """Get the underlying simulator."""
        return self._simulator

    @property
    def estimator(self) -> GasEstimator:
        """Get the underlying estimator."""
        return self._estimator


# Global instance
_simulation_service: Optional[SimulationAndEstimation] = None


def get_simulation_service(
    simulation_config: Optional[TransactionSimulationConfig] = None,
    gas_config: Optional[GasEstimationConfig] = None,
) -> SimulationAndEstimation:
    """Get the global simulation and estimation service."""
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = SimulationAndEstimation(simulation_config, gas_config)
    return _simulation_service
