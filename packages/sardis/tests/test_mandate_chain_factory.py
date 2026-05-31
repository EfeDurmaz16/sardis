"""Tests for the single typed mandate-chain factory.

The factory must produce REAL ``MandateChain`` objects that
``PaymentOrchestrator.execute_chain()`` accepts.  In the real domain model,
money is carried as integer *minor units* (``amount_minor``) and the currency
is the ``token`` field.  The factory's public contract takes ``Decimal`` money
(no float) and converts to minor units internally.
"""
from decimal import Decimal

import pytest

from sardis.core.mandate_chain_factory import build_mandate_chain
from sardis.core.mandates import CartMandate, IntentMandate, MandateChain, PaymentMandate


def test_build_mandate_chain_minimal():
    chain = build_mandate_chain(
        agent_id="agt_1",
        amount="12.34",
        currency="USDC",
        counterparty="0xabc",
        wallet_id="wal_1",
        mandate_id="md_1",
    )
    assert isinstance(chain, MandateChain)
    assert isinstance(chain.intent, IntentMandate)
    assert isinstance(chain.cart, CartMandate)
    assert isinstance(chain.payment, PaymentMandate)

    # execute_chain reads chain.payment.mandate_id
    assert chain.payment.mandate_id == "md_1"

    # 12.34 USDC (6 decimals) -> 12_340_000 minor units, computed via Decimal (no float)
    assert chain.payment.amount_minor == 12_340_000

    # currency maps to the payment token; counterparty -> destination
    assert chain.payment.token == "USDC"
    assert chain.payment.destination == "0xabc"
    assert chain.payment.wallet_id == "wal_1"

    # All three mandates must share the same subject (agent_id) for the
    # MandateChain.__post_init__ consistency check to pass.
    assert chain.intent.subject == "agt_1"
    assert chain.cart.subject == "agt_1"
    assert chain.payment.subject == "agt_1"


def test_amount_is_computed_with_decimal_not_float():
    # A value that is not exactly representable in float; Decimal must be used.
    chain = build_mandate_chain(
        agent_id="agt_2",
        amount=Decimal("0.10"),
        currency="USDC",
        counterparty="0xdef",
        wallet_id="wal_2",
        mandate_id="md_2",
    )
    # 0.10 USDC @ 6 decimals == 100_000 minor units exactly.
    assert chain.payment.amount_minor == 100_000


def test_bool_amount_rejected():
    # bool subclasses int — a money path must not silently accept True/False.
    with pytest.raises(TypeError):
        build_mandate_chain(
            agent_id="agt_b",
            amount=True,
            currency="USDC",
            counterparty="0xbool",
            wallet_id="wal_b",
            mandate_id="md_b",
        )


def test_mandate_id_generated_when_omitted():
    chain = build_mandate_chain(
        agent_id="agt_3",
        amount="1.00",
        currency="USDC",
        counterparty="0xfeed",
        wallet_id="wal_3",
    )
    assert chain.payment.mandate_id
    # intent/cart ids are derived from the (generated) payment mandate id.
    assert chain.intent.mandate_id != chain.payment.mandate_id
    assert chain.cart.mandate_id != chain.payment.mandate_id


def test_decimals_override_for_non_usdc():
    # EURC-like token with 2 decimals.
    chain = build_mandate_chain(
        agent_id="agt_4",
        amount="5.00",
        currency="FOO",
        counterparty="0xbar",
        wallet_id="wal_4",
        mandate_id="md_4",
        decimals=2,
    )
    assert chain.payment.amount_minor == 500


def test_agent_id_set_on_payment_for_orchestrator_lookups():
    """P1-1: the orchestrator reads ``payment.agent_id`` / ``payment.from_agent``
    for KYA, fastpath, group policy and the agent-scoped spending-mandate lookup.

    The factory only stores the acting agent on ``subject`` historically, so
    those orchestrator code paths were silently skipped on factory-built chains.
    The acting agent must be exposed as ``payment.agent_id``.
    """
    chain = build_mandate_chain(
        agent_id="agt_acting",
        amount="10.00",
        currency="USDC",
        counterparty="0xabc",
        wallet_id="wal_x",
        mandate_id="md_x",
    )
    assert chain.payment.agent_id == "agt_acting"
    # The orchestrator's `agent_id or from_agent` read must resolve the agent.
    resolved = getattr(chain.payment, "agent_id", None) or getattr(
        chain.payment, "from_agent", None
    )
    assert resolved == "agt_acting"


def test_passes_orchestrator_post_init_validation():
    # Building must not raise the MandateChain.__post_init__ ValueError
    # (same subject, ordered expirations, payment <= cart total).
    chain = build_mandate_chain(
        agent_id="agt_5",
        amount="100.00",
        currency="USDC",
        counterparty="0xabc",
        wallet_id="wal_5",
        mandate_id="md_5",
    )
    cart_total = chain.cart.subtotal_minor + chain.cart.taxes_minor
    assert chain.payment.amount_minor <= cart_total
    assert chain.intent.expires_at <= chain.cart.expires_at <= chain.payment.expires_at
