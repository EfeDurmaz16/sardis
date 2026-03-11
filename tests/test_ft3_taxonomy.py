"""Tests for the FT3 (Fraud Tools, Tactics, Techniques) taxonomy module."""
from __future__ import annotations

import pytest
from datetime import UTC, datetime

from sardis_guardrails.ft3_taxonomy import (
    FT3_AGENT_TACTIC_COUNT,
    FT3_STANDARD_TACTIC_COUNT,
    FT3_VERSION,
    HIGH_CONFIDENCE_THRESHOLD,
    SARDIS_TECHNIQUE_PREFIX,
    FT3Event,
    FT3Mitigation,
    FT3MitigationStatus,
    FT3Severity,
    FT3Tactic,
    FT3TaxonomyRegistry,
    FT3TaxonomyStats,
    FT3Technique,
    classify_event,
    create_ft3_registry,
)


# ============ FT3Technique ============


class TestFT3Technique:
    def test_creation(self):
        t = FT3Technique(
            technique_id="T0101",
            name="Synthetic Identity",
            description="Fabricated identity",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD,
            severity=FT3Severity.HIGH,
        )
        assert t.technique_id == "T0101"
        assert t.name == "Synthetic Identity"
        assert t.tactic == FT3Tactic.ACCOUNT_CREATION_FRAUD
        assert t.severity == FT3Severity.HIGH
        assert t.indicators == []
        assert t.mitigations == []
        assert t.is_agent_specific is False

    def test_full_id_property(self):
        t = FT3Technique(
            technique_id="T1301",
            name="Agent Identity Spoofing",
            description="Spoofing",
            tactic=FT3Tactic.AGENT_IMPERSONATION,
            severity=FT3Severity.CRITICAL,
        )
        assert t.full_id == "FT3-T1301"

    def test_agent_specific_flag(self):
        t = FT3Technique(
            technique_id="T1501",
            name="Prompt Injection Payment",
            description="Tricking agent",
            tactic=FT3Tactic.AUTONOMOUS_FRAUD,
            severity=FT3Severity.CRITICAL,
            is_agent_specific=True,
        )
        assert t.is_agent_specific is True

    def test_with_indicators_and_mitigations(self):
        t = FT3Technique(
            technique_id="T0201",
            name="Credential Stuffing",
            description="Reusing leaked credentials",
            tactic=FT3Tactic.ACCOUNT_TAKEOVER,
            severity=FT3Severity.HIGH,
            indicators=["High-volume login failures"],
            mitigations=["Rate limit authentication attempts"],
        )
        assert len(t.indicators) == 1
        assert len(t.mitigations) == 1


# ============ FT3Event ============


class TestFT3Event:
    def test_creation(self):
        e = FT3Event(
            event_id="evt001",
            technique_id="T0101",
            agent_id="agent_1",
            transaction_id="tx_1",
            confidence=0.95,
        )
        assert e.event_id == "evt001"
        assert e.technique_id == "T0101"
        assert e.agent_id == "agent_1"
        assert e.transaction_id == "tx_1"
        assert e.confidence == 0.95
        assert isinstance(e.detected_at, datetime)
        assert e.details == {}

    def test_is_high_confidence_true(self):
        e = FT3Event(event_id="e1", technique_id="T0101", confidence=0.85)
        assert e.is_high_confidence is True

    def test_is_high_confidence_exactly_threshold(self):
        e = FT3Event(event_id="e2", technique_id="T0101", confidence=0.8)
        assert e.is_high_confidence is True

    def test_is_high_confidence_false(self):
        e = FT3Event(event_id="e3", technique_id="T0101", confidence=0.79)
        assert e.is_high_confidence is False

    def test_defaults(self):
        e = FT3Event(event_id="e4", technique_id="T0101")
        assert e.agent_id == ""
        assert e.transaction_id == ""
        assert e.confidence == 0.0
        assert e.details == {}


# ============ FT3Mitigation ============


class TestFT3Mitigation:
    def test_creation(self):
        m = FT3Mitigation(
            mitigation_id="M001",
            name="Rate Limiting",
            description="Limit auth attempts",
            technique_ids=["T0201", "T0202"],
            status=FT3MitigationStatus.ACTIVE,
        )
        assert m.mitigation_id == "M001"
        assert m.name == "Rate Limiting"
        assert len(m.technique_ids) == 2
        assert m.status == FT3MitigationStatus.ACTIVE

    def test_default_status(self):
        m = FT3Mitigation(
            mitigation_id="M002",
            name="KBA",
            description="Knowledge-based auth",
        )
        assert m.status == FT3MitigationStatus.ACTIVE
        assert m.technique_ids == []

    def test_planned_status(self):
        m = FT3Mitigation(
            mitigation_id="M003",
            name="Biometric Auth",
            description="Facial recognition",
            status=FT3MitigationStatus.PLANNED,
        )
        assert m.status == FT3MitigationStatus.PLANNED


