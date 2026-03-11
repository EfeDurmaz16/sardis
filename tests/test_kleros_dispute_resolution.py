"""Tests for Kleros decentralized dispute resolution.

Covers issue #142. Tests dispute lifecycle, evidence submission,
ruling management, appeal flow, cost estimation, and calldata builders.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis_protocol.kleros import (
    ARBITRATION_FEE_ESTIMATES,
    DEFAULT_APPEAL_PERIOD_DAYS,
    DEFAULT_EVIDENCE_PERIOD_DAYS,
    DEFAULT_NUM_JURORS,
    KLEROS_ARBITRATOR_ADDRESS,
    MIN_DISPUTE_AMOUNT_USD,
    ArbitrationCostEstimate,
    CourtCategory,
    Dispute,
    DisputeParty,
    DisputePartyRole,
    DisputeRulingResult,
    DisputeStatus,
    Evidence,
    EvidenceType,
    KlerosDisputeResolver,
    Ruling,
    build_appeal_calldata,
    build_create_dispute_calldata,
    build_rule_calldata,
    build_submit_evidence_calldata,
    create_dispute_resolver,
)


# ============ Dispute Creation Tests ============


class TestDisputeCreation:
    def test_create_dispute(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Service not delivered",
        )
        assert isinstance(dispute, Dispute)
        assert dispute.status == DisputeStatus.EVIDENCE
        assert dispute.claimant.party_id == "alice"
        assert dispute.respondent.party_id == "bob"
        assert dispute.amount_usd == Decimal("1000")
        assert dispute.is_active is True

    def test_create_dispute_with_escrow(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("500"),
            reason="Defective delivery",
            escrow_id="esc_123",
        )
        assert dispute.escrow_id == "esc_123"

    def test_create_dispute_custom_court(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("5000"),
            reason="Technical issue",
            court=CourtCategory.TECHNICAL,
        )
        assert dispute.court == CourtCategory.TECHNICAL

    def test_create_dispute_custom_jurors(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("10000"),
            reason="Large dispute",
            num_jurors=5,
        )
        assert dispute.num_jurors == 5

    def test_dispute_evidence_period(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        assert dispute.evidence_period_end is not None
        delta = dispute.evidence_period_end - dispute.created_at
        assert abs(delta.days - DEFAULT_EVIDENCE_PERIOD_DAYS) <= 1

    def test_get_dispute(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("100"),
            reason="Test",
        )
        found = resolver.get_dispute(dispute.dispute_id)
        assert found is dispute

    def test_get_dispute_not_found(self):
        resolver = KlerosDisputeResolver()
        assert resolver.get_dispute("nonexistent") is None


# ============ Evidence Submission Tests ============


class TestEvidenceSubmission:
    def _create_dispute(self, resolver: KlerosDisputeResolver) -> Dispute:
        return resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test dispute",
        )

    def test_submit_evidence(self):
        resolver = KlerosDisputeResolver()
        dispute = self._create_dispute(resolver)
        evidence = resolver.submit_evidence(
            dispute_id=dispute.dispute_id,
            submitted_by="alice",
            evidence_type=EvidenceType.DOCUMENT,
            title="Receipt",
            description="Payment receipt showing transfer",
        )
        assert isinstance(evidence, Evidence)
        assert evidence.dispute_id == dispute.dispute_id
        assert evidence.submitted_by == "alice"
        assert dispute.evidence_count == 1

    def test_submit_evidence_with_file(self):
        resolver = KlerosDisputeResolver()
        dispute = self._create_dispute(resolver)
        evidence = resolver.submit_evidence(
            dispute_id=dispute.dispute_id,
            submitted_by="bob",
            evidence_type=EvidenceType.SCREENSHOT,
            title="Delivery screenshot",
            description="Screenshot showing delivered item",
            file_uri="ipfs://QmXyz123",
            file_hash="abc123",
        )
        assert evidence.file_uri == "ipfs://QmXyz123"
        assert evidence.file_hash == "abc123"

    def test_submit_multiple_evidence(self):
        resolver = KlerosDisputeResolver()
        dispute = self._create_dispute(resolver)
        resolver.submit_evidence(
            dispute_id=dispute.dispute_id,
            submitted_by="alice",
            evidence_type=EvidenceType.DOCUMENT,
            title="Doc 1",
            description="First document",
        )
        resolver.submit_evidence(
            dispute_id=dispute.dispute_id,
            submitted_by="bob",
            evidence_type=EvidenceType.DELIVERY_PROOF,
            title="Delivery proof",
            description="Proof of delivery",
        )
        assert dispute.evidence_count == 2

    def test_evidence_updates_party_count(self):
        resolver = KlerosDisputeResolver()
        dispute = self._create_dispute(resolver)
        resolver.submit_evidence(
            dispute_id=dispute.dispute_id,
            submitted_by="alice",
            evidence_type=EvidenceType.DOCUMENT,
            title="Doc",
            description="Test",
        )
        assert dispute.claimant.evidence_submitted == 1
        assert dispute.respondent.evidence_submitted == 0

    def test_submit_evidence_not_found(self):
        resolver = KlerosDisputeResolver()
        with pytest.raises(ValueError, match="not found"):
            resolver.submit_evidence(
                dispute_id="fake",
                submitted_by="alice",
                evidence_type=EvidenceType.DOCUMENT,
                title="Doc",
                description="Test",
            )

    def test_submit_evidence_closed_period(self):
        resolver = KlerosDisputeResolver()
        dispute = self._create_dispute(resolver)
        resolver.advance_to_voting(dispute.dispute_id)
        with pytest.raises(ValueError, match="Cannot submit evidence"):
            resolver.submit_evidence(
                dispute_id=dispute.dispute_id,
                submitted_by="alice",
                evidence_type=EvidenceType.DOCUMENT,
                title="Late evidence",
                description="Should fail",
            )

    def test_evidence_uri(self):
        evidence = Evidence(
            evidence_id="ev_1",
            dispute_id="disp_1",
            submitted_by="alice",
            evidence_type=EvidenceType.DOCUMENT,
            title="Receipt",
            description="Payment receipt",
            file_uri="ipfs://QmTest",
            file_hash="hash123",
        )
        import json
        uri = json.loads(evidence.evidence_uri)
        assert uri["name"] == "Receipt"
        assert uri["fileURI"] == "ipfs://QmTest"


# ============ Voting and Ruling Tests ============


class TestRulings:
    def _setup_dispute_for_voting(self, resolver: KlerosDisputeResolver) -> Dispute:
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        resolver.advance_to_voting(dispute.dispute_id)
        return dispute

    def test_advance_to_voting(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        result = resolver.advance_to_voting(dispute.dispute_id)
        assert result.status == DisputeStatus.VOTE

    def test_advance_wrong_state(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        resolver.advance_to_voting(dispute.dispute_id)
        with pytest.raises(ValueError, match="Cannot advance"):
            resolver.advance_to_voting(dispute.dispute_id)

    def test_submit_ruling_claimant_wins(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_dispute_for_voting(resolver)
        result = resolver.submit_ruling(dispute.dispute_id, Ruling.CLAIMANT_WINS)
        assert isinstance(result, DisputeRulingResult)
        assert result.claimant_won is True
        assert result.respondent_won is False
        assert dispute.status == DisputeStatus.APPEAL

    def test_submit_ruling_respondent_wins(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_dispute_for_voting(resolver)
        result = resolver.submit_ruling(dispute.dispute_id, Ruling.RESPONDENT_WINS)
        assert result.respondent_won is True
        assert result.claimant_won is False

    def test_submit_ruling_refuse(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_dispute_for_voting(resolver)
        result = resolver.submit_ruling(dispute.dispute_id, Ruling.REFUSE_TO_RULE)
        assert result.refused_to_rule is True

    def test_ruling_not_found(self):
        resolver = KlerosDisputeResolver()
        with pytest.raises(ValueError, match="not found"):
            resolver.submit_ruling("fake", Ruling.CLAIMANT_WINS)

    def test_ruling_wrong_state(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        with pytest.raises(ValueError, match="Cannot rule"):
            resolver.submit_ruling(dispute.dispute_id, Ruling.CLAIMANT_WINS)

    def test_execute_ruling(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_dispute_for_voting(resolver)
        resolver.submit_ruling(dispute.dispute_id, Ruling.CLAIMANT_WINS)
        result = resolver.execute_ruling(dispute.dispute_id)
        assert result.executed is True
        assert result.appeal_possible is False
        assert dispute.status == DisputeStatus.RESOLVED
        assert dispute.is_active is False

    def test_execute_no_ruling(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_dispute_for_voting(resolver)
        with pytest.raises(ValueError, match="No ruling"):
            resolver.execute_ruling(dispute.dispute_id)


# ============ Appeal Tests ============


class TestAppeals:
    def _setup_ruled_dispute(self, resolver: KlerosDisputeResolver) -> Dispute:
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("5000"),
            reason="Test",
        )
        resolver.advance_to_voting(dispute.dispute_id)
        resolver.submit_ruling(dispute.dispute_id, Ruling.RESPONDENT_WINS)
        return dispute

    def test_appeal_ruling(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        resolver.appeal_ruling(dispute.dispute_id)
        assert dispute.status == DisputeStatus.EVIDENCE
        assert dispute.appeal_count == 1
        assert dispute.current_round == 2
        assert dispute.num_jurors == 7  # 3*2+1

    def test_appeal_resets_ruling(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        resolver.appeal_ruling(dispute.dispute_id)
        assert dispute.ruling is None

    def test_max_appeals(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        # Appeal 3 times (max)
        for _ in range(3):
            resolver.appeal_ruling(dispute.dispute_id)
            resolver.advance_to_voting(dispute.dispute_id)
            resolver.submit_ruling(dispute.dispute_id, Ruling.RESPONDENT_WINS)
        # 4th appeal should fail
        with pytest.raises(ValueError, match="Cannot appeal"):
            resolver.appeal_ruling(dispute.dispute_id)

    def test_juror_doubling(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        assert dispute.num_jurors == 3
        resolver.appeal_ruling(dispute.dispute_id)
        assert dispute.num_jurors == 7  # 3*2+1
        resolver.advance_to_voting(dispute.dispute_id)
        resolver.submit_ruling(dispute.dispute_id, Ruling.CLAIMANT_WINS)
        resolver.appeal_ruling(dispute.dispute_id)
        assert dispute.num_jurors == 15  # 7*2+1

    def test_is_appealable(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        assert dispute.is_appealable is True

    def test_not_appealable_resolved(self):
        resolver = KlerosDisputeResolver()
        dispute = self._setup_ruled_dispute(resolver)
        resolver.execute_ruling(dispute.dispute_id)
        assert dispute.is_appealable is False


# ============ Cancellation Tests ============


class TestCancellation:
    def test_cancel_dispute(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        result = resolver.cancel_dispute(dispute.dispute_id, "Parties settled")
        assert result.status == DisputeStatus.CANCELLED
        assert result.is_active is False

    def test_cancel_resolved_fails(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        resolver.advance_to_voting(dispute.dispute_id)
        resolver.submit_ruling(dispute.dispute_id, Ruling.CLAIMANT_WINS)
        resolver.execute_ruling(dispute.dispute_id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            resolver.cancel_dispute(dispute.dispute_id)

    def test_cancel_not_found(self):
        resolver = KlerosDisputeResolver()
        with pytest.raises(ValueError, match="not found"):
            resolver.cancel_dispute("fake")


# ============ Cost Estimation Tests ============


class TestCostEstimation:
    def test_basic_estimate(self):
        resolver = KlerosDisputeResolver()
        estimate = resolver.estimate_arbitration_cost()
        assert isinstance(estimate, ArbitrationCostEstimate)
        assert estimate.fee_eth > 0
        assert estimate.fee_usd_estimate > 0

    def test_escrow_court_cost(self):
        resolver = KlerosDisputeResolver(eth_price_usd=Decimal("3000"))
        estimate = resolver.estimate_arbitration_cost(
            court=CourtCategory.ESCROW,
            num_jurors=3,
        )
        expected_eth = Decimal("0.05") * 3
        assert estimate.fee_eth == expected_eth
        assert estimate.fee_usd_estimate == expected_eth * Decimal("3000")

    def test_economical_check(self):
        resolver = KlerosDisputeResolver(eth_price_usd=Decimal("3000"))
        estimate = resolver.estimate_arbitration_cost(
            court=CourtCategory.ESCROW,
            num_jurors=3,
            dispute_amount_usd=Decimal("10000"),
        )
        # fee = 0.05*3*3000 = $450, 10000 >= 450*3 = 1350 → economical
        assert estimate.is_economical is True

    def test_not_economical(self):
        resolver = KlerosDisputeResolver(eth_price_usd=Decimal("3000"))
        estimate = resolver.estimate_arbitration_cost(
            court=CourtCategory.ESCROW,
            num_jurors=3,
            dispute_amount_usd=Decimal("100"),
        )
        # fee = $450, 100 < 450*3 = 1350 → not economical
        assert estimate.is_economical is False


# ============ Listing Tests ============


class TestListDisputes:
    def test_list_active(self):
        resolver = KlerosDisputeResolver()
        d1 = resolver.create_dispute(
            claimant_id="a", respondent_id="b",
            amount_usd=Decimal("100"), reason="Test",
        )
        d2 = resolver.create_dispute(
            claimant_id="c", respondent_id="d",
            amount_usd=Decimal("200"), reason="Test2",
        )
        resolver.cancel_dispute(d2.dispute_id)
        active = resolver.list_active_disputes()
        assert len(active) == 1
        assert active[0].dispute_id == d1.dispute_id

    def test_list_by_escrow(self):
        resolver = KlerosDisputeResolver()
        resolver.create_dispute(
            claimant_id="a", respondent_id="b",
            amount_usd=Decimal("100"), reason="T1",
            escrow_id="esc_1",
        )
        resolver.create_dispute(
            claimant_id="c", respondent_id="d",
            amount_usd=Decimal("200"), reason="T2",
            escrow_id="esc_2",
        )
        disputes = resolver.list_disputes_for_escrow("esc_1")
        assert len(disputes) == 1


# ============ Calldata Tests ============


class TestCalldata:
    def test_create_dispute_calldata(self):
        calldata = build_create_dispute_calldata(
            num_jurors=3,
            subcourt_id=4,
            metadata_hash=b"\x01" * 32,
        )
        assert len(calldata) > 4
        assert calldata[:4] == bytes.fromhex("c13517e1")

    def test_submit_evidence_calldata(self):
        calldata = build_submit_evidence_calldata(
            dispute_id=42,
            evidence_uri="ipfs://QmTest123",
        )
        assert len(calldata) > 4
        assert calldata[:4] == bytes.fromhex("5bb5e54b")

    def test_appeal_calldata(self):
        calldata = build_appeal_calldata(dispute_id=42)
        assert len(calldata) > 4
        assert calldata[:4] == bytes.fromhex("44b22815")

    def test_rule_calldata(self):
        calldata = build_rule_calldata(dispute_id=42, ruling=1)
        assert len(calldata) == 68  # 4 + 32 + 32

    def test_get_dispute_calldata(self):
        resolver = KlerosDisputeResolver()
        dispute = resolver.create_dispute(
            claimant_id="alice",
            respondent_id="bob",
            amount_usd=Decimal("1000"),
            reason="Test",
        )
        calldata = resolver.get_dispute_calldata(dispute.dispute_id)
        assert calldata is not None
        assert len(calldata) > 4


# ============ Dispute Properties Tests ============


class TestDisputeProperties:
    def test_is_active_statuses(self):
        dispute = Dispute(dispute_id="1")
        assert dispute.is_active is True
        dispute.status = DisputeStatus.RESOLVED
        assert dispute.is_active is False
        dispute.status = DisputeStatus.CANCELLED
        assert dispute.is_active is False

    def test_can_submit_evidence(self):
        dispute = Dispute(dispute_id="1", status=DisputeStatus.EVIDENCE)
        assert dispute.can_submit_evidence is True
        dispute.status = DisputeStatus.VOTE
        assert dispute.can_submit_evidence is False

    def test_evidence_count(self):
        dispute = Dispute(dispute_id="1")
        assert dispute.evidence_count == 0


# ============ Enum Tests ============


class TestEnums:
    def test_dispute_statuses(self):
        assert len(DisputeStatus) == 7

    def test_rulings(self):
        assert Ruling.REFUSE_TO_RULE == 0
        assert Ruling.CLAIMANT_WINS == 1
        assert Ruling.RESPONDENT_WINS == 2

    def test_evidence_types(self):
        assert len(EvidenceType) == 8

    def test_court_categories(self):
        assert len(CourtCategory) == 6

    def test_party_roles(self):
        assert DisputePartyRole.CLAIMANT.value == "claimant"


# ============ Constants Tests ============


class TestConstants:
    def test_arbitrator_address(self):
        assert KLEROS_ARBITRATOR_ADDRESS.startswith("0x")

    def test_default_jurors(self):
        assert DEFAULT_NUM_JURORS == 3

    def test_default_evidence_period(self):
        assert DEFAULT_EVIDENCE_PERIOD_DAYS == 7

    def test_appeal_period(self):
        assert DEFAULT_APPEAL_PERIOD_DAYS == 3

    def test_min_dispute_amount(self):
        assert MIN_DISPUTE_AMOUNT_USD == Decimal("10")

    def test_fee_estimates(self):
        assert CourtCategory.ESCROW in ARBITRATION_FEE_ESTIMATES
        assert all(v > 0 for v in ARBITRATION_FEE_ESTIMATES.values())


# ============ Factory Tests ============


class TestFactory:
    def test_create_resolver(self):
        resolver = create_dispute_resolver()
        assert isinstance(resolver, KlerosDisputeResolver)

    def test_create_resolver_custom(self):
        resolver = create_dispute_resolver(
            default_court=CourtCategory.TECHNICAL,
            eth_price_usd=Decimal("4000"),
        )
        assert resolver._default_court == CourtCategory.TECHNICAL
        assert resolver._eth_price_usd == Decimal("4000")


# ============ Module Export Tests ============


class TestModuleExports:
    def test_imports_from_protocol(self):
        from sardis_protocol import (
            ArbitrationCostEstimate,
            CourtCategory,
            DisputeRulingResult,
            DisputeStatus,
            EvidenceType,
            KlerosDisputeResolver,
            Ruling,
            create_dispute_resolver,
        )
        assert all([
            ArbitrationCostEstimate, CourtCategory,
            DisputeRulingResult, DisputeStatus, EvidenceType,
            KlerosDisputeResolver, Ruling, create_dispute_resolver,
        ])
