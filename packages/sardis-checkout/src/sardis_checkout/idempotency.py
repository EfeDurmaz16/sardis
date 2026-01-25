"""
Idempotency support for checkout operations.

This module provides idempotency key handling to ensure that duplicate
requests (e.g., due to network retries) result in the same response
without creating duplicate transactions.

Audit fix #2: Add idempotency key support for all operations.
"""
from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, TypeVar, Generic, Callable, Awaitable
from functools import wraps

from sardis_checkout.models import IdempotencyRecord

logger = logging.getLogger(__name__)

T = TypeVar("T")


class IdempotencyError(Exception):
    """Base exception for idempotency errors."""
    pass


class IdempotencyKeyConflict(IdempotencyError):
    """Raised when an idempotency key is reused with different parameters."""
    pass


class IdempotencyOperationInProgress(IdempotencyError):
    """Raised when an operation with the same key is already in progress."""
    pass


class IdempotencyStore(ABC):
    """Abstract interface for idempotency record storage."""

    @abstractmethod
    async def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        """Get an idempotency record by key."""
        pass

    @abstractmethod
    async def create(self, record: IdempotencyRecord) -> bool:
        """
        Create a new idempotency record.

        Returns True if created, False if key already exists.
        """
        pass

    @abstractmethod
    async def update(self, record: IdempotencyRecord) -> bool:
        """Update an existing idempotency record."""
        pass

    @abstractmethod
    async def delete(self, idempotency_key: str) -> bool:
        """Delete an idempotency record."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired idempotency records. Returns count of removed records."""
        pass


