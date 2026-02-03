"""Tests for scheduler and background jobs."""
from __future__ import annotations

import pytest
import asyncio
from sardis_v2_core.scheduler import SardisScheduler, init_scheduler, get_scheduler


@pytest.fixture
def scheduler():
    """Create a scheduler instance for testing."""
    return SardisScheduler()


@pytest.mark.anyio
async def test_scheduler_initialization():
    """Test scheduler can be initialized."""
    scheduler = SardisScheduler()
    assert scheduler is not None
    assert not scheduler.is_running


@pytest.mark.anyio
async def test_scheduler_start_stop(scheduler):
    """Test scheduler can be started and stopped."""
    await scheduler.start()
    assert scheduler.is_running

    await scheduler.shutdown()
    assert not scheduler.is_running


@pytest.mark.anyio
async def test_add_cron_job(scheduler):
    """Test adding a cron job."""
    call_count = []

    async def test_job():
        call_count.append(1)

    scheduler.add_cron_job(
        test_job,
        job_id="test_cron",
        hour=0,
        minute=0,
    )

    # Job should be registered but not executed yet
    assert len(call_count) == 0


@pytest.mark.anyio
async def test_add_interval_job(scheduler):
    """Test adding an interval job."""
    call_count = []

    async def test_job():
        call_count.append(1)

    scheduler.add_interval_job(
        test_job,
        job_id="test_interval",
        seconds=1,
    )

    await scheduler.start()

    # Wait for job to execute at least once
    await asyncio.sleep(1.5)

    await scheduler.shutdown()

    # Job should have been called at least once
    assert len(call_count) >= 1


@pytest.mark.anyio
async def test_interval_job_executes_multiple_times(scheduler):
    """Test interval job executes on schedule."""
    call_count = []

    async def test_job():
        call_count.append(1)

    scheduler.add_interval_job(
        test_job,
        job_id="test_multiple",
        seconds=1,
    )

    await scheduler.start()

    # Wait for multiple executions
    await asyncio.sleep(2.5)

    await scheduler.shutdown()

    # Should have executed 2-3 times
    assert len(call_count) >= 2


@pytest.mark.anyio
async def test_job_replace_existing(scheduler):
    """Test that jobs can be replaced."""
    call_count_1 = []
    call_count_2 = []

    async def job_1():
        call_count_1.append(1)

    async def job_2():
        call_count_2.append(1)

    # Add first job
    scheduler.add_interval_job(
        job_1,
        job_id="replaceable_job",
        seconds=1,
    )

    # Replace with second job
    scheduler.add_interval_job(
        job_2,
        job_id="replaceable_job",
        seconds=1,
    )

    await scheduler.start()
    await asyncio.sleep(1.5)
    await scheduler.shutdown()

    # Only second job should have executed
    assert len(call_count_1) == 0
    assert len(call_count_2) >= 1


@pytest.mark.anyio
async def test_global_scheduler_init():
    """Test global scheduler initialization."""
    scheduler = init_scheduler()
    assert scheduler is not None

    retrieved = get_scheduler()
    assert retrieved is scheduler


@pytest.mark.anyio
async def test_get_scheduler_before_init():
    """Test get_scheduler raises error if not initialized."""
    # Reset global scheduler
    import sardis_v2_core.scheduler as scheduler_module
    scheduler_module._scheduler = None

    with pytest.raises(RuntimeError, match="Scheduler not initialized"):
        get_scheduler()


@pytest.mark.anyio
async def test_scheduler_with_database_url():
    """Test scheduler with database URL for persistence."""
    # Use in-memory SQLite for testing
    scheduler = SardisScheduler(database_url="sqlite:///:memory:")
    assert scheduler is not None
    # Note: Starting scheduler with database persistence requires module-level
    # functions for job serialization. We only verify creation here.


@pytest.mark.anyio
async def test_scheduler_timezone():
    """Test scheduler with custom timezone."""
    scheduler = SardisScheduler(timezone="America/New_York")
    assert scheduler is not None


@pytest.mark.anyio
async def test_multiple_jobs(scheduler):
    """Test scheduler can handle multiple jobs."""
    calls_1 = []
    calls_2 = []

    async def job_1():
        calls_1.append(1)

    async def job_2():
        calls_2.append(1)

    scheduler.add_interval_job(job_1, job_id="job1", seconds=1)
    scheduler.add_interval_job(job_2, job_id="job2", seconds=1)

    await scheduler.start()
    await asyncio.sleep(1.5)
    await scheduler.shutdown()

    # Both jobs should have executed
    assert len(calls_1) >= 1
    assert len(calls_2) >= 1


@pytest.mark.anyio
async def test_job_exception_handling(scheduler):
    """Test that job exceptions don't crash the scheduler."""
    call_count = []

    async def failing_job():
        call_count.append(1)
        raise ValueError("Test error")

    scheduler.add_interval_job(failing_job, job_id="failing", seconds=1)

    await scheduler.start()
    await asyncio.sleep(1.5)
    await scheduler.shutdown()

    # Job should have attempted execution despite error
    assert len(call_count) >= 1
