"""
Comprehensive logging utilities for blockchain operations.

Features:
- Structured logging for all blockchain operations
- Transaction lifecycle logging
- RPC call metrics
- Audit trail support
- Sensitive data masking
- Performance metrics
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from .config import LoggingConfig, get_config

logger = logging.getLogger(__name__)

# Type variable for decorator
F = TypeVar("F", bound=Callable)


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationType(str, Enum):
    """Types of blockchain operations."""
    RPC_CALL = "rpc_call"
    TRANSACTION_SUBMIT = "transaction_submit"
    TRANSACTION_CONFIRM = "transaction_confirm"
    GAS_ESTIMATION = "gas_estimation"
    SIMULATION = "simulation"
    NONCE_MANAGEMENT = "nonce_management"
    CONFIRMATION_TRACKING = "confirmation_tracking"
    REORG_DETECTION = "reorg_detection"
    HEALTH_CHECK = "health_check"
    ENDPOINT_FAILOVER = "endpoint_failover"


@dataclass
class OperationContext:
    """Context for a blockchain operation."""
    operation_id: str
    operation_type: OperationType
    chain: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True, error: Optional[str] = None) -> None:
        """Mark operation as complete."""
        self.completed_at = datetime.now(timezone.utc)
        self.duration_ms = (
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "chain": self.chain,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class RPCCallLog:
    """Log entry for an RPC call."""
    method: str
    endpoint_url: str
    chain: str
    request_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "method": self.method,
            "endpoint_url": self._mask_url(self.endpoint_url),
            "chain": self.chain,
            "request_id": self.request_id,
            "started_at": self.started_at.isoformat(),
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URL (like API keys)."""
        # Remove any query parameters that might contain keys
        if "?" in url:
            base = url.split("?")[0]
            return f"{base}?<params_masked>"
        return url


@dataclass
class TransactionLog:
    """Log entry for a transaction."""
    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    value_wei: int
    nonce: int
    gas_limit: int
    max_fee_gwei: Decimal
    priority_fee_gwei: Decimal
    submitted_at: datetime
    status: str = "pending"
    block_number: Optional[int] = None
    confirmations: int = 0
    gas_used: Optional[int] = None
    effective_gas_price: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self, mask_addresses: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        from_addr = self._mask_address(self.from_address) if mask_addresses else self.from_address
        to_addr = self._mask_address(self.to_address) if mask_addresses else self.to_address

        return {
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "from_address": from_addr,
            "to_address": to_addr,
            "value_wei": self.value_wei,
            "nonce": self.nonce,
            "gas_limit": self.gas_limit,
            "max_fee_gwei": float(self.max_fee_gwei),
            "priority_fee_gwei": float(self.priority_fee_gwei),
            "submitted_at": self.submitted_at.isoformat(),
            "status": self.status,
            "block_number": self.block_number,
            "confirmations": self.confirmations,
            "gas_used": self.gas_used,
            "error": self.error,
        }

    @staticmethod
    def _mask_address(address: str) -> str:
        """Mask middle portion of address for privacy."""
        if len(address) < 10:
            return address
        return f"{address[:6]}...{address[-4:]}"


