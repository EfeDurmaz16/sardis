"""
Bulk operations support for the Sardis SDK.

This module provides utilities for executing multiple operations efficiently,
with support for batching, concurrency control, and error handling.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from .models.errors import SardisError

# Type variables
T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type


class OperationStatus(str, Enum):
    """Status of a bulk operation item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class OperationResult(Generic[T, R]):
    """Result of a single operation within a bulk operation.

    Attributes:
        input: The input that was processed
        output: The output/result (if successful)
        status: Status of the operation
        error: Error details (if failed)
        duration_ms: Time taken for the operation
        index: Original index in the batch
    """

    input: T
    output: Optional[R] = None
    status: OperationStatus = OperationStatus.PENDING
    error: Optional[SardisError] = None
    duration_ms: float = 0
    index: int = 0

    @property
    def is_success(self) -> bool:
        """Check if operation succeeded."""
        return self.status == OperationStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if operation failed."""
        return self.status == OperationStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "index": self.index,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
        }
        if self.output is not None:
            result["output"] = self.output
        if self.error is not None:
            result["error"] = self.error.to_dict()
        return result


@dataclass
class BulkOperationSummary:
    """Summary of a bulk operation.

    Attributes:
        total: Total number of operations
        successful: Number of successful operations
        failed: Number of failed operations
        skipped: Number of skipped operations
        total_duration_ms: Total time for all operations
        started_at: When the bulk operation started
        completed_at: When the bulk operation completed
    """

    total: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_ms: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all operations completed (success or fail)."""
        return self.successful + self.failed + self.skipped == self.total

    @property
    def has_failures(self) -> bool:
        """Check if any operations failed."""
        return self.failed > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": f"{self.success_rate:.2f}%",
            "total_duration_ms": self.total_duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class BulkOperationResult(Generic[T, R]):
    """Complete result of a bulk operation.

    Attributes:
        results: List of individual operation results
        summary: Summary statistics
    """

    results: List[OperationResult[T, R]] = field(default_factory=list)
    summary: BulkOperationSummary = field(default_factory=BulkOperationSummary)

    @property
    def successful_results(self) -> List[OperationResult[T, R]]:
        """Get only successful results."""
        return [r for r in self.results if r.is_success]

    @property
    def failed_results(self) -> List[OperationResult[T, R]]:
        """Get only failed results."""
        return [r for r in self.results if r.is_failed]

    @property
    def outputs(self) -> List[R]:
        """Get all successful outputs."""
        return [r.output for r in self.results if r.output is not None]

    @property
    def errors(self) -> List[Tuple[int, SardisError]]:
        """Get all errors with their indices."""
        return [(r.index, r.error) for r in self.results if r.error is not None]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary.to_dict(),
        }


@dataclass
class BulkConfig:
    """Configuration for bulk operations.

    Attributes:
        batch_size: Number of operations per batch
        max_concurrency: Maximum concurrent operations
        stop_on_error: Whether to stop on first error
        retry_failed: Whether to retry failed operations
        max_retries: Maximum retries for failed operations
        delay_between_batches: Delay between batches in seconds
    """

    batch_size: int = 100
    max_concurrency: int = 10
    stop_on_error: bool = False
    retry_failed: bool = True
    max_retries: int = 2
    delay_between_batches: float = 0.1


