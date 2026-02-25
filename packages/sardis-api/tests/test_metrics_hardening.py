from __future__ import annotations

from sardis_api.routers.metrics import (
    policy_denial_burst_window,
    policy_denial_spikes_total,
    provider_errors_total,
    record_funding_attempt,
    record_policy_denial_spike,
)


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
