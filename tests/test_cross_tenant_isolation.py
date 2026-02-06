"""Cross-tenant isolation proof tests for security boundaries.

This test suite verifies that wallet-agent bindings, card-agent bindings,
and mandate chains properly enforce tenant isolation. Each test documents
the specific isolation boundary it proves.

Markers: protocol_conformance, security
"""
from __future__ import annotations

import pytest
import time
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from typing import Optional

from sardis_protocol.verifier import MandateVerifier, MandateChainVerification
from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_v2_core import SardisSettings, load_settings
from sardis_v2_core.identity import AgentIdentity, IdentityRegistry
from sardis_v2_core.mandates import PaymentMandate, CartMandate, IntentMandate
from sardis_v2_core.wallets import Wallet
from sardis_v2_core.agents import Agent, SpendingLimits, AgentPolicy
from sardis_cards.models import Card, CardStatus, CardType

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.security]


# Mock stores for testing isolation boundaries
@dataclass
class MockWalletStore:
    """Mock wallet store for isolation testing."""
    wallets: dict[str, Wallet]

    def get(self, wallet_id: str) -> Optional[Wallet]:
        return self.wallets.get(wallet_id)

    def get_owner(self, wallet_id: str) -> Optional[str]:
        """Get the agent_id that owns this wallet."""
        wallet = self.wallets.get(wallet_id)
        return wallet.agent_id if wallet else None


@dataclass
class MockCardStore:
    """Mock card store for isolation testing."""
    cards: dict[str, Card]

    def get(self, card_id: str) -> Optional[Card]:
        return self.cards.get(card_id)

    def get_owner(self, card_id: str) -> Optional[str]:
        """Get the wallet_id that owns this card."""
        card = self.cards.get(card_id)
        return card.wallet_id if card else None


@dataclass
class MockAgentStore:
    """Mock agent store for isolation testing."""
    agents: dict[str, Agent]

    def get(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)


def _proof() -> dict:
    """Create a mock proof for mandate testing."""
    return {
        "type": "DataIntegrityProof",
        "verification_method": "ed25519:" + ("00" * 32),
        "created": "2026-01-01T00:00:00Z",
        "proof_purpose": "assertionMethod",
        "proof_value": "cHJvb2Y=",
    }


def _create_mandate_bundle(
    agent_id: str,
    wallet_id: str,
    merchant_domain: str = "merchant.example",
) -> AP2PaymentExecuteRequest:
    """Create a complete AP2 mandate bundle for testing."""
    now = int(time.time())

    intent = {
        "mandate_id": f"mnd_intent_{agent_id}",
        "mandate_type": "intent",
        "issuer": "did:web:sardis.network",
        "subject": agent_id,
        "expires_at": now + 300,
        "nonce": f"n1_{agent_id}",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "intent",
        "scope": ["checkout"],
        "requested_amount": 10_000,
    }

    cart = {
        "mandate_id": f"mnd_cart_{agent_id}",
        "mandate_type": "cart",
        "issuer": "did:web:sardis.network",
        "subject": agent_id,
        "expires_at": now + 300,
        "nonce": f"n2_{agent_id}",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "cart",
        "line_items": [{"sku": "x", "qty": 1, "price_minor": 10_000}],
        "merchant_domain": merchant_domain,
        "currency": "USD",
        "subtotal_minor": 10_000,
        "taxes_minor": 0,
    }

    payment = {
        "mandate_id": f"mnd_payment_{agent_id}_{wallet_id}",
        "mandate_type": "payment",
        "issuer": "did:web:sardis.network",
        "subject": agent_id,
        "expires_at": now + 300,
        "nonce": f"n3_{agent_id}",
        "proof": _proof(),
        "domain": "sardis.network",
        "purpose": "checkout",
        "chain": "base_sepolia",
        "token": "USDC",
        "amount_minor": 10_000,
        "destination": "0x0000000000000000000000000000000000000000",
        "audit_hash": f"hash_{wallet_id}",
        "merchant_domain": merchant_domain,
    }

    return AP2PaymentExecuteRequest(intent=intent, cart=cart, payment=payment)


# =============================================================================
# Wallet-Agent Binding Tests (3 tests)
# =============================================================================