class ChainLogger:
    """
    Comprehensive logger for blockchain operations.

    Provides structured logging with:
    - Operation context tracking
    - Transaction lifecycle logging
    - RPC call metrics
    - Audit trail support
    - Performance tracking
    """

    def __init__(
        self,
        name: str = "sardis_chain",
        config: Optional[LoggingConfig] = None,
    ):
        self._logger = logging.getLogger(name)
        self._config = config or get_config().logging
        self._operation_counter = 0

        # Metrics collection
        self._rpc_calls: List[RPCCallLog] = []
        self._transactions: Dict[str, TransactionLog] = {}
        self._max_history = 1000

    def _generate_operation_id(self) -> str:
        """Generate a unique operation ID."""
        self._operation_counter += 1
        timestamp = int(time.time() * 1000)
        return f"op_{timestamp}_{self._operation_counter}"

    def _get_level(self, level_str: str) -> int:
        """Convert level string to logging level."""
        return getattr(logging, level_str.upper(), logging.INFO)

    def _format_log_data(self, data: Dict[str, Any]) -> str:
        """Format data for logging."""
        # Convert Decimals to floats for JSON serialization
        def convert(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            return obj

        formatted = {k: convert(v) for k, v in data.items()}
        return json.dumps(formatted, default=str)

    @asynccontextmanager
    async def operation_context(
        self,
        operation_type: OperationType,
        chain: str,
        **metadata,
    ):
        """
        Context manager for tracking an operation.

        Usage:
            async with logger.operation_context(OperationType.RPC_CALL, "base") as ctx:
                # Do operation
                ctx.metadata["result"] = result
        """
        ctx = OperationContext(
            operation_id=self._generate_operation_id(),
            operation_type=operation_type,
            chain=chain,
            metadata=metadata,
        )

        self._logger.debug(
            f"Starting {operation_type.value} on {chain}",
            extra={"operation": ctx.to_dict()},
        )

        try:
            yield ctx
            ctx.complete(success=True)

        except Exception as e:
            ctx.complete(success=False, error=str(e))
            raise

        finally:
            level = (
                self._get_level(self._config.error_level)
                if not ctx.success
                else self._get_level(self._config.transaction_level)
            )
            self._logger.log(
                level,
                f"Completed {operation_type.value} on {chain} in {ctx.duration_ms:.0f}ms "
                f"(success={ctx.success})",
                extra={"operation": ctx.to_dict()},
            )

    def log_rpc_call(
        self,
        method: str,
        endpoint_url: str,
        chain: str,
        request_id: int,
        duration_ms: float,
        success: bool,
        error_code: Optional[int] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """Log an RPC call."""
        if not self._config.log_rpc_latency:
            return

        log_entry = RPCCallLog(
            method=method,
            endpoint_url=endpoint_url,
            chain=chain,
            request_id=request_id,
            started_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count,
        )

        # Store for metrics
        self._rpc_calls.append(log_entry)
        if len(self._rpc_calls) > self._max_history:
            self._rpc_calls = self._rpc_calls[-self._max_history:]

        level = (
            self._get_level(self._config.error_level)
            if not success
            else self._get_level(self._config.rpc_call_level)
        )

        self._logger.log(
            level,
            f"RPC {method} to {chain} in {duration_ms:.0f}ms (success={success})",
            extra={"rpc_call": log_entry.to_dict()},
        )

    def log_transaction_submitted(
        self,
        tx_hash: str,
        chain: str,
        from_address: str,
        to_address: str,
        value_wei: int,
        nonce: int,
        gas_limit: int,
        max_fee_gwei: Decimal,
        priority_fee_gwei: Decimal,
    ) -> None:
        """Log transaction submission."""
        log_entry = TransactionLog(
            tx_hash=tx_hash,
            chain=chain,
            from_address=from_address,
            to_address=to_address,
            value_wei=value_wei,
            nonce=nonce,
            gas_limit=gas_limit,
            max_fee_gwei=max_fee_gwei,
            priority_fee_gwei=priority_fee_gwei,
            submitted_at=datetime.now(timezone.utc),
            status="submitted",
        )

        self._transactions[tx_hash] = log_entry

        self._logger.log(
            self._get_level(self._config.transaction_level),
            f"Transaction submitted: {tx_hash} on {chain}",
            extra={"transaction": log_entry.to_dict(self._config.mask_addresses)},
        )

        # Audit log
        if self._config.audit_log_enabled:
            self._write_audit_log("transaction_submitted", log_entry.to_dict())

    def log_transaction_confirmed(
        self,
        tx_hash: str,
        block_number: int,
        confirmations: int,
        gas_used: int,
        effective_gas_price: Optional[int] = None,
    ) -> None:
        """Log transaction confirmation."""
        if tx_hash in self._transactions:
            log_entry = self._transactions[tx_hash]
            log_entry.status = "confirmed"
            log_entry.block_number = block_number
            log_entry.confirmations = confirmations
            log_entry.gas_used = gas_used
            log_entry.effective_gas_price = effective_gas_price
        else:
            log_entry = None

        self._logger.log(
            self._get_level(self._config.confirmation_level),
            f"Transaction confirmed: {tx_hash} in block {block_number} "
            f"with {confirmations} confirmations",
            extra={"transaction": log_entry.to_dict(self._config.mask_addresses) if log_entry else {}},
        )

        # Audit log
        if self._config.audit_log_enabled:
            self._write_audit_log("transaction_confirmed", {
                "tx_hash": tx_hash,
                "block_number": block_number,
                "confirmations": confirmations,
                "gas_used": gas_used,
            })

    def log_transaction_failed(
        self,
        tx_hash: str,
        error: str,
        revert_reason: Optional[str] = None,
    ) -> None:
        """Log transaction failure."""
        if tx_hash in self._transactions:
            log_entry = self._transactions[tx_hash]
            log_entry.status = "failed"
            log_entry.error = error
        else:
            log_entry = None

        self._logger.log(
            self._get_level(self._config.error_level),
            f"Transaction failed: {tx_hash} - {error}"
            + (f" (revert: {revert_reason})" if revert_reason else ""),
            extra={"transaction": log_entry.to_dict(self._config.mask_addresses) if log_entry else {}},
        )

        # Audit log
        if self._config.audit_log_enabled:
            self._write_audit_log("transaction_failed", {
                "tx_hash": tx_hash,
                "error": error,
                "revert_reason": revert_reason,
            })

    def log_endpoint_failover(
        self,
        chain: str,
        failed_endpoint: str,
        new_endpoint: str,
        error: str,
    ) -> None:
        """Log RPC endpoint failover."""
        if not self._config.log_endpoint_health:
            return

        self._logger.warning(
            f"Endpoint failover on {chain}: {failed_endpoint} -> {new_endpoint}",
            extra={
                "failover": {
                    "chain": chain,
                    "failed_endpoint": failed_endpoint,
                    "new_endpoint": new_endpoint,
                    "error": error,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    def log_reorg_detected(
        self,
        chain: str,
        depth: int,
        severity: str,
        affected_txs: List[str],
    ) -> None:
        """Log chain reorganization detection."""
        level = (
            logging.CRITICAL if severity == "critical"
            else logging.ERROR if severity == "deep"
            else logging.WARNING
        )

        self._logger.log(
            level,
            f"Chain reorg detected on {chain}: depth={depth}, severity={severity}, "
            f"affected_txs={len(affected_txs)}",
            extra={
                "reorg": {
                    "chain": chain,
                    "depth": depth,
                    "severity": severity,
                    "affected_transactions": affected_txs,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

        # Always audit log reorgs
        if self._config.audit_log_enabled:
            self._write_audit_log("reorg_detected", {
                "chain": chain,
                "depth": depth,
                "severity": severity,
                "affected_transactions": affected_txs,
            })

    def log_gas_estimation(
        self,
        chain: str,
        gas_limit: int,
        max_fee_gwei: Decimal,
        priority_fee_gwei: Decimal,
        estimated_cost_usd: Optional[Decimal] = None,
        is_capped: bool = False,
    ) -> None:
        """Log gas estimation."""
        if not self._config.log_gas_prices:
            return

        self._logger.debug(
            f"Gas estimation for {chain}: limit={gas_limit}, "
            f"max_fee={max_fee_gwei:.2f} gwei, "
            f"priority_fee={priority_fee_gwei:.2f} gwei"
            + (f", cost=${estimated_cost_usd:.2f}" if estimated_cost_usd else "")
            + (" (CAPPED)" if is_capped else ""),
            extra={
                "gas_estimation": {
                    "chain": chain,
                    "gas_limit": gas_limit,
                    "max_fee_gwei": float(max_fee_gwei),
                    "priority_fee_gwei": float(priority_fee_gwei),
                    "estimated_cost_usd": float(estimated_cost_usd) if estimated_cost_usd else None,
                    "is_capped": is_capped,
                }
            },
        )

    def log_nonce_management(
        self,
        address: str,
        action: str,
        nonce: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log nonce management operation."""
        if not self._config.log_nonces:
            return

        masked_address = (
            self._mask_address(address)
            if self._config.mask_addresses
            else address
        )

        self._logger.debug(
            f"Nonce {action} for {masked_address}: {nonce}",
            extra={
                "nonce_management": {
                    "address": masked_address,
                    "action": action,
                    "nonce": nonce,
                    "details": details or {},
                }
            },
        )

    @staticmethod
    def _mask_address(address: str) -> str:
        """Mask middle portion of address for privacy."""
        if len(address) < 10:
            return address
        return f"{address[:6]}...{address[-4:]}"

    def _write_audit_log(self, event_type: str, data: Dict[str, Any]) -> None:
        """Write to audit log."""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }

        if self._config.audit_log_path:
            # Write to file
            try:
                with open(self._config.audit_log_path, "a") as f:
                    f.write(json.dumps(audit_entry, default=str) + "\n")
            except Exception as e:
                self._logger.error(f"Failed to write audit log: {e}")
        else:
            # Use default logger at INFO level
            self._logger.info(
                f"AUDIT: {event_type}",
                extra={"audit": audit_entry},
            )

    def get_rpc_metrics(self) -> Dict[str, Any]:
        """Get RPC call metrics."""
        if not self._rpc_calls:
            return {"total_calls": 0}

        successful = [c for c in self._rpc_calls if c.success]
        failed = [c for c in self._rpc_calls if not c.success]

        latencies = [c.duration_ms for c in successful if c.duration_ms]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return {
            "total_calls": len(self._rpc_calls),
            "successful_calls": len(successful),
            "failed_calls": len(failed),
            "success_rate": len(successful) / len(self._rpc_calls) if self._rpc_calls else 0,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
        }

    def get_transaction_metrics(self) -> Dict[str, Any]:
        """Get transaction metrics."""
        if not self._transactions:
            return {"total_transactions": 0}

        statuses = {}
        for tx in self._transactions.values():
            statuses[tx.status] = statuses.get(tx.status, 0) + 1

        return {
            "total_transactions": len(self._transactions),
            "status_breakdown": statuses,
        }


# Global logger instance
_chain_logger: Optional[ChainLogger] = None


def get_chain_logger(
    name: str = "sardis_chain",
    config: Optional[LoggingConfig] = None,
) -> ChainLogger:
    """Get the global chain logger instance."""
    global _chain_logger
    if _chain_logger is None:
        _chain_logger = ChainLogger(name, config)
    return _chain_logger


def log_operation(operation_type: OperationType, chain: str = "unknown"):
    """
    Decorator for logging blockchain operations.

    Usage:
        @log_operation(OperationType.RPC_CALL, "base")
        async def my_function():
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_chain_logger()
            async with logger.operation_context(operation_type, chain):
                return await func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    json_format: bool = False,
) -> None:
    """
    Set up logging configuration.

    Args:
        level: Log level
        format_string: Custom format string
        json_format: Use JSON formatting
    """
    if format_string is None:
        if json_format:
            format_string = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
        else:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
    )

    # Set specific loggers
    logging.getLogger("sardis_chain").setLevel(getattr(logging, level.upper()))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