# ============ FT3TaxonomyRegistry ============


class TestFT3TaxonomyRegistry:
    @pytest.fixture()
    def registry(self) -> FT3TaxonomyRegistry:
        return FT3TaxonomyRegistry()

    @pytest.fixture()
    def sample_technique(self) -> FT3Technique:
        return FT3Technique(
            technique_id="T9901",
            name="Test Technique",
            description="A technique for testing purposes",
            tactic=FT3Tactic.CARD_FRAUD,
            severity=FT3Severity.LOW,
        )

    # -- register_technique --

    def test_register_technique(self, registry, sample_technique):
        result = registry.register_technique(sample_technique)
        assert result is sample_technique
        assert registry.technique_count == 1

    def test_register_technique_duplicate_raises(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        with pytest.raises(ValueError, match="Duplicate technique ID"):
            registry.register_technique(sample_technique)

    # -- register_mitigation --

    def test_register_mitigation(self, registry):
        m = FT3Mitigation(
            mitigation_id="M100",
            name="Test Mitigation",
            description="Desc",
            technique_ids=["T9901"],
        )
        result = registry.register_mitigation(m)
        assert result is m

    # -- get_technique --

    def test_get_technique_found(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        found = registry.get_technique("T9901")
        assert found is sample_technique

    def test_get_technique_not_found(self, registry):
        assert registry.get_technique("TXXXX") is None

    # -- get_techniques_for_tactic --

    def test_get_techniques_for_tactic(self, registry):
        t1 = FT3Technique(
            technique_id="T0301",
            name="Card Testing",
            description="Small txns",
            tactic=FT3Tactic.CARD_FRAUD,
            severity=FT3Severity.HIGH,
        )
        t2 = FT3Technique(
            technique_id="T0101",
            name="Synthetic Identity",
            description="Fake identity",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD,
            severity=FT3Severity.HIGH,
        )
        registry.register_technique(t1)
        registry.register_technique(t2)
        card_techniques = registry.get_techniques_for_tactic(FT3Tactic.CARD_FRAUD)
        assert len(card_techniques) == 1
        assert card_techniques[0].technique_id == "T0301"

    # -- get_agent_specific_techniques --

    def test_get_agent_specific_techniques(self, registry):
        t_normal = FT3Technique(
            technique_id="T0101",
            name="Normal",
            description="Not agent-specific",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD,
            severity=FT3Severity.LOW,
        )
        t_agent = FT3Technique(
            technique_id="T1301",
            name="Agent Spoofing",
            description="Agent-specific",
            tactic=FT3Tactic.AGENT_IMPERSONATION,
            severity=FT3Severity.CRITICAL,
            is_agent_specific=True,
        )
        registry.register_technique(t_normal)
        registry.register_technique(t_agent)
        agent_techs = registry.get_agent_specific_techniques()
        assert len(agent_techs) == 1
        assert agent_techs[0].technique_id == "T1301"

    # -- search_techniques --

    def test_search_techniques_by_name(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        results = registry.search_techniques("Test")
        assert len(results) == 1

    def test_search_techniques_by_description(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        results = registry.search_techniques("testing purposes")
        assert len(results) == 1

    def test_search_techniques_case_insensitive(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        results = registry.search_techniques("test technique")
        assert len(results) == 1

    def test_search_techniques_no_match(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        results = registry.search_techniques("nonexistent")
        assert len(results) == 0

    # -- record_event --

    def test_record_event(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        event = registry.record_event(
            technique_id="T9901",
            agent_id="agent_1",
            transaction_id="tx_1",
            confidence=0.9,
            details={"ip": "1.2.3.4"},
        )
        assert event.technique_id == "T9901"
        assert event.agent_id == "agent_1"
        assert event.confidence == 0.9
        assert event.details == {"ip": "1.2.3.4"}
        assert len(event.event_id) == 12
        assert registry.event_count == 1

    def test_record_event_unknown_technique_raises(self, registry):
        with pytest.raises(ValueError, match="Unknown technique"):
            registry.record_event(technique_id="TXXXX")

    # -- get_events --

    def test_get_events_unfiltered(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        registry.record_event(technique_id="T9901", confidence=0.5)
        registry.record_event(technique_id="T9901", confidence=0.9)
        events = registry.get_events()
        assert len(events) == 2

    def test_get_events_by_technique(self, registry):
        t1 = FT3Technique(
            technique_id="T0001", name="A", description="A",
            tactic=FT3Tactic.CARD_FRAUD, severity=FT3Severity.LOW,
        )
        t2 = FT3Technique(
            technique_id="T0002", name="B", description="B",
            tactic=FT3Tactic.CARD_FRAUD, severity=FT3Severity.LOW,
        )
        registry.register_technique(t1)
        registry.register_technique(t2)
        registry.record_event(technique_id="T0001")
        registry.record_event(technique_id="T0002")
        registry.record_event(technique_id="T0001")
        events = registry.get_events(technique_id="T0001")
        assert len(events) == 2

    def test_get_events_by_agent(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        registry.record_event(technique_id="T9901", agent_id="agent_a")
        registry.record_event(technique_id="T9901", agent_id="agent_b")
        events = registry.get_events(agent_id="agent_a")
        assert len(events) == 1
        assert events[0].agent_id == "agent_a"

    def test_get_events_by_min_confidence(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        registry.record_event(technique_id="T9901", confidence=0.3)
        registry.record_event(technique_id="T9901", confidence=0.7)
        registry.record_event(technique_id="T9901", confidence=0.95)
        events = registry.get_events(min_confidence=0.5)
        assert len(events) == 2

    # -- get_stats --

    def test_get_stats(self, registry):
        t1 = FT3Technique(
            technique_id="T0101", name="A", description="A",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD, severity=FT3Severity.LOW,
        )
        t2 = FT3Technique(
            technique_id="T0102", name="B", description="B",
            tactic=FT3Tactic.ACCOUNT_CREATION_FRAUD, severity=FT3Severity.LOW,
        )
        t3 = FT3Technique(
            technique_id="T1301", name="C", description="C",
            tactic=FT3Tactic.AGENT_IMPERSONATION, severity=FT3Severity.HIGH,
            is_agent_specific=True,
        )
        registry.register_technique(t1)
        registry.register_technique(t2)
        registry.register_technique(t3)
        stats = registry.get_stats()
        assert stats.total_tactics == 2
        assert stats.total_techniques == 3
        assert stats.agent_specific_count == 1
        assert stats.coverage_by_tactic["TA01"] == 2
        assert stats.coverage_by_tactic["TA13"] == 1

    # -- load_standard_taxonomy --

    def test_load_standard_taxonomy_counts(self, registry):
        registry.load_standard_taxonomy()
        assert registry.technique_count >= 20
        # Verify agent-specific techniques exist
        agent_techs = registry.get_agent_specific_techniques()
        assert len(agent_techs) >= 8  # T1301-T1503

    def test_load_standard_taxonomy_all_agent_tactics_covered(self, registry):
        registry.load_standard_taxonomy()
        for tactic in (FT3Tactic.AGENT_IMPERSONATION, FT3Tactic.POLICY_EVASION, FT3Tactic.AUTONOMOUS_FRAUD):
            techniques = registry.get_techniques_for_tactic(tactic)
            assert len(techniques) >= 2, f"Tactic {tactic.name} has < 2 techniques"

    def test_load_standard_taxonomy_standard_tactics_covered(self, registry):
        registry.load_standard_taxonomy()
        for tactic in (
            FT3Tactic.ACCOUNT_CREATION_FRAUD,
            FT3Tactic.ACCOUNT_TAKEOVER,
            FT3Tactic.CARD_FRAUD,
            FT3Tactic.IDENTITY_FRAUD,
            FT3Tactic.MONEY_LAUNDERING,
        ):
            techniques = registry.get_techniques_for_tactic(tactic)
            assert len(techniques) >= 2, f"Tactic {tactic.name} has < 2 techniques"

    def test_load_standard_taxonomy_no_duplicates(self, registry):
        registry.load_standard_taxonomy()
        # Calling again should raise
        with pytest.raises(ValueError, match="Duplicate technique ID"):
            registry.load_standard_taxonomy()

    # -- Properties --

    def test_technique_count_empty(self, registry):
        assert registry.technique_count == 0

    def test_event_count_empty(self, registry):
        assert registry.event_count == 0

    def test_technique_count_after_load(self, registry):
        registry.load_standard_taxonomy()
        assert registry.technique_count >= 20

    def test_event_count_after_record(self, registry, sample_technique):
        registry.register_technique(sample_technique)
        registry.record_event(technique_id="T9901")
        registry.record_event(technique_id="T9901")
        assert registry.event_count == 2


# ============ Tactic Enum ============


class TestTacticEnum:
    def test_tactic_count(self):
        assert len(FT3Tactic) == 15

    def test_standard_tactic_values(self):
        assert FT3Tactic.ACCOUNT_CREATION_FRAUD.value == "TA01"
        assert FT3Tactic.ACCOUNT_TAKEOVER.value == "TA02"
        assert FT3Tactic.CARD_FRAUD.value == "TA03"
        assert FT3Tactic.IDENTITY_FRAUD.value == "TA04"
        assert FT3Tactic.MONEY_LAUNDERING.value == "TA05"
        assert FT3Tactic.MERCHANT_FRAUD.value == "TA06"
        assert FT3Tactic.PROMO_ABUSE.value == "TA07"
        assert FT3Tactic.REFUND_FRAUD.value == "TA08"
        assert FT3Tactic.WIRE_FRAUD.value == "TA09"
        assert FT3Tactic.CHECK_FRAUD.value == "TA10"
        assert FT3Tactic.LOAN_FRAUD.value == "TA11"
        assert FT3Tactic.INSURANCE_FRAUD.value == "TA12"

    def test_agent_tactic_values(self):
        assert FT3Tactic.AGENT_IMPERSONATION.value == "TA13"
        assert FT3Tactic.POLICY_EVASION.value == "TA14"
        assert FT3Tactic.AUTONOMOUS_FRAUD.value == "TA15"

    def test_tactic_is_str_enum(self):
        assert isinstance(FT3Tactic.CARD_FRAUD, str)
        assert FT3Tactic.CARD_FRAUD == "TA03"


# ============ Severity Enum ============


class TestSeverityEnum:
    def test_severity_count(self):
        assert len(FT3Severity) == 5

    def test_severity_values(self):
        assert FT3Severity.INFO.value == "info"
        assert FT3Severity.LOW.value == "low"
        assert FT3Severity.MEDIUM.value == "medium"
        assert FT3Severity.HIGH.value == "high"
        assert FT3Severity.CRITICAL.value == "critical"

    def test_severity_is_str_enum(self):
        assert isinstance(FT3Severity.HIGH, str)
        assert FT3Severity.HIGH == "high"


# ============ Constants ============


class TestConstants:
    def test_ft3_version(self):
        assert FT3_VERSION == "1.0.0"

    def test_standard_tactic_count(self):
        assert FT3_STANDARD_TACTIC_COUNT == 12

    def test_agent_tactic_count(self):
        assert FT3_AGENT_TACTIC_COUNT == 3

    def test_high_confidence_threshold(self):
        assert HIGH_CONFIDENCE_THRESHOLD == 0.8

    def test_sardis_technique_prefix(self):
        assert SARDIS_TECHNIQUE_PREFIX == "T13"


# ============ Factory ============


class TestFactory:
    def test_create_ft3_registry_with_defaults(self):
        registry = create_ft3_registry(load_defaults=True)
        assert registry.technique_count >= 20

    def test_create_ft3_registry_without_defaults(self):
        registry = create_ft3_registry(load_defaults=False)
        assert registry.technique_count == 0

    def test_create_ft3_registry_default_arg(self):
        registry = create_ft3_registry()
        assert registry.technique_count >= 20


# ============ classify_event helper ============


class TestClassifyEvent:
    def test_classify_event(self):
        event = classify_event(
            technique_id="T0101",
            agent_id="agent_x",
            transaction_id="tx_123",
            confidence=0.88,
            details={"reason": "test"},
        )
        assert isinstance(event, FT3Event)
        assert event.technique_id == "T0101"
        assert event.agent_id == "agent_x"
        assert event.confidence == 0.88
        assert event.is_high_confidence is True
        assert len(event.event_id) == 12

    def test_classify_event_defaults(self):
        event = classify_event(technique_id="T0301")
        assert event.agent_id == ""
        assert event.transaction_id == ""
        assert event.confidence == 0.0
        assert event.details == {}


# ============ Module Exports ============


class TestModuleExports:
    def test_import_from_sardis_guardrails(self):
        from sardis_guardrails import (
            FT3TaxonomyRegistry,
            FT3Tactic,
            FT3Technique,
            FT3Event,
            FT3Severity,
            FT3Mitigation,
            FT3MitigationStatus,
            FT3TaxonomyStats,
            create_ft3_registry,
            classify_event,
        )
        # Just verify they imported without error
        assert FT3TaxonomyRegistry is not None
        assert FT3Tactic is not None
        assert FT3Technique is not None
        assert FT3Event is not None
        assert FT3Severity is not None
        assert FT3Mitigation is not None
        assert FT3MitigationStatus is not None
        assert FT3TaxonomyStats is not None
        assert create_ft3_registry is not None
        assert classify_event is not None