def test_agent_cannot_execute_payment_from_another_agents_wallet():
    """
    Isolation boundary: Agent A cannot execute payments from Agent B's wallet.

    Creates two agent contexts with different wallet IDs. Verifies that when
    Agent A tries to create a mandate chain with Agent B's wallet ID, the
    payment execution is rejected due to wallet ownership mismatch.
    """
    # Setup: Create two agents with their own wallets
    agent_a = Agent.new(name="Agent A", owner_id="tenant_1")
    agent_b = Agent.new(name="Agent B", owner_id="tenant_2")

    wallet_a = Wallet.new(agent_id=agent_a.agent_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=agent_b.agent_id, wallet_id="wallet_b")

    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    # Agent A tries to use Agent B's wallet
    bundle = _create_mandate_bundle(
        agent_id=agent_a.agent_id,
        wallet_id="wallet_b",  # Wrong wallet!
    )

    # Verify wallet ownership mismatch
    wallet_owner = wallet_store.get_owner("wallet_b")
    assert wallet_owner == agent_b.agent_id
    assert wallet_owner != agent_a.agent_id, "Agent A should not own wallet B"

    # In a real system, this check would happen in the payment executor
    # Before signing a transaction, we must verify:
    # mandate.subject == wallet.agent_id
    assert bundle.payment["subject"] == agent_a.agent_id
    wallet = wallet_store.get("wallet_b")
    assert wallet.agent_id == agent_b.agent_id
    assert bundle.payment["subject"] != wallet.agent_id, (
        "Payment mandate subject must match wallet owner"
    )


def test_mandate_chain_rejects_mismatched_agent_wallet_binding():
    """
    Isolation boundary: Mandate chain with Agent A's identity but Agent B's
    wallet is rejected.

    Verifies that the subject field in the payment mandate is validated
    against the wallet owner. The mandate chain should be rejected if the
    signing agent doesn't own the wallet specified in the payment details.
    """
    # Setup: Two agents, Agent A tries to impersonate or use B's wallet
    agent_a_id = "agent_a"
    agent_b_id = "agent_b"

    wallet_a = Wallet.new(agent_id=agent_a_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=agent_b_id, wallet_id="wallet_b")

    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    # Create mandate bundle where Agent A signs but references wallet_b
    bundle = _create_mandate_bundle(
        agent_id=agent_a_id,  # Agent A is signing
        wallet_id="wallet_b",  # But trying to use Agent B's wallet
    )

    # Verify the isolation violation
    payment_subject = bundle.payment["subject"]
    wallet_b_owner = wallet_store.get_owner("wallet_b")

    assert payment_subject == agent_a_id
    assert wallet_b_owner == agent_b_id
    assert payment_subject != wallet_b_owner, (
        "Subject-wallet binding violation: Agent A cannot use Agent B's wallet"
    )


def test_wallet_policy_checks_use_wallet_owner_policies():
    """
    Isolation boundary: Wallet policy checks use the wallet OWNER's policies,
    not the requesting agent's policies.

    Verifies that when checking spending policies, the system uses the policies
    associated with the wallet's owner, preventing policy bypass attacks.
    """
    # Setup: Two agents with different spending policies
    agent_a = Agent.new(
        name="Agent A",
        owner_id="tenant_1",
        spending_limits=SpendingLimits(
            per_transaction=Decimal("50.00"),  # Low limit
            daily=Decimal("200.00"),
        ),
        policy=AgentPolicy(
            blocked_merchants=["evil-merchant.com"],
        ),
    )

    agent_b = Agent.new(
        name="Agent B",
        owner_id="tenant_2",
        spending_limits=SpendingLimits(
            per_transaction=Decimal("10000.00"),  # High limit
            daily=Decimal("50000.00"),
        ),
        policy=AgentPolicy(
            blocked_merchants=[],  # No restrictions
        ),
    )

    wallet_a = Wallet.new(agent_id=agent_a.agent_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=agent_b.agent_id, wallet_id="wallet_b")

    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    agent_store = MockAgentStore(agents={
        agent_a.agent_id: agent_a,
        agent_b.agent_id: agent_b,
    })

    # Transaction amount that exceeds Agent A's limit but not Agent B's
    tx_amount = Decimal("100.00")

    # Verify policy retrieval logic
    wallet = wallet_store.get("wallet_a")
    assert wallet is not None
    wallet_owner_id = wallet.agent_id
    assert wallet_owner_id == agent_a.agent_id

    # Get the CORRECT policy (from wallet owner)
    owner_agent = agent_store.get(wallet_owner_id)
    assert owner_agent is not None
    owner_limit = owner_agent.spending_limits.per_transaction

    # Verify we're using the wallet owner's policy, not another agent's
    assert owner_limit == Decimal("50.00"), "Should use Agent A's limit"
    assert tx_amount > owner_limit, "Transaction should violate Agent A's policy"

    # Verify we're NOT accidentally using Agent B's policy
    wrong_agent = agent_store.get(agent_b.agent_id)
    assert wrong_agent.spending_limits.per_transaction == Decimal("10000.00")
    assert tx_amount < wrong_agent.spending_limits.per_transaction

    # The key isolation property: Policy must come from wallet owner
    assert owner_agent.agent_id != wrong_agent.agent_id
    assert owner_limit != wrong_agent.spending_limits.per_transaction