class AsyncBulkExecutor(Generic[T, R]):
    """Executor for async bulk operations.

    This class manages the execution of multiple async operations with
    configurable batching, concurrency, and error handling.

    Example:
        ```python
        async def create_agent(name: str) -> Agent:
            return await client.agents.create(name=name)

        executor = AsyncBulkExecutor(
            operation=create_agent,
            config=BulkConfig(batch_size=50, max_concurrency=5),
        )

        names = ["agent1", "agent2", "agent3", ...]
        result = await executor.execute(names)

        print(f"Created {result.summary.successful} agents")
        if result.summary.has_failures:
            for idx, error in result.errors:
                print(f"Failed to create {names[idx]}: {error}")
        ```
    """

    def __init__(
        self,
        operation: Callable[[T], Awaitable[R]],
        config: Optional[BulkConfig] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_item_complete: Optional[Callable[[OperationResult[T, R]], None]] = None,
    ):
        """Initialize the bulk executor.

        Args:
            operation: Async function to execute for each item
            config: Bulk operation configuration
            on_progress: Optional callback for progress updates (completed, total)
            on_item_complete: Optional callback when each item completes
        """
        self._operation = operation
        self._config = config or BulkConfig()
        self._on_progress = on_progress
        self._on_item_complete = on_item_complete
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def execute(self, items: Sequence[T]) -> BulkOperationResult[T, R]:
        """Execute the bulk operation on all items.

        Args:
            items: Sequence of items to process

        Returns:
            BulkOperationResult with all results and summary
        """
        import time

        start_time = datetime.utcnow()
        start_monotonic = time.monotonic()

        # Initialize semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self._config.max_concurrency)

        # Create operation results
        results: List[OperationResult[T, R]] = [
            OperationResult(input=item, index=i) for i, item in enumerate(items)
        ]

        # Process in batches
        total = len(items)
        completed = 0

        for batch_start in range(0, total, self._config.batch_size):
            batch_end = min(batch_start + self._config.batch_size, total)
            batch_results = results[batch_start:batch_end]

            # Execute batch concurrently
            tasks = [
                self._execute_single(result) for result in batch_results
            ]
            await asyncio.gather(*tasks)

            completed += len(batch_results)

            # Check for stop on error
            if self._config.stop_on_error:
                if any(r.is_failed for r in batch_results):
                    # Mark remaining as skipped
                    for r in results[batch_end:]:
                        r.status = OperationStatus.SKIPPED
                    break

            # Progress callback
            if self._on_progress:
                self._on_progress(completed, total)

            # Delay between batches
            if batch_end < total and self._config.delay_between_batches > 0:
                await asyncio.sleep(self._config.delay_between_batches)

        # Calculate summary
        end_time = datetime.utcnow()
        total_duration_ms = (time.monotonic() - start_monotonic) * 1000

        summary = BulkOperationSummary(
            total=total,
            successful=sum(1 for r in results if r.is_success),
            failed=sum(1 for r in results if r.is_failed),
            skipped=sum(1 for r in results if r.status == OperationStatus.SKIPPED),
            total_duration_ms=total_duration_ms,
            started_at=start_time,
            completed_at=end_time,
        )

        return BulkOperationResult(results=results, summary=summary)

    async def _execute_single(
        self,
        result: OperationResult[T, R],
        retry_count: int = 0,
    ) -> None:
        """Execute a single operation with concurrency control."""
        import time

        async with self._semaphore:
            result.status = OperationStatus.IN_PROGRESS
            start_time = time.monotonic()

            try:
                output = await self._operation(result.input)
                result.output = output
                result.status = OperationStatus.SUCCESS
            except SardisError as e:
                # Check if we should retry
                if (
                    self._config.retry_failed
                    and e.retryable
                    and retry_count < self._config.max_retries
                ):
                    await self._execute_single(result, retry_count + 1)
                    return

                result.error = e
                result.status = OperationStatus.FAILED
            except Exception as e:
                result.error = SardisError(str(e))
                result.status = OperationStatus.FAILED

            result.duration_ms = (time.monotonic() - start_time) * 1000

            # Item complete callback
            if self._on_item_complete:
                self._on_item_complete(result)