class InMemoryIdempotencyStore(IdempotencyStore):
    """
    In-memory idempotency store for development and testing.

    Note: This store is not suitable for production use in distributed
    environments. Use a persistent store like Redis or a database.
    """

    def __init__(self):
        self._records: Dict[str, IdempotencyRecord] = {}

    async def get(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        record = self._records.get(idempotency_key)
        if record and record.expires_at < datetime.utcnow():
            del self._records[idempotency_key]
            return None
        return record

    async def create(self, record: IdempotencyRecord) -> bool:
        if record.idempotency_key in self._records:
            existing = self._records[record.idempotency_key]
            if existing.expires_at >= datetime.utcnow():
                return False
        self._records[record.idempotency_key] = record
        return True

    async def update(self, record: IdempotencyRecord) -> bool:
        if record.idempotency_key not in self._records:
            return False
        self._records[record.idempotency_key] = record
        return True

    async def delete(self, idempotency_key: str) -> bool:
        if idempotency_key in self._records:
            del self._records[idempotency_key]
            return True
        return False

    async def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired_keys = [
            key for key, record in self._records.items()
            if record.expires_at < now
        ]
        for key in expired_keys:
            del self._records[key]
        return len(expired_keys)


class IdempotencyManager:
    """
    Manages idempotency for checkout operations.

    This manager ensures that operations with the same idempotency key:
    1. Return the same response if already completed
    2. Block concurrent duplicate requests
    3. Allow retries after failures

    Usage:
        manager = IdempotencyManager(store)

        # Check and execute with idempotency
        result = await manager.execute_idempotent(
            idempotency_key="key-123",
            operation="create_checkout",
            request_data={"amount": 100},
            execute_fn=lambda: create_checkout_impl(),
        )
    """

    def __init__(
        self,
        store: IdempotencyStore,
        default_ttl_hours: int = 24,
        lock_timeout_seconds: int = 60,
    ):
        self.store = store
        self.default_ttl_hours = default_ttl_hours
        self.lock_timeout_seconds = lock_timeout_seconds

    def _compute_request_hash(self, request_data: Dict[str, Any]) -> str:
        """Compute a hash of the request data for conflict detection."""
        # Sort keys for consistent hashing
        normalized = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def check_idempotency(
        self,
        idempotency_key: str,
        operation: str,
        request_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if an idempotent operation has already been completed.

        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name (e.g., "create_checkout")
            request_data: Request parameters for hash computation

        Returns:
            Cached response if operation was completed, None otherwise

        Raises:
            IdempotencyKeyConflict: If key was used with different parameters
            IdempotencyOperationInProgress: If operation is currently running
        """
        record = await self.store.get(idempotency_key)

        if record is None:
            return None

        # Verify request hash matches
        request_hash = self._compute_request_hash(request_data)
        if record.request_hash != request_hash:
            raise IdempotencyKeyConflict(
                f"Idempotency key '{idempotency_key}' was previously used with "
                f"different request parameters"
            )

        # Check if operation is in progress
        if record.status == "pending":
            # Check for stale locks
            lock_expiry = record.created_at + timedelta(seconds=self.lock_timeout_seconds)
            if datetime.utcnow() < lock_expiry:
                raise IdempotencyOperationInProgress(
                    f"Operation with idempotency key '{idempotency_key}' is in progress"
                )
            else:
                # Stale lock, allow retry
                logger.warning(
                    f"Releasing stale idempotency lock for key '{idempotency_key}'"
                )
                await self.store.delete(idempotency_key)
                return None

        # Return cached response for completed operations
        if record.status == "completed" and record.response is not None:
            logger.info(
                f"Returning cached response for idempotency key '{idempotency_key}'"
            )
            return record.response

        # Failed operations can be retried
        if record.status == "failed":
            await self.store.delete(idempotency_key)
            return None

        return None

    async def start_operation(
        self,
        idempotency_key: str,
        operation: str,
        request_data: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> IdempotencyRecord:
        """
        Start a new idempotent operation.

        Creates a pending record to lock the operation.
        """
        request_hash = self._compute_request_hash(request_data)

        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            operation=operation,
            request_hash=request_hash,
            status="pending",
            agent_id=agent_id,
            expires_at=datetime.utcnow() + timedelta(hours=self.default_ttl_hours),
        )

        if not await self.store.create(record):
            raise IdempotencyOperationInProgress(
                f"Could not acquire lock for idempotency key '{idempotency_key}'"
            )

        return record

    async def complete_operation(
        self,
        idempotency_key: str,
        response: Dict[str, Any],
        checkout_id: Optional[str] = None,
    ) -> None:
        """Mark an idempotent operation as completed with its response."""
        record = await self.store.get(idempotency_key)
        if record is None:
            logger.warning(
                f"Attempted to complete unknown idempotency key '{idempotency_key}'"
            )
            return

        record.status = "completed"
        record.response = response
        record.completed_at = datetime.utcnow()
        record.checkout_id = checkout_id

        await self.store.update(record)

    async def fail_operation(
        self,
        idempotency_key: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark an idempotent operation as failed."""
        record = await self.store.get(idempotency_key)
        if record is None:
            return

        record.status = "failed"
        record.completed_at = datetime.utcnow()
        if error_message:
            record.response = {"error": error_message}

        await self.store.update(record)

    async def execute_idempotent(
        self,
        idempotency_key: str,
        operation: str,
        request_data: Dict[str, Any],
        execute_fn: Callable[[], Awaitable[T]],
        serialize_fn: Optional[Callable[[T], Dict[str, Any]]] = None,
        agent_id: Optional[str] = None,
    ) -> tuple[T, bool]:
        """
        Execute an operation with idempotency guarantees.

        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name
            request_data: Request parameters
            execute_fn: Async function to execute the operation
            serialize_fn: Optional function to serialize result for caching
            agent_id: Optional agent ID for logging

        Returns:
            Tuple of (result, is_duplicate) where is_duplicate indicates
            if the result was returned from cache
        """
        # Check for existing result
        cached = await self.check_idempotency(idempotency_key, operation, request_data)
        if cached is not None:
            # Return cached result - caller needs to deserialize
            return cached, True  # type: ignore

        # Start new operation
        await self.start_operation(idempotency_key, operation, request_data, agent_id)

        try:
            # Execute the operation
            result = await execute_fn()

            # Serialize and cache the result
            if serialize_fn:
                serialized = serialize_fn(result)
            elif hasattr(result, "__dict__"):
                serialized = asdict(result) if hasattr(result, "__dataclass_fields__") else result.__dict__
            else:
                serialized = {"result": result}

            checkout_id = serialized.get("checkout_id")
            await self.complete_operation(idempotency_key, serialized, checkout_id)

            return result, False

        except Exception as e:
            await self.fail_operation(idempotency_key, str(e))
            raise


def idempotent(
    key_param: str = "idempotency_key",
    operation: Optional[str] = None,
):
    """
    Decorator to make an async method idempotent.

    Usage:
        @idempotent(key_param="idempotency_key", operation="create_checkout")
        async def create_checkout(self, request: CheckoutRequest) -> CheckoutResponse:
            ...

    The decorated method must be on a class that has an `idempotency_manager`
    attribute.
    """
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(self, *args, **kwargs) -> T:
            # Get idempotency key from kwargs or args
            idempotency_key = kwargs.get(key_param)

            # If no key, just execute normally
            if not idempotency_key:
                return await fn(self, *args, **kwargs)

            # Get idempotency manager
            manager: Optional[IdempotencyManager] = getattr(
                self, "idempotency_manager", None
            )
            if not manager:
                logger.warning(
                    "Idempotency key provided but no idempotency_manager available"
                )
                return await fn(self, *args, **kwargs)

            # Build request data for hashing
            request_data = dict(kwargs)
            for i, arg in enumerate(args):
                if hasattr(arg, "__dataclass_fields__"):
                    request_data[f"arg_{i}"] = asdict(arg)
                elif hasattr(arg, "__dict__"):
                    request_data[f"arg_{i}"] = arg.__dict__
                else:
                    request_data[f"arg_{i}"] = arg

            # Execute with idempotency
            op_name = operation or fn.__name__
            result, is_duplicate = await manager.execute_idempotent(
                idempotency_key=idempotency_key,
                operation=op_name,
                request_data=request_data,
                execute_fn=lambda: fn(self, *args, **kwargs),
            )

            return result

        return wrapper
    return decorator


def generate_idempotency_key(
    prefix: str,
    *components: Any,
) -> str:
    """
    Generate a deterministic idempotency key from components.

    Usage:
        key = generate_idempotency_key("checkout", agent_id, amount, timestamp)
    """
    parts = [str(prefix)]
    for comp in components:
        if comp is not None:
            parts.append(str(comp))

    combined = ":".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:32]
