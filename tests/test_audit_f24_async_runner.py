"""Tests for F24: Async runner should log and re-raise exceptions."""
import asyncio
import logging
import pytest


@pytest.mark.asyncio
async def test_async_runner_logs_and_raises_exception(caplog):
    """Interval job runner should log ERROR and re-raise exceptions, not swallow them."""
    from sardis_v2_core.scheduler import SardisScheduler

    scheduler = SardisScheduler(database_url=None)

    # Force fallback mode for this test (interval jobs work in fallback)
    if scheduler._scheduler is not None:
        scheduler._scheduler = None

    call_count = [0]

    async def failing_job():
        call_count[0] += 1
        raise ValueError("Test exception from job")

    # Register interval job with very short interval
    scheduler.add_interval_job(failing_job, "test_failing_job", seconds=0.05)

    with caplog.at_level(logging.ERROR):
        await scheduler.start()

        # Wait for job to execute and fail
        await asyncio.sleep(0.15)

        await scheduler.shutdown(wait=True)

    # Job should have been called at least once
    assert call_count[0] >= 1, "Job should have executed at least once"

    # Should have ERROR log
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) > 0, "Expected ERROR log when job fails"

    error_msg = error_logs[0].message
    assert "test_failing_job" in error_msg, f"Error log should mention job ID: {error_msg}"
    assert "ValueError" in error_msg, f"Error log should mention exception type: {error_msg}"


@pytest.mark.asyncio
async def test_async_runner_stops_on_exception():
    """When exception is raised, the runner task should terminate."""
    from sardis_v2_core.scheduler import SardisScheduler

    scheduler = SardisScheduler(database_url=None)

    if scheduler._scheduler is not None:
        scheduler._scheduler = None

    call_count = [0]

    async def failing_job():
        call_count[0] += 1
        raise RuntimeError("Job failed")

    scheduler.add_interval_job(failing_job, "failing_job", seconds=0.05)

    await scheduler.start()

    # Wait for failure
    await asyncio.sleep(0.15)

    # Get the task
    job = scheduler._interval_jobs.get("failing_job")
    assert job is not None
    assert job.task is not None

    # Wait a bit more to see if task completed with exception
    await asyncio.sleep(0.1)

    # Task should be done (either cancelled or failed)
    assert job.task.done(), "Task should have terminated after exception"

    await scheduler.shutdown(wait=True)

    # Job should have been called at least once before failing
    assert call_count[0] >= 1, "Job should have executed before raising exception"
