"""
Batch screening support module.

Provides efficient batch processing for compliance screenings:
- Concurrent batch execution
- Progress tracking
- Error handling and partial failure support
- Result aggregation
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Result type


class BatchStatus(str, Enum):
    """Status of a batch job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ItemStatus(str, Enum):
    """Status of an individual item in a batch."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchItem(Generic[T]):
    """A single item in a batch job."""
    item_id: str
    input_data: Dict[str, Any]
    status: ItemStatus = ItemStatus.PENDING
    result: Optional[T] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "status": self.status.value,
            "input_data": self.input_data,
            "result": self.result if isinstance(self.result, (dict, list, str, int, float, bool, type(None))) else str(self.result),
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class BatchJob(Generic[T]):
    """A batch processing job."""
    job_id: str
    job_type: str
    items: List[BatchItem[T]] = field(default_factory=list)
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        """Total number of items."""
        return len(self.items)

    @property
    def completed_items(self) -> int:
        """Number of completed items."""
        return sum(1 for item in self.items if item.status == ItemStatus.COMPLETED)

    @property
    def failed_items(self) -> int:
        """Number of failed items."""
        return sum(1 for item in self.items if item.status == ItemStatus.FAILED)

    @property
    def pending_items(self) -> int:
        """Number of pending items."""
        return sum(1 for item in self.items if item.status == ItemStatus.PENDING)

    @property
    def progress_percent(self) -> float:
        """Completion percentage."""
        if self.total_items == 0:
            return 100.0
        processed = self.completed_items + self.failed_items
        return (processed / self.total_items) * 100

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        processed = self.completed_items + self.failed_items
        if processed == 0:
            return 0.0
        return (self.completed_items / processed) * 100

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total job duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_results(self) -> List[T]:
        """Get all successful results."""
        return [item.result for item in self.items if item.result is not None]

    def get_failures(self) -> List[Dict[str, Any]]:
        """Get all failure details."""
        return [
            {
                "item_id": item.item_id,
                "input_data": item.input_data,
                "error": item.error,
            }
            for item in self.items
            if item.status == ItemStatus.FAILED
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "pending_items": self.pending_items,
            "progress_percent": self.progress_percent,
            "success_rate": self.success_rate,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_concurrency: int = 10  # Maximum concurrent items
    max_retries: int = 3  # Maximum retries per item
    retry_delay_seconds: float = 1.0  # Delay between retries
    timeout_seconds: float = 60.0  # Timeout per item
    continue_on_error: bool = True  # Continue processing after failures
    batch_size: int = 100  # Process in batches of this size


class BatchProcessor(Generic[T]):
    """
    Generic batch processor for compliance operations.

    Supports concurrent processing with configurable parallelism,
    retry logic, and progress tracking.
    """

    def __init__(
        self,
        config: Optional[BatchConfig] = None,
        on_progress: Optional[Callable[[BatchJob[T]], None]] = None,
    ):
        """
        Initialize batch processor.

        Args:
            config: Batch processing configuration
            on_progress: Callback called after each item completes
        """
        self._config = config or BatchConfig()
        self._on_progress = on_progress
        self._jobs: Dict[str, BatchJob[T]] = {}
        self._cancelled: set = set()

    async def create_job(
        self,
        job_type: str,
        items: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchJob[T]:
        """
        Create a new batch job.

        Args:
            job_type: Type of job (e.g., "pep_screening", "sanctions_screening")
            items: List of input data dictionaries
            metadata: Additional job metadata

        Returns:
            Created BatchJob
        """
        job_id = f"batch_{uuid.uuid4().hex[:12]}"

        batch_items = [
            BatchItem[T](
                item_id=f"{job_id}_{i:06d}",
                input_data=item,
            )
            for i, item in enumerate(items)
        ]

        job = BatchJob[T](
            job_id=job_id,
            job_type=job_type,
            items=batch_items,
            metadata=metadata or {},
        )

        self._jobs[job_id] = job
        logger.info(f"Batch job created: {job_id} with {len(items)} items")

        return job

    async def execute_job(
        self,
        job: BatchJob[T],
        processor: Callable[[Dict[str, Any]], T],
    ) -> BatchJob[T]:
        """
        Execute a batch job.

        Args:
            job: The batch job to execute
            processor: Async function to process each item

        Returns:
            Completed BatchJob with results
        """
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)

        logger.info(f"Starting batch job {job.job_id}")

        # Process items with concurrency limit
        semaphore = asyncio.Semaphore(self._config.max_concurrency)

        async def process_item(item: BatchItem[T]) -> None:
            if job.job_id in self._cancelled:
                item.status = ItemStatus.SKIPPED
                return

            async with semaphore:
                await self._process_single_item(item, processor)

            # Progress callback
            if self._on_progress:
                try:
                    self._on_progress(job)
                except Exception as e:
                    logger.error(f"Progress callback failed: {e}")

        # Process in batches to avoid overwhelming memory
        for i in range(0, len(job.items), self._config.batch_size):
            if job.job_id in self._cancelled:
                break

            batch = job.items[i:i + self._config.batch_size]
            await asyncio.gather(*[process_item(item) for item in batch])

        # Determine final status
        job.completed_at = datetime.now(timezone.utc)

        if job.job_id in self._cancelled:
            job.status = BatchStatus.CANCELLED
        elif job.failed_items == 0:
            job.status = BatchStatus.COMPLETED
        elif job.completed_items > 0:
            job.status = BatchStatus.PARTIALLY_COMPLETED
        else:
            job.status = BatchStatus.FAILED

        logger.info(
            f"Batch job {job.job_id} completed: "
            f"{job.completed_items}/{job.total_items} successful "
            f"({job.progress_percent:.1f}% complete)"
        )

        return job

    async def _process_single_item(
        self,
        item: BatchItem[T],
        processor: Callable[[Dict[str, Any]], T],
    ) -> None:
        """Process a single item with retry logic."""
        item.status = ItemStatus.PROCESSING
        item.started_at = datetime.now(timezone.utc)

        for attempt in range(self._config.max_retries + 1):
            try:
                # Check if processor is async
                if asyncio.iscoroutinefunction(processor):
                    result = await asyncio.wait_for(
                        processor(item.input_data),
                        timeout=self._config.timeout_seconds,
                    )
                else:
                    # Run sync function in executor
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, processor, item.input_data),
                        timeout=self._config.timeout_seconds,
                    )

                item.result = result
                item.status = ItemStatus.COMPLETED
                item.completed_at = datetime.now(timezone.utc)
                return

            except asyncio.TimeoutError:
                item.error = f"Timeout after {self._config.timeout_seconds}s"
                item.retry_count = attempt + 1
            except Exception as e:
                item.error = str(e)
                item.retry_count = attempt + 1
                logger.warning(f"Item {item.item_id} failed (attempt {attempt + 1}): {e}")

            # Retry with exponential backoff
            if attempt < self._config.max_retries:
                delay = self._config.retry_delay_seconds * (2 ** attempt)
                await asyncio.sleep(delay)

        # All retries exhausted
        item.status = ItemStatus.FAILED
        item.completed_at = datetime.now(timezone.utc)

        if not self._config.continue_on_error:
            raise RuntimeError(f"Item {item.item_id} failed after {self._config.max_retries} retries")

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self._jobs:
            self._cancelled.add(job_id)
            logger.info(f"Batch job {job_id} cancelled")
            return True
        return False

    def get_job(self, job_id: str) -> Optional[BatchJob[T]]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status summary."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return job.to_dict()


class ComplianceBatchScreener:
    """
    High-level batch screening service for compliance operations.

    Provides convenient methods for batch screening of different types.
    """

    def __init__(
        self,
        pep_service=None,
        sanctions_service=None,
        adverse_media_service=None,
        config: Optional[BatchConfig] = None,
    ):
        """
        Initialize batch screener.

        Args:
            pep_service: PEP screening service
            sanctions_service: Sanctions screening service
            adverse_media_service: Adverse media screening service
            config: Batch processing configuration
        """
        self._pep_service = pep_service
        self._sanctions_service = sanctions_service
        self._adverse_media_service = adverse_media_service
        self._config = config or BatchConfig()
        self._processor = BatchProcessor(config=self._config)

    async def batch_pep_screening(
        self,
        subjects: List[Dict[str, Any]],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> BatchJob:
        """
        Perform batch PEP screening.

        Args:
            subjects: List of dicts with 'subject_id', 'name', and optional 'date_of_birth', 'country'
            on_progress: Optional callback with progress percentage

        Returns:
            Completed BatchJob with PEP screening results
        """
        if not self._pep_service:
            raise ValueError("PEP service not configured")

        # Create processor that calls PEP service
        async def process_pep(data: Dict[str, Any]):
            result = await self._pep_service.screen_individual(
                subject_id=data["subject_id"],
                name=data["name"],
                date_of_birth=data.get("date_of_birth"),
                country=data.get("country"),
            )
            # Convert to dict for serialization
            return {
                "is_pep": result.is_pep,
                "subject_id": result.subject_id,
                "subject_name": result.subject_name,
                "highest_risk": result.highest_risk.value if hasattr(result.highest_risk, 'value') else result.highest_risk,
                "match_count": result.match_count,
                "requires_enhanced_due_diligence": result.requires_enhanced_due_diligence,
            }

        # Create and execute job
        job = await self._processor.create_job(
            job_type="pep_screening",
            items=subjects,
            metadata={"total_subjects": len(subjects)},
        )

        # Wrap progress callback
        def progress_callback(batch_job):
            if on_progress:
                on_progress(batch_job.progress_percent)

        self._processor._on_progress = progress_callback

        return await self._processor.execute_job(job, process_pep)

    async def batch_sanctions_screening(
        self,
        addresses: List[Dict[str, Any]],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> BatchJob:
        """
        Perform batch sanctions screening.

        Args:
            addresses: List of dicts with 'address' and optional 'chain'
            on_progress: Optional callback with progress percentage

        Returns:
            Completed BatchJob with sanctions screening results
        """
        if not self._sanctions_service:
            raise ValueError("Sanctions service not configured")

        async def process_sanctions(data: Dict[str, Any]):
            result = await self._sanctions_service.screen_address(
                address=data["address"],
                chain=data.get("chain", "ethereum"),
            )
            return {
                "entity_id": result.entity_id,
                "risk_level": result.risk_level.value if hasattr(result.risk_level, 'value') else result.risk_level,
                "is_sanctioned": result.is_sanctioned,
                "should_block": result.should_block,
                "matches": result.matches,
            }

        job = await self._processor.create_job(
            job_type="sanctions_screening",
            items=addresses,
            metadata={"total_addresses": len(addresses)},
        )

        def progress_callback(batch_job):
            if on_progress:
                on_progress(batch_job.progress_percent)

        self._processor._on_progress = progress_callback

        return await self._processor.execute_job(job, process_sanctions)

    async def batch_adverse_media_screening(
        self,
        subjects: List[Dict[str, Any]],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> BatchJob:
        """
        Perform batch adverse media screening.

        Args:
            subjects: List of dicts with 'subject_id', 'name', and optional 'country'
            on_progress: Optional callback with progress percentage

        Returns:
            Completed BatchJob with adverse media results
        """
        if not self._adverse_media_service:
            raise ValueError("Adverse media service not configured")

        async def process_media(data: Dict[str, Any]):
            result = await self._adverse_media_service.screen_individual(
                subject_id=data["subject_id"],
                name=data["name"],
                country=data.get("country"),
            )
            return {
                "has_adverse_media": result.has_adverse_media,
                "subject_id": result.subject_id,
                "subject_name": result.subject_name,
                "highest_severity": result.highest_severity.value if hasattr(result.highest_severity, 'value') else result.highest_severity,
                "article_count": result.article_count,
                "requires_review": result.requires_review,
                "risk_score": result.risk_score,
            }

        job = await self._processor.create_job(
            job_type="adverse_media_screening",
            items=subjects,
            metadata={"total_subjects": len(subjects)},
        )

        def progress_callback(batch_job):
            if on_progress:
                on_progress(batch_job.progress_percent)

        self._processor._on_progress = progress_callback

        return await self._processor.execute_job(job, process_media)

    async def batch_combined_screening(
        self,
        subjects: List[Dict[str, Any]],
        include_pep: bool = True,
        include_sanctions: bool = True,
        include_adverse_media: bool = True,
        on_progress: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, BatchJob]:
        """
        Perform combined batch screening across all types.

        Args:
            subjects: List of subject data
            include_pep: Include PEP screening
            include_sanctions: Include sanctions screening
            include_adverse_media: Include adverse media screening
            on_progress: Callback with (screening_type, progress)

        Returns:
            Dict mapping screening type to BatchJob
        """
        results = {}

        if include_pep and self._pep_service:
            def pep_progress(pct):
                if on_progress:
                    on_progress("pep", pct)

            results["pep"] = await self.batch_pep_screening(subjects, pep_progress)

        if include_sanctions and self._sanctions_service:
            # Convert subjects to addresses format
            addresses = [
                {"address": s.get("address", s.get("subject_id")), "chain": s.get("chain", "ethereum")}
                for s in subjects
                if s.get("address") or s.get("subject_id")
            ]

            def sanctions_progress(pct):
                if on_progress:
                    on_progress("sanctions", pct)

            results["sanctions"] = await self.batch_sanctions_screening(addresses, sanctions_progress)

        if include_adverse_media and self._adverse_media_service:
            def media_progress(pct):
                if on_progress:
                    on_progress("adverse_media", pct)

            results["adverse_media"] = await self.batch_adverse_media_screening(subjects, media_progress)

        return results

    def get_batch_summary(self, jobs: Dict[str, BatchJob]) -> Dict[str, Any]:
        """
        Get summary of multiple batch jobs.

        Args:
            jobs: Dict mapping job type to BatchJob

        Returns:
            Summary statistics
        """
        total_items = sum(job.total_items for job in jobs.values())
        completed_items = sum(job.completed_items for job in jobs.values())
        failed_items = sum(job.failed_items for job in jobs.values())

        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "failed_items": failed_items,
            "overall_success_rate": (completed_items / total_items * 100) if total_items > 0 else 0,
            "by_type": {
                job_type: {
                    "status": job.status.value,
                    "total": job.total_items,
                    "completed": job.completed_items,
                    "failed": job.failed_items,
                    "success_rate": job.success_rate,
                }
                for job_type, job in jobs.items()
            },
        }


def create_batch_screener(
    pep_service=None,
    sanctions_service=None,
    adverse_media_service=None,
    config: Optional[BatchConfig] = None,
) -> ComplianceBatchScreener:
    """
    Factory function to create batch screener.

    Args:
        pep_service: PEP screening service
        sanctions_service: Sanctions screening service
        adverse_media_service: Adverse media service
        config: Batch processing configuration

    Returns:
        Configured ComplianceBatchScreener
    """
    return ComplianceBatchScreener(
        pep_service=pep_service,
        sanctions_service=sanctions_service,
        adverse_media_service=adverse_media_service,
        config=config,
    )
