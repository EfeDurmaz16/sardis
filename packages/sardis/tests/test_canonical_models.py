"""Lock the canonical-model single-source-of-truth contract.

These tests assert that `sardis.canonical_models` re-exports the SAME class
objects as the engine (`sardis.core`) and SDK (`sardis.models`) layers — i.e.
it introduces no new types and changes no field shape. If someone later
collapses the layers, these identity assertions are the first thing to update,
forcing an intentional decision rather than silent drift.
"""
from __future__ import annotations

import sardis.canonical_models as cm
from sardis import core as engine
from sardis import models as sdk


def test_engine_names_are_core_classes() -> None:
    assert cm.EngineAgent is engine.Agent
    assert cm.EngineWallet is engine.Wallet
    assert cm.EnginePayment is engine.PaymentObject
    assert cm.EngineAgentGroup is engine.AgentGroup
    assert cm.EngineTokenLimit is engine.TokenLimit
    assert cm.EngineTokenBalance is engine.TokenBalance
    assert cm.AgentPolicy is engine.AgentPolicy
    assert cm.SpendingLimits is engine.SpendingLimits


def test_sdk_names_are_model_classes() -> None:
    assert cm.SdkAgent is sdk.Agent
    assert cm.SdkWallet is sdk.Wallet
    assert cm.SdkPayment is sdk.Payment
    assert cm.SdkPaymentStatus is sdk.PaymentStatus
    assert cm.SdkAgentGroup is sdk.AgentGroupModel
    assert cm.SdkTokenLimit is sdk.TokenLimit
    assert cm.SdkTokenBalance is sdk.TokenBalance


def test_bare_canonical_names_resolve_to_engine_domain() -> None:
    # Engine is authoritative on the money path / orchestrator / apps-api.
    assert cm.Agent is engine.Agent
    assert cm.Wallet is engine.Wallet
    assert cm.Payment is engine.PaymentObject
    assert cm.AgentGroup is engine.AgentGroup
    assert cm.TokenLimit is engine.TokenLimit
    assert cm.TokenBalance is engine.TokenBalance


def test_engine_and_sdk_layers_are_distinct() -> None:
    # The two layers are a DTO-vs-domain split, not duplicates: distinct classes.
    assert cm.EngineAgent is not cm.SdkAgent
    assert cm.EngineWallet is not cm.SdkWallet
    assert cm.EnginePayment is not cm.SdkPayment


def test_money_safety_state_lives_only_on_engine_wallet() -> None:
    # Wallet freeze is a money-safety control that must NOT leak into the public DTO.
    # This is why the pair is intentionally NOT collapsed (DONE_WITH_CONCERNS).
    assert hasattr(cm.EngineWallet, "freeze")
    assert "is_frozen" in cm.EngineWallet.model_fields
    assert "is_frozen" not in cm.SdkWallet.model_fields
