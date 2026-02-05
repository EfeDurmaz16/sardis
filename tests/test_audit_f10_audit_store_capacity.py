"""Test F10: In-memory audit store warns when approaching capacity."""
import logging
from collections import deque
from sardis_compliance.checks import ComplianceAuditStore, ComplianceAuditEntry


def _make_store(max_entries):
    """Create a ComplianceAuditStore with a small capacity for testing."""
    store = ComplianceAuditStore()
    store.MAX_ENTRIES = max_entries
    # deque.maxlen is read-only, so replace the deque entirely
    store._entries = deque(store._entries, maxlen=max_entries)
    return store


def _entry(i):
    return ComplianceAuditEntry(
        mandate_id=f"mandate_{i}",
        subject=f"agent_{i}",
        allowed=True,
    )


def test_audit_store_warns_at_90_percent_capacity(caplog):
    """When audit store reaches 90% capacity, it should log a WARNING."""
    store = _make_store(100)

    with caplog.at_level(logging.WARNING):
        # Fill to 89% - should not warn
        for i in range(89):
            store.append(_entry(i))
        assert len(caplog.records) == 0

        # Add one more to reach 90% - should warn
        store.append(_entry(90))

        assert len(caplog.records) > 0
        assert caplog.records[0].levelname == "WARNING"
        assert "approaching capacity" in caplog.records[0].message.lower()
        assert "90/100" in caplog.records[0].message


def test_audit_store_warns_at_95_percent_capacity(caplog):
    """Warning should continue at 95%."""
    store = _make_store(100)

    with caplog.at_level(logging.WARNING):
        for i in range(95):
            store.append(_entry(i))

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) > 0
        assert "approaching capacity" in warnings[-1].message.lower()


def test_audit_store_warns_at_100_percent_capacity(caplog):
    """Warning should occur at 100% capacity."""
    store = _make_store(100)

    with caplog.at_level(logging.WARNING):
        for i in range(100):
            store.append(_entry(i))

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) > 0
        assert "100/100" in warnings[-1].message


def test_audit_store_capacity_message_mentions_postgresql(caplog):
    """Warning message should suggest migrating to PostgreSQL."""
    store = _make_store(10)

    with caplog.at_level(logging.WARNING):
        for i in range(9):
            store.append(_entry(i))

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) > 0
        assert "postgresql" in warnings[0].message.lower()


def test_audit_store_below_threshold_no_warning(caplog):
    """Below 90% capacity, no warning should be logged."""
    store = _make_store(100)

    with caplog.at_level(logging.WARNING):
        for i in range(50):
            store.append(_entry(i))

        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 0
