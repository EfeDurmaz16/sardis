from __future__ import annotations

from sardis_api.routers.metrics import (
    approval_queue_depth,
    payment_execution_duration_seconds,
    policy_denial_burst_window,
    policy_denial_spikes_total,
    provider_errors_total,
    record_payment_execution_latency,
    record_funding_attempt,
    record_policy_denial_spike,
    set_approval_queue_depth,
)
from sardis_api.middleware.logging import StructuredLoggingMiddleware


def test_record_funding_attempt_failed_increments_provider_error_counter():
    before = provider_errors_total.labels(provider="stripe", operation="funding")._value.get()
    record_funding_attempt(provider="stripe", rail="fiat", status="failed")
    after = provider_errors_total.labels(provider="stripe", operation="funding")._value.get()
    assert after == before + 1


def test_record_policy_denial_spike_updates_window_and_counter():
    reason = "limit_exceeded_test"
    before_spikes = policy_denial_spikes_total.labels(reason=reason)._value.get()
    for _ in range(3):
        record_policy_denial_spike(reason, window_seconds=300, threshold=3)

    burst_value = policy_denial_burst_window.labels(reason=reason)._value.get()
    after_spikes = policy_denial_spikes_total.labels(reason=reason)._value.get()
    assert burst_value >= 3
    assert after_spikes >= before_spikes + 1


def test_record_payment_execution_latency_observes_histogram():
    before = payment_execution_duration_seconds.labels(
        rail="onchain",
        outcome="success",
    )._sum.get()
    record_payment_execution_latency(
        rail="onchain",
        outcome="success",
        duration_seconds=0.42,
    )
    after = payment_execution_duration_seconds.labels(
        rail="onchain",
        outcome="success",
    )._sum.get()
    assert after >= before + 0.42


def test_set_approval_queue_depth_sets_pending_gauge():
    set_approval_queue_depth(pending_count=7, queue="pending")
    current = approval_queue_depth.labels(queue="pending")._value.get()
    assert current == 7


def test_logging_middleware_classifies_payment_paths():
    assert StructuredLoggingMiddleware._is_payment_endpoint("/api/v2/wallets/w1/pay/onchain")
    assert StructuredLoggingMiddleware._infer_payment_rail("/api/v2/wallets/w1/pay/onchain") == "onchain"
    assert StructuredLoggingMiddleware._infer_payment_rail("/api/v2/cards/card_1/freeze") == "fiat"