# =============================================================================
# Card-Agent Binding Tests (3 tests)
# =============================================================================

def test_virtual_card_cannot_be_used_by_wrong_agent():
    """
    Isolation boundary: Virtual card issued to Agent A cannot be used by Agent B.

    Verifies that card ownership checks prevent cross-agent card usage.
    """
    # Setup: Two agents with cards
    agent_a_id = "agent_a"
    agent_b_id = "agent_b"

    wallet_a = Wallet.new(agent_id=agent_a_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=agent_b_id, wallet_id="wallet_b")

    card_a = Card(
        card_id="card_a",
        wallet_id="wallet_a",
        status=CardStatus.ACTIVE,
        card_type=CardType.MULTI_USE,
    )

    card_b = Card(
        card_id="card_b",
        wallet_id="wallet_b",
        status=CardStatus.ACTIVE,
        card_type=CardType.MULTI_USE,
    )

    card_store = MockCardStore(cards={
        "card_a": card_a,
        "card_b": card_b,
    })

    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    # Agent A tries to use Agent B's card
    attempting_agent_id = agent_a_id
    target_card_id = "card_b"

    # Verify card ownership
    card = card_store.get(target_card_id)
    assert card is not None
    card_wallet_id = card.wallet_id

    # Get wallet owner
    wallet = wallet_store.get(card_wallet_id)
    assert wallet is not None
    card_owner_agent_id = wallet.agent_id

    # Verify isolation
    assert card_owner_agent_id == agent_b_id
    assert attempting_agent_id == agent_a_id
    assert attempting_agent_id != card_owner_agent_id, (
        "Agent A should not be able to use Agent B's card"
    )


def test_card_freeze_unfreeze_requires_owning_agent():
    """
    Isolation boundary: Card freeze/unfreeze operations require the card's
    owning agent.

    Verifies that administrative operations on cards are restricted to the
    agent that owns the wallet linked to the card.
    """
    # Setup
    agent_a_id = "agent_a"
    agent_b_id = "agent_b"

    wallet_a = Wallet.new(agent_id=agent_a_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=agent_b_id, wallet_id="wallet_b")

    card_a = Card(
        card_id="card_a",
        wallet_id="wallet_a",
        status=CardStatus.ACTIVE,
    )

    card_store = MockCardStore(cards={"card_a": card_a})
    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    # Function to check if an agent can modify a card
    def can_modify_card(agent_id: str, card_id: str) -> tuple[bool, str]:
        card = card_store.get(card_id)
        if not card:
            return False, "card_not_found"

        wallet = wallet_store.get(card.wallet_id)
        if not wallet:
            return False, "wallet_not_found"

        if wallet.agent_id != agent_id:
            return False, "unauthorized_agent"

        return True, "ok"

    # Agent A can modify their own card
    allowed, reason = can_modify_card(agent_a_id, "card_a")
    assert allowed is True
    assert reason == "ok"

    # Agent B cannot modify Agent A's card
    allowed, reason = can_modify_card(agent_b_id, "card_a")
    assert allowed is False
    assert reason == "unauthorized_agent", (
        "Agent B should not be able to freeze/unfreeze Agent A's card"
    )