class SyncBulkExecutor(Generic[T, R]):
    """Executor for sync bulk operations.

    This class manages the execution of multiple operations sequentially
    with configurable batching and error handling.

    Example:
        ```python
        def create_agent(name: str) -> Agent:
            return client.agents.create(name=name)

        executor = SyncBulkExecutor(
            operation=create_agent,
            config=BulkConfig(batch_size=50),
        )

        names = ["agent1", "agent2", "agent3", ...]
        result = executor.execute(names)

        print(f"Created {result.summary.successful} agents")
        ```
    """

    def __init__(
        self,
        operation: Callable[[T], R],
        config: Optional[BulkConfig] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_item_complete: Optional[Callable[[OperationResult[T, R]], None]] = None,
    ):
        """Initialize the bulk executor.

        Args:
            operation: Function to execute for each item
            config: Bulk operation configuration
            on_progress: Optional callback for progress updates (completed, total)
            on_item_complete: Optional callback when each item completes
        """
        self._operation = operation
        self._config = config or BulkConfig()
        self._on_progress = on_progress
        self._on_item_complete = on_item_complete

    def execute(self, items: Sequence[T]) -> BulkOperationResult[T, R]:
        """Execute the bulk operation on all items.

        Args:
            items: Sequence of items to process

        Returns:
            BulkOperationResult with all results and summary
        """
        import time

        start_time = datetime.utcnow()
        start_monotonic = time.monotonic()

        # Create operation results
        results: List[OperationResult[T, R]] = [
            OperationResult(input=item, index=i) for i, item in enumerate(items)
        ]

        # Process items
        total = len(items)
        completed = 0
        stop = False

        for result in results:
            if stop:
                result.status = OperationStatus.SKIPPED
                continue

            self._execute_single(result)
            completed += 1

            # Check for stop on error
            if self._config.stop_on_error and result.is_failed:
                stop = True

            # Progress callback
            if self._on_progress:
                self._on_progress(completed, total)

            # Item complete callback
            if self._on_item_complete:
                self._on_item_complete(result)

        # Calculate summary
        end_time = datetime.utcnow()
        total_duration_ms = (time.monotonic() - start_monotonic) * 1000

        summary = BulkOperationSummary(
            total=total,
            successful=sum(1 for r in results if r.is_success),
            failed=sum(1 for r in results if r.is_failed),
            skipped=sum(1 for r in results if r.status == OperationStatus.SKIPPED),
            total_duration_ms=total_duration_ms,
            started_at=start_time,
            completed_at=end_time,
        )

        return BulkOperationResult(results=results, summary=summary)

    def _execute_single(
        self,
        result: OperationResult[T, R],
        retry_count: int = 0,
    ) -> None:
        """Execute a single operation."""
        import time

        result.status = OperationStatus.IN_PROGRESS
        start_time = time.monotonic()

        try:
            output = self._operation(result.input)
            result.output = output
            result.status = OperationStatus.SUCCESS
        except SardisError as e:
            # Check if we should retry
            if (
                self._config.retry_failed
                and e.retryable
                and retry_count < self._config.max_retries
            ):
                self._execute_single(result, retry_count + 1)
                return

            result.error = e
            result.status = OperationStatus.FAILED
        except Exception as e:
            result.error = SardisError(str(e))
            result.status = OperationStatus.FAILED

        result.duration_ms = (time.monotonic() - start_time) * 1000


async def bulk_execute_async(
    operation: Callable[[T], Awaitable[R]],
    items: Sequence[T],
    config: Optional[BulkConfig] = None,
) -> BulkOperationResult[T, R]:
    """Convenience function to execute a bulk async operation.

    Args:
        operation: Async function to execute for each item
        items: Sequence of items to process
        config: Optional bulk configuration

    Returns:
        BulkOperationResult with all results and summary
    """
    executor = AsyncBulkExecutor(operation, config)
    return await executor.execute(items)


def bulk_execute_sync(
    operation: Callable[[T], R],
    items: Sequence[T],
    config: Optional[BulkConfig] = None,
) -> BulkOperationResult[T, R]:
    """Convenience function to execute a bulk sync operation.

    Args:
        operation: Function to execute for each item
        items: Sequence of items to process
        config: Optional bulk configuration

    Returns:
        BulkOperationResult with all results and summary
    """
    executor = SyncBulkExecutor(operation, config)
    return executor.execute(items)


__all__ = [
    "OperationStatus",
    "OperationResult",
    "BulkOperationSummary",
    "BulkOperationResult",
    "BulkConfig",
    "AsyncBulkExecutor",
    "SyncBulkExecutor",
    "bulk_execute_async",
    "bulk_execute_sync",
]
