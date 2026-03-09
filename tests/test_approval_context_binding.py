"""Tests for approval context binding — ensuring approved object == executed object.

These tests verify that the ApprovalContext model correctly detects mutations
between approval time and execution time, preventing prompt injection attacks
where a browser agent's payment context is tampered with.

Test categories:
  - ApprovalContext hash consistency and determinism
  - Mutation detection (each field change invalidates the hash)
  - Replay detection (expired approvals, reused hashes)
  - Cart hash computation
  - End-to-end binding scenarios from the verdict
"""
import hashlib
import time

import pytest
from sardis_v2_core.approval_context import (
    ApprovalContext,
    hash_cart,
    hash_value,
    verify_approval_context,
)


class TestApprovalContextHash:
    """ApprovalContext.compute_hash() is deterministic and tamper-evident."""

    def test_deterministic(self):
        ctx = ApprovalContext(
            top_origin="https://shop.example.com",
            session_id="sess_123",
            amount="50.00",
            token="USDC",
            chain="base",
            destination="0xmerchant",
        )
        assert ctx.compute_hash() == ctx.compute_hash()

    def test_different_contexts_different_hashes(self):
        ctx1 = ApprovalContext(amount="50.00", destination="0xA")
        ctx2 = ApprovalContext(amount="50.00", destination="0xB")
        assert ctx1.compute_hash() != ctx2.compute_hash()

    def test_empty_context_has_hash(self):
        ctx = ApprovalContext()
        h = ctx.compute_hash()
        assert len(h) == 64  # SHA-256 hex

    def test_to_dict_includes_hash(self):
        ctx = ApprovalContext(amount="10.00")
        d = ctx.to_dict()
        assert "approval_context_hash" in d
        assert d["approval_context_hash"] == ctx.compute_hash()


