"""Tests for pipeline hooks extracted from ControlPlane.

Covers AGIT, KYA, and FIDES hooks — approve, reject, skip, and error paths.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sardis_v2_core.hooks import create_agit_hook, create_fides_hook, create_kya_hook
from sardis_v2_core.pre_execution_pipeline import PreExecutionPipeline


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

@dataclass
class StubIntent:
    """Minimal intent stub matching ExecutionIntent interface."""
    agent_id: str = "agent_001"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StubPolicyChainVerification:
    valid: bool
    chain_length: int
    broken_at: int | None = None
    error: str | None = None


class StubAgitEngine:
    """Synchronous stub for AgitPolicyEngine."""

    def __init__(self, verification: StubPolicyChainVerification):
        self._verification = verification

    def verify_policy_chain(self, agent_id: str) -> StubPolicyChainVerification:
        return self._verification


class ErrorAgitEngine:
    """AgitPolicyEngine stub that always raises."""

    def verify_policy_chain(self, agent_id: str):
        raise RuntimeError("AGIT unavailable")


@dataclass
class StubTrustScore:
    overall: float
    tier: StubTrustTier


class StubTrustTier:
    def __init__(self, value: str):
        self.value = value


def _make_trust_scorer(overall: float, tier_value: str = "medium"):
    """Return an async mock TrustScorer."""
    score = StubTrustScore(overall=overall, tier=StubTrustTier(tier_value))
    scorer = AsyncMock()
    scorer.calculate_trust = AsyncMock(return_value=score)
    return scorer


def _make_error_trust_scorer():
    """Return a TrustScorer that always raises."""
    scorer = AsyncMock()
    scorer.calculate_trust = AsyncMock(side_effect=RuntimeError("scorer down"))
    return scorer


# ===========================================================================
# AGIT hook tests
# ===========================================================================


class TestAgitHook:

    @pytest.mark.asyncio
    async def test_approve_valid_chain(self):
        engine = StubAgitEngine(StubPolicyChainVerification(valid=True, chain_length=5))
        hook = create_agit_hook(engine)
        result = await hook(StubIntent())

        assert result.decision == "approve"
        assert result.evidence["agit"] == "valid"
        assert result.evidence["chain_length"] == 5

    @pytest.mark.asyncio
    async def test_reject_tampered_chain(self):
        engine = StubAgitEngine(
            StubPolicyChainVerification(valid=False, chain_length=3, broken_at=2, error="hash mismatch")
        )
        hook = create_agit_hook(engine)
        result = await hook(StubIntent())

        assert result.decision == "reject"
        assert result.reason == "policy_chain_tampered"
        assert result.evidence["broken_at"] == 2
        assert result.evidence["chain_length"] == 3

    @pytest.mark.asyncio
    async def test_skip_no_agent_id(self):
        engine = StubAgitEngine(StubPolicyChainVerification(valid=True, chain_length=0))
        hook = create_agit_hook(engine)
        result = await hook(StubIntent(agent_id=""))

        assert result.decision == "skip"
        assert "no agent_id" in result.reason

    @pytest.mark.asyncio
    async def test_error_fail_closed(self):
        hook = create_agit_hook(ErrorAgitEngine(), fail_open=False)
        result = await hook(StubIntent())

        assert result.decision == "reject"
        assert "AGIT policy verification unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_error_fail_open(self):
        hook = create_agit_hook(ErrorAgitEngine(), fail_open=True)
        result = await hook(StubIntent())

        assert result.decision == "skip"
        assert "fail-open" in result.reason

    @pytest.mark.asyncio
    async def test_hook_has_name(self):
        engine = StubAgitEngine(StubPolicyChainVerification(valid=True, chain_length=0))
        hook = create_agit_hook(engine)
        assert hook.__name__ == "agit_hook"


# ===========================================================================
# KYA hook tests
# ===========================================================================


class TestKyaHook:

    @pytest.mark.asyncio
    async def test_approve_sufficient_trust(self):
        scorer = _make_trust_scorer(0.8, "high")
        hook = create_kya_hook(scorer, min_trust=0.3)
        result = await hook(StubIntent())

        assert result.decision == "approve"
        assert result.evidence["trust_score"] == 0.8
        assert result.evidence["trust_tier"] == "high"

    @pytest.mark.asyncio
    async def test_reject_insufficient_trust(self):
        scorer = _make_trust_scorer(0.1, "untrusted")
        hook = create_kya_hook(scorer, min_trust=0.3)
        result = await hook(StubIntent())

        assert result.decision == "reject"
        assert "trust_score_insufficient" in result.reason
        assert result.evidence["trust_score"] == 0.1
        assert result.evidence["min_required"] == 0.3

    @pytest.mark.asyncio
    async def test_reject_exactly_at_boundary(self):
        """Score exactly equal to min_trust should NOT reject (>= semantics via <)."""
        scorer = _make_trust_scorer(0.3, "low")
        hook = create_kya_hook(scorer, min_trust=0.3)
        result = await hook(StubIntent())

        assert result.decision == "approve"

    @pytest.mark.asyncio
    async def test_skip_no_agent_id(self):
        scorer = _make_trust_scorer(0.5)
        hook = create_kya_hook(scorer)
        result = await hook(StubIntent(agent_id=""))

        assert result.decision == "skip"

    @pytest.mark.asyncio
    async def test_error_fail_open(self):
        scorer = _make_error_trust_scorer()
        hook = create_kya_hook(scorer, fail_open=True)
        result = await hook(StubIntent())

        assert result.decision == "skip"
        assert "unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_error_fail_closed(self):
        scorer = _make_error_trust_scorer()
        hook = create_kya_hook(scorer, fail_open=False)
        result = await hook(StubIntent())

        assert result.decision == "reject"
        assert "unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_hook_has_name(self):
        hook = create_kya_hook(_make_trust_scorer(0.5))
        assert hook.__name__ == "kya_hook"

    @pytest.mark.asyncio
    async def test_passes_agent_did_from_metadata(self):
        scorer = _make_trust_scorer(0.8, "high")
        hook = create_kya_hook(scorer)
        intent = StubIntent(metadata={"fides_did": "did:fides:agent42"})
        await hook(intent)

        scorer.calculate_trust.assert_awaited_once_with(
            agent_id="agent_001",
            agent_did="did:fides:agent42",
        )


# ===========================================================================
# FIDES hook tests
# ===========================================================================


class TestFidesHook:

    @pytest.mark.asyncio
    async def test_approve_sufficient_trust(self):
        scorer = _make_trust_scorer(0.7, "high")
        hook = create_fides_hook(scorer, min_trust=0.3)
        intent = StubIntent(metadata={"fides_did": "did:fides:agent_001"})
        result = await hook(intent)

        assert result.decision == "approve"
        assert result.evidence["trust_score"] == 0.7
        assert result.evidence["fides_did"] == "did:fides:agent_001"

    @pytest.mark.asyncio
    async def test_reject_insufficient_trust(self):
        scorer = _make_trust_scorer(0.1, "untrusted")
        hook = create_fides_hook(scorer, min_trust=0.3)
        intent = StubIntent(metadata={"fides_did": "did:fides:agent_001"})
        result = await hook(intent)

        assert result.decision == "reject"
        assert "trust_score_insufficient" in result.reason
        assert result.evidence["trust_score"] == 0.1
        assert result.evidence["fides_did"] == "did:fides:agent_001"

    @pytest.mark.asyncio
    async def test_skip_no_fides_did(self):
        scorer = _make_trust_scorer(0.5)
        hook = create_fides_hook(scorer)
        result = await hook(StubIntent())

        assert result.decision == "skip"
        assert "no fides_did" in result.reason
        scorer.calculate_trust.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_fail_open(self):
        scorer = _make_error_trust_scorer()
        hook = create_fides_hook(scorer, fail_open=True)
        intent = StubIntent(metadata={"fides_did": "did:fides:agent_001"})
        result = await hook(intent)

        assert result.decision == "skip"
        assert "unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_error_fail_closed(self):
        scorer = _make_error_trust_scorer()
        hook = create_fides_hook(scorer, fail_open=False)
        intent = StubIntent(metadata={"fides_did": "did:fides:agent_001"})
        result = await hook(intent)

        assert result.decision == "reject"
        assert "unavailable" in result.reason

    @pytest.mark.asyncio
    async def test_hook_has_name(self):
        hook = create_fides_hook(_make_trust_scorer(0.5))
        assert hook.__name__ == "fides_hook"

    @pytest.mark.asyncio
    async def test_passes_fides_did_to_scorer(self):
        scorer = _make_trust_scorer(0.8, "high")
        hook = create_fides_hook(scorer)
        intent = StubIntent(metadata={"fides_did": "did:fides:test123"})
        await hook(intent)

        scorer.calculate_trust.assert_awaited_once_with(
            agent_id="agent_001",
            agent_did="did:fides:test123",
        )


# ===========================================================================
# Pipeline integration: compose all three hooks
# ===========================================================================


class TestPipelineIntegration:

    @pytest.mark.asyncio
    async def test_all_hooks_approve(self):
        agit = StubAgitEngine(StubPolicyChainVerification(valid=True, chain_length=3))
        kya_scorer = _make_trust_scorer(0.8, "high")
        fides_scorer = _make_trust_scorer(0.7, "high")

        pipeline = PreExecutionPipeline(hooks=[
            create_agit_hook(agit),
            create_kya_hook(kya_scorer, min_trust=0.3),
            create_fides_hook(fides_scorer, min_trust=0.3),
        ])

        intent = StubIntent(metadata={"fides_did": "did:fides:agent_001"})
        result = await pipeline.evaluate(intent)

        assert result.decision == "approve"

    @pytest.mark.asyncio
    async def test_agit_rejects_short_circuits(self):
        agit = StubAgitEngine(
            StubPolicyChainVerification(valid=False, chain_length=2, broken_at=1)
        )
        kya_scorer = _make_trust_scorer(0.8, "high")

        pipeline = PreExecutionPipeline(hooks=[
            create_agit_hook(agit),
            create_kya_hook(kya_scorer),
        ])

        result = await pipeline.evaluate(StubIntent())

        assert result.decision == "reject"
        assert "policy_chain_tampered" in result.reason
        # KYA scorer should never have been called
        kya_scorer.calculate_trust.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fides_skip_allows_pipeline_to_continue(self):
        """When intent has no fides_did, fides hook skips and pipeline approves."""
        agit = StubAgitEngine(StubPolicyChainVerification(valid=True, chain_length=1))
        kya_scorer = _make_trust_scorer(0.6, "medium")
        fides_scorer = _make_trust_scorer(0.5, "medium")

        pipeline = PreExecutionPipeline(hooks=[
            create_agit_hook(agit),
            create_kya_hook(kya_scorer, min_trust=0.3),
            create_fides_hook(fides_scorer, min_trust=0.3),
        ])

        # No fides_did in metadata -> fides hook skips
        result = await pipeline.evaluate(StubIntent())

        assert result.decision == "approve"


# ===========================================================================
# ControlPlane deprecation warning
# ===========================================================================


class TestControlPlaneDeprecation:

    @pytest.mark.asyncio
    async def test_submit_emits_deprecation_warning(self):
        from sardis_v2_core.control_plane import ControlPlane

        cp = ControlPlane()
        from sardis_v2_core.execution_intent import ExecutionIntent

        intent = ExecutionIntent(agent_id="agent_001")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            await cp.submit(intent)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()
            assert "PaymentOrchestrator" in str(deprecation_warnings[0].message)