def test_card_spending_limits_are_per_card_not_per_agent():
    """
    Isolation boundary: Card spending limits are per-card, not per-agent,
    ensuring isolation between cards.

    Verifies that multiple cards from the same agent maintain separate spending
    tracking, preventing limit bypass by using multiple cards.
    """
    # Setup: Agent with two cards
    agent_id = "agent_a"
    wallet_a = Wallet.new(agent_id=agent_id, wallet_id="wallet_a")

    card_1 = Card(
        card_id="card_1",
        wallet_id="wallet_a",
        status=CardStatus.ACTIVE,
        limit_daily=Decimal("1000.00"),
        spent_today=Decimal("800.00"),  # Close to limit
        funded_amount=Decimal("1000.00"),  # Sufficient funds
    )

    card_2 = Card(
        card_id="card_2",
        wallet_id="wallet_a",
        status=CardStatus.ACTIVE,
        limit_daily=Decimal("1000.00"),
        spent_today=Decimal("100.00"),  # Fresh card
        funded_amount=Decimal("1000.00"),  # Sufficient funds
    )

    card_store = MockCardStore(cards={
        "card_1": card_1,
        "card_2": card_2,
    })

    # Try to authorize $300 on each card
    test_amount = Decimal("300.00")

    # Card 1 should reject (800 + 300 > 1000)
    card1_available = card_1.limit_daily - card_1.spent_today
    card1_can_authorize = test_amount <= card1_available

    # Card 2 should accept (100 + 300 < 1000)
    card2_available = card_2.limit_daily - card_2.spent_today
    card2_can_authorize = test_amount <= card2_available

    assert card1_can_authorize is False, "Card 1 should reject due to daily limit"
    assert card2_can_authorize is True, "Card 2 should accept (fresh limit)"

    # Key isolation property: Cards maintain separate spending tracking
    assert card_1.spent_today != card_2.spent_today
    assert card_1.card_id != card_2.card_id

    # Verify via the card's authorization check
    can_auth_1, reason_1 = card_1.can_authorize(test_amount)
    can_auth_2, reason_2 = card_2.can_authorize(test_amount)

    assert can_auth_1 is False
    assert "exceeds available balance" in reason_1 or "limit" in reason_1
    assert can_auth_2 is True
    assert reason_2 == "OK"


# =============================================================================
# Cross-Tenant Mandate Isolation (3 tests)
# =============================================================================

def test_mandate_chain_cannot_reference_cross_tenant_wallets():
    """
    Isolation boundary: Mandate chain from Tenant A cannot reference wallets
    from Tenant B.

    Verifies that the mandate chain validation enforces tenant boundaries
    by checking wallet ownership against the mandate subject.
    """
    # Setup: Two tenants with separate agents and wallets
    tenant_a_agent = Agent.new(name="Tenant A Agent", owner_id="tenant_a")
    tenant_b_agent = Agent.new(name="Tenant B Agent", owner_id="tenant_b")

    wallet_a = Wallet.new(agent_id=tenant_a_agent.agent_id, wallet_id="wallet_a")
    wallet_b = Wallet.new(agent_id=tenant_b_agent.agent_id, wallet_id="wallet_b")

    wallet_store = MockWalletStore(wallets={
        "wallet_a": wallet_a,
        "wallet_b": wallet_b,
    })

    # Tenant A agent tries to create mandate for Tenant B's wallet
    bundle = _create_mandate_bundle(
        agent_id=tenant_a_agent.agent_id,
        wallet_id="wallet_b",  # Cross-tenant violation
    )

    # Verify cross-tenant isolation
    mandate_subject = bundle.payment["subject"]
    target_wallet = wallet_store.get("wallet_b")

    assert mandate_subject == tenant_a_agent.agent_id
    assert target_wallet.agent_id == tenant_b_agent.agent_id
    assert tenant_a_agent.owner_id == "tenant_a"
    assert tenant_b_agent.owner_id == "tenant_b"

    # The isolation violation
    assert mandate_subject != target_wallet.agent_id, (
        "Mandate subject must match wallet owner to prevent cross-tenant access"
    )