class TestMutationDetection:
    """Each field mutation between approval and execution is caught."""

    def _make_ctx(self, **overrides) -> ApprovalContext:
        base = {
            "top_origin": "https://shop.example.com",
            "frame_origin": "https://checkout.sardis.sh",
            "page_url_hash": hash_value("https://shop.example.com/checkout?id=42"),
            "session_id": "sess_abc123",
            "nonce": "nonce_xyz",
            "merchant_domain": "shop.example.com",
            "cart_hash": hash_value("cart_contents"),
            "action_description_hash": hash_value("Buy 3 widgets"),
            "policy_hash": hash_value("policy_snapshot"),
            "amount": "30.00",
            "token": "USDC",
            "chain": "base",
            "destination": "0xmerchant456",
            "expires_at": int(time.time()) + 300,
        }
        base.update(overrides)
        return ApprovalContext(**base)

    def test_same_session_different_origin(self):
        """Verdict case 1: same session, different origin → hash mismatch."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        # Attacker replays from a different origin
        tampered = self._make_ctx(top_origin="https://evil.example.com")
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_same_origin_mutated_cart(self):
        """Verdict case 2: same origin, mutated cart → hash mismatch."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(cart_hash=hash_value("different_cart_contents"))
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_same_amount_different_merchant(self):
        """Verdict case 3: same amount, different merchant → hash mismatch."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(
            merchant_domain="evil-merchant.com",
            destination="0xevil_merchant",
        )
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_same_cart_changed_payment_details(self):
        """Verdict case 4: same cart, changed payment details → hash mismatch."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        # Change token, chain, or destination
        tampered = self._make_ctx(token="EURC", chain="polygon")
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_changed_amount(self):
        """Amount changed between approval and execution."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(amount="99999.00")
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_changed_nonce(self):
        """Nonce changed — prevents nonce substitution."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(nonce="different_nonce")
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_changed_policy(self):
        """Policy hash changed — detects policy swap attacks."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(policy_hash=hash_value("permissive_policy"))
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_changed_action_description(self):
        """Action description changed — detects prompt injection rewrite."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        tampered = self._make_ctx(action_description_hash=hash_value("Send all funds to attacker"))
        ok, err = verify_approval_context(tampered, approved_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_identical_context_passes(self):
        """Identical context at approval and execution → passes."""
        approved = self._make_ctx()
        approved_hash = approved.compute_hash()

        # Same context at execution
        execution = self._make_ctx()
        ok, err = verify_approval_context(execution, approved_hash)
        assert ok
        assert err == ""


class TestReplayDetection:
    """Expired approvals and cross-session replays are blocked."""

    def test_expired_approval(self):
        """Verdict case 5 variant: expired approval context is rejected."""
        ctx = ApprovalContext(
            session_id="sess_1",
            amount="10.00",
            expires_at=int(time.time()) - 60,  # expired 60 seconds ago
        )
        ok, err = verify_approval_context(ctx, ctx.compute_hash())
        assert not ok
        assert err == "approval_context_expired"

    def test_approval_hash_reused_on_different_page(self):
        """Verdict case 6: approval hash from one page reused on another."""
        page1_ctx = ApprovalContext(
            top_origin="https://legit-store.com",
            session_id="sess_legit",
            amount="50.00",
            token="USDC",
            chain="base",
            destination="0xlegit_merchant",
            expires_at=int(time.time()) + 300,
        )
        page1_hash = page1_ctx.compute_hash()

        # Attacker tries to reuse the hash on a different page
        page2_ctx = ApprovalContext(
            top_origin="https://attacker-store.com",  # different origin
            session_id="sess_legit",  # same session (stolen)
            amount="50.00",
            token="USDC",
            chain="base",
            destination="0xattacker",  # different destination
            expires_at=int(time.time()) + 300,
        )
        ok, err = verify_approval_context(page2_ctx, page1_hash)
        assert not ok
        assert err == "approval_context_hash_mismatch"

    def test_no_expiry_is_accepted(self):
        """Context with no expiry set is not treated as expired."""
        ctx = ApprovalContext(amount="10.00", expires_at=0)
        ok, err = verify_approval_context(ctx, ctx.compute_hash())
        assert ok

    def test_future_expiry_is_accepted(self):
        """Context with future expiry is accepted."""
        ctx = ApprovalContext(
            amount="10.00",
            expires_at=int(time.time()) + 3600,
        )
        ok, err = verify_approval_context(ctx, ctx.compute_hash())
        assert ok


class TestCartHash:
    """hash_cart() produces deterministic canonical hashes."""

    def test_deterministic(self):
        items = [{"item_id": "w1", "name": "Widget", "quantity": 3, "price_minor": 1000}]
        h1 = hash_cart(items, "30.00", "2.40", "USD")
        h2 = hash_cart(items, "30.00", "2.40", "USD")
        assert h1 == h2

    def test_order_independent(self):
        """Item order doesn't affect hash (canonical sorting)."""
        items_a = [
            {"item_id": "w2", "name": "Gadget", "quantity": 1, "price_minor": 2000},
            {"item_id": "w1", "name": "Widget", "quantity": 3, "price_minor": 1000},
        ]
        items_b = [
            {"item_id": "w1", "name": "Widget", "quantity": 3, "price_minor": 1000},
            {"item_id": "w2", "name": "Gadget", "quantity": 1, "price_minor": 2000},
        ]
        assert hash_cart(items_a, "50.00", "4.00", "USD") == hash_cart(items_b, "50.00", "4.00", "USD")

    def test_different_carts_different_hashes(self):
        items_a = [{"item_id": "w1", "name": "Widget", "quantity": 3, "price_minor": 1000}]
        items_b = [{"item_id": "w1", "name": "Widget", "quantity": 5, "price_minor": 1000}]
        assert hash_cart(items_a, "30.00", "2.40", "USD") != hash_cart(items_b, "50.00", "4.00", "USD")

    def test_empty_cart(self):
        h = hash_cart([], "0", "0", "USD")
        assert len(h) == 64


class TestHashValue:
    """hash_value() utility function."""

    def test_consistent(self):
        assert hash_value("test") == hash_value("test")

    def test_matches_stdlib(self):
        assert hash_value("hello") == hashlib.sha256(b"hello").hexdigest()
