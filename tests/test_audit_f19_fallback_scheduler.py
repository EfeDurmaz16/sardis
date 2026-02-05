"""Tests for F19: Fallback scheduler warns when cron jobs are silently dropped."""
import logging
import pytest


def test_fallback_scheduler_warns_on_cron_job(caplog):
    """Fallback scheduler should log WARNING when cron job won't execute."""
    from sardis_v2_core.scheduler import SardisScheduler

    # Create scheduler without APScheduler (database_url=None forces fallback if APScheduler missing)
    scheduler = SardisScheduler(database_url=None)

    # Only test if we're in fallback mode (no APScheduler)
    if scheduler._scheduler is not None:
        pytest.skip("APScheduler is available, test only applies to fallback mode")

    with caplog.at_level(logging.WARNING):
        scheduler.add_cron_job(
            lambda: None,
            "test_cron_job",
            hour=9,
            minute=0,
        )

    # Should have WARNING about cron job not executing
    warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warning_logs) > 0, "Expected WARNING log when cron job registered in fallback mode"

    warning_msg = warning_logs[0].message
    assert "test_cron_job" in warning_msg, f"Warning should mention job ID: {warning_msg}"
    assert "NOT execute" in warning_msg or "not execute" in warning_msg.lower(), f"Warning should mention non-execution: {warning_msg}"
    assert "APScheduler" in warning_msg, f"Warning should mention APScheduler: {warning_msg}"


def test_fallback_scheduler_stores_but_does_not_execute_cron():
    """Cron jobs are stored but never executed in fallback mode."""
    from sardis_v2_core.scheduler import SardisScheduler

    scheduler = SardisScheduler(database_url=None)

    if scheduler._scheduler is not None:
        pytest.skip("APScheduler is available, test only applies to fallback mode")

    executed = []

    def cron_func():
        executed.append(True)

    scheduler.add_cron_job(cron_func, "test_cron", hour=0, minute=0)

    # Job should be stored
    assert "test_cron" in scheduler._cron_jobs
    assert scheduler._cron_jobs["test_cron"] == cron_func

    # But it should never execute (even after start)
    # This is the silent drop behavior - we now warn about it
    assert len(executed) == 0, "Cron job should not execute in fallback mode"
