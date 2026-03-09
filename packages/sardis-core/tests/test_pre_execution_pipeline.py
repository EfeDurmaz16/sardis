"""Tests for the PreExecutionPipeline composable authorization hook system."""

from __future__ import annotations

import pytest

from sardis_v2_core.pre_execution_pipeline import HookResult, PreExecutionPipeline


@pytest.mark.asyncio
async def test_empty_pipeline_approves():
    """An empty pipeline (no hooks) should return approve."""
    pipeline = PreExecutionPipeline()
    result = await pipeline.evaluate({"amount": "100"})

    assert result.decision == "approve"
    assert result.reason == ""


@pytest.mark.asyncio
async def test_pipeline_runs_all_hooks_in_order():
    """Hooks run sequentially; all-approve yields final approve."""
    call_order: list[str] = []

    async def hook_a(intent) -> HookResult:
        call_order.append("a")
        return HookResult(decision="approve", reason="hook_a ok")

    async def hook_b(intent) -> HookResult:
        call_order.append("b")
        return HookResult(decision="approve", reason="hook_b ok")

    async def hook_c(intent) -> HookResult:
        call_order.append("c")
        return HookResult(decision="approve", reason="hook_c ok")

    pipeline = PreExecutionPipeline(hooks=[hook_a, hook_b, hook_c])
    result = await pipeline.evaluate({"amount": "50"})

    assert result.decision == "approve"
    assert call_order == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_pipeline_stops_on_first_rejection():
    """First reject short-circuits; later hooks are never called."""
    call_order: list[str] = []

    async def hook_a(intent) -> HookResult:
        call_order.append("a")
        return HookResult(decision="approve")

    async def hook_b(intent) -> HookResult:
        call_order.append("b")
        return HookResult(
            decision="reject",
            reason="over limit",
            evidence={"limit": 1000, "requested": 2000},
        )

    async def hook_c(intent) -> HookResult:
        call_order.append("c")
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline(hooks=[hook_a, hook_b, hook_c])
    result = await pipeline.evaluate({"amount": "2000"})

    assert result.decision == "reject"
    assert result.reason == "over limit"
    assert result.evidence == {"limit": 1000, "requested": 2000}
    assert call_order == ["a", "b"]  # hook_c never called


@pytest.mark.asyncio
async def test_pipeline_skip_does_not_block():
    """Skip results are ignored; pipeline continues to next hook."""
    call_order: list[str] = []

    async def hook_skip(intent) -> HookResult:
        call_order.append("skip")
        return HookResult(decision="skip", reason="not applicable")

    async def hook_approve(intent) -> HookResult:
        call_order.append("approve")
        return HookResult(decision="approve", reason="all good")

    pipeline = PreExecutionPipeline(hooks=[hook_skip, hook_approve])
    result = await pipeline.evaluate({"amount": "10"})

    assert result.decision == "approve"
    assert call_order == ["skip", "approve"]


@pytest.mark.asyncio
async def test_pipeline_hook_error_rejects():
    """An exception in a hook results in a reject (fail-closed)."""

    async def bad_hook(intent) -> HookResult:
        raise RuntimeError("connection timeout")

    async def never_called(intent) -> HookResult:
        raise AssertionError("should not be reached")

    pipeline = PreExecutionPipeline(hooks=[bad_hook, never_called])
    result = await pipeline.evaluate({"amount": "10"})

    assert result.decision == "reject"
    assert "Hook error" in result.reason
    assert "connection timeout" in result.reason


@pytest.mark.asyncio
async def test_add_hook_dynamically():
    """Hooks added via add_hook() are appended and run in order."""
    call_order: list[str] = []

    async def hook_a(intent) -> HookResult:
        call_order.append("a")
        return HookResult(decision="approve")

    async def hook_b(intent) -> HookResult:
        call_order.append("b")
        return HookResult(decision="approve")

    pipeline = PreExecutionPipeline()
    pipeline.add_hook(hook_a)
    pipeline.add_hook(hook_b)

    result = await pipeline.evaluate({})

    assert result.decision == "approve"
    assert call_order == ["a", "b"]


@pytest.mark.asyncio
async def test_all_skip_results_in_approve():
    """If every hook skips, the pipeline should still approve."""

    async def skip_hook(intent) -> HookResult:
        return HookResult(decision="skip")

    pipeline = PreExecutionPipeline(hooks=[skip_hook, skip_hook])
    result = await pipeline.evaluate({})

    assert result.decision == "approve"


@pytest.mark.asyncio
async def test_hook_receives_intent_object():
    """Hooks receive the intent argument passed to evaluate()."""
    captured_intents: list = []

    async def capture_hook(intent) -> HookResult:
        captured_intents.append(intent)
        return HookResult(decision="approve")

    intent_data = {"agent_id": "agent_123", "amount": "500"}
    pipeline = PreExecutionPipeline(hooks=[capture_hook])
    await pipeline.evaluate(intent_data)

    assert len(captured_intents) == 1
    assert captured_intents[0] is intent_data