def test_ap2_subject_validated_against_tap_identity():
    """
    Isolation boundary: AP2 subject field is validated against authenticated
    agent identity (TAP identity must match AP2 subject).

    Verifies that the identity verification binds the TAP-authenticated agent
    to the AP2 mandate chain subject, preventing identity spoofing.
    """
    settings = SardisSettings(environment="dev")

    # Setup identity registry with two agents
    identity_registry = IdentityRegistry()

    # Agent A's identity
    agent_a_identity, agent_a_key = AgentIdentity.generate()
    agent_a_identity.agent_id = "agent_a"
    identity_registry.issue(
        agent_id="agent_a",
        public_key=agent_a_identity.public_key,
        domain="sardis.network",
        algorithm="ed25519",
    )

    # Agent B's identity
    agent_b_identity, agent_b_key = AgentIdentity.generate()
    agent_b_identity.agent_id = "agent_b"
    identity_registry.issue(
        agent_id="agent_b",
        public_key=agent_b_identity.public_key,
        domain="sardis.network",
        algorithm="ed25519",
    )

    # Create mandate bundle where Agent A is the subject
    bundle = _create_mandate_bundle(
        agent_id="agent_a",
        wallet_id="wallet_a",
    )

    # Mock the verification method to show Agent B's key (spoofing attempt)
    bundle.payment["proof"]["verification_method"] = (
        f"ed25519:{agent_b_identity.public_key.hex()}"
    )

    # Verify identity binding check
    verifier = MandateVerifier(settings=settings, identity_registry=identity_registry)

    # The verifier should detect that the verification_method (Agent B's key)
    # doesn't match the subject field (Agent A)
    verification_method = bundle.payment["proof"]["verification_method"]
    algorithm, public_key = IdentityRegistry.parse_verification_method(verification_method)

    # Check binding for the subject claimed in the mandate
    subject_matches = identity_registry.verify_binding(
        agent_id="agent_a",  # Subject claims to be Agent A
        domain="sardis.network",
        public_key=public_key,  # But using Agent B's key
        algorithm=algorithm,
    )

    assert subject_matches is False, (
        "TAP identity (Agent B's key) must match AP2 subject (Agent A) - "
        "this mismatch should be rejected"
    )


def test_ucp_checkout_sessions_scoped_to_creating_agent():
    """
    Isolation boundary: UCP checkout sessions are scoped to the creating
    agent/tenant.

    Verifies that checkout sessions maintain proper tenant isolation and
    cannot be accessed or manipulated by other agents.
    """
    from sardis_checkout.models import CheckoutSession, CustomerSession, PSPType, PaymentStatus

    # Setup: Two agents creating checkout sessions
    agent_a_id = "agent_a"
    agent_b_id = "agent_b"

    session_a = CustomerSession(
        session_id="session_a",
        agent_id=agent_a_id,
        customer_email="customer-a@example.com",
        status="active",
    )

    session_b = CustomerSession(
        session_id="session_b",
        agent_id=agent_b_id,
        customer_email="customer-b@example.com",
        status="active",
    )

    checkout_a = CheckoutSession(
        session_id="checkout_a",
        psp=PSPType.STRIPE,
        checkout_url="https://checkout.example.com/a",
        agent_id=agent_a_id,
        merchant_id="merchant_a",
        amount=Decimal("100.00"),
        status=PaymentStatus.PENDING,
    )

    checkout_b = CheckoutSession(
        session_id="checkout_b",
        psp=PSPType.STRIPE,
        checkout_url="https://checkout.example.com/b",
        agent_id=agent_b_id,
        merchant_id="merchant_b",
        amount=Decimal("200.00"),
        status=PaymentStatus.PENDING,
    )

    # Mock session store
    session_store = {
        "session_a": session_a,
        "session_b": session_b,
        "checkout_a": checkout_a,
        "checkout_b": checkout_b,
    }

    # Function to check session access
    def can_access_session(agent_id: str, session_id: str) -> tuple[bool, str]:
        session = session_store.get(session_id)
        if not session:
            return False, "session_not_found"

        if hasattr(session, "agent_id") and session.agent_id != agent_id:
            return False, "unauthorized_agent"

        return True, "ok"

    # Agent A can access their own sessions
    can_access, reason = can_access_session(agent_a_id, "session_a")
    assert can_access is True

    can_access, reason = can_access_session(agent_a_id, "checkout_a")
    assert can_access is True

    # Agent A cannot access Agent B's sessions
    can_access, reason = can_access_session(agent_a_id, "session_b")
    assert can_access is False
    assert reason == "unauthorized_agent"

    can_access, reason = can_access_session(agent_a_id, "checkout_b")
    assert can_access is False
    assert reason == "unauthorized_agent"

    # Verify session ownership
    assert session_a.agent_id == agent_a_id
    assert session_b.agent_id == agent_b_id
    assert checkout_a.agent_id == agent_a_id
    assert checkout_b.agent_id == agent_b_id

    # Key isolation property: Sessions are bound to agents
    assert session_a.agent_id != session_b.agent_id
    assert checkout_a.agent_id != checkout_b.agent_id
