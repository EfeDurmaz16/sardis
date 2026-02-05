"""Test F22: Remove duplicate compliance check from executor.

Ensures dispatch_payment does NOT perform compliance checks - that's the
orchestrator's responsibility (Phase 2).
"""
import inspect


def test_dispatch_payment_does_not_call_compliance():
    """dispatch_payment source must not contain compliance preflight calls."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor.dispatch_payment)
    assert "_check_compliance_preflight" not in source, (
        "dispatch_payment must not call _check_compliance_preflight"
    )
    assert "_check_sanctions" not in source, (
        "dispatch_payment must not call _check_sanctions"
    )


def test_dispatch_payment_docstring_mentions_orchestrator():
    """dispatch_payment docstring should clarify orchestrator handles compliance."""
    from sardis_chain.executor import ChainExecutor
    docstring = ChainExecutor.dispatch_payment.__doc__ or ""
    assert "orchestrator" in docstring.lower(), (
        "Docstring should mention that orchestrator handles compliance"
    )


def test_dispatch_payment_docstring_no_compliance_claims():
    """dispatch_payment docstring must not claim to perform compliance."""
    from sardis_chain.executor import ChainExecutor
    docstring = (ChainExecutor.dispatch_payment.__doc__ or "").lower()
    assert "compliance preflight check passes" not in docstring
    assert "sanctions screening passes" not in docstring


def test_live_payment_path_no_compliance():
    """The live payment execution path must not contain compliance calls."""
    from sardis_chain.executor import ChainExecutor
    source = inspect.getsource(ChainExecutor._execute_live_payment_with_gas_protection)
    assert "_check_compliance_preflight" not in source, (
        "_execute_live_payment_with_gas_protection must not call compliance preflight"
    )
    assert "_check_sanctions" not in source, (
        "_execute_live_payment_with_gas_protection must not call sanctions check"
    )
