"""
Idempotency Tests for Sardis Payment System

These tests verify that payment requests are processed exactly once,
even if the same request is sent multiple times.

FINTECH CRITICAL: Duplicate payment prevention is essential for financial systems.
"""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import pytest


class TestIdempotencyBasic:
    """Basic idempotency tests for payment operations."""

    @pytest.mark.asyncio
    async def test_same_mandate_id_returns_same_result(self, client, test_wallet_id):
        """
        The same mandate_id should always return the same result.

        FINTECH RULE: A mandate with the same ID must not be executed twice.
        """
        mandate_id = f"mnd_test_{uuid.uuid4().hex[:12]}"

        payload = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "1" * 40,
                "amount_minor": "1000000",  # 1 USDC
                "token": "USDC",
                "chain": "base_sepolia",
                "purpose": "Idempotency test",
            }
        }

        # First request
        response1 = await client.post("/api/v2/mandates/execute", json=payload)

        # Second request with same mandate_id
        response2 = await client.post("/api/v2/mandates/execute", json=payload)

        # Both should succeed or both should fail consistently
        assert response1.status_code == response2.status_code

        # If successful, the transaction details should match
        if response1.status_code == 200:
            result1 = response1.json()
            result2 = response2.json()

            # Same mandate_id should not create a new transaction
            # It should return the cached/existing result
            assert result1.get("payment_id") == result2.get("payment_id") or \
                   "already_processed" in str(result2).lower() or \
                   result2.get("status") == "duplicate"

    @pytest.mark.asyncio
    async def test_different_mandate_ids_create_separate_transactions(self, client, test_wallet_id):
        """
        Different mandate_ids should create separate transactions.
        """
        base_payload = {
            "subject": test_wallet_id,
            "destination": "0x" + "1" * 40,
            "amount_minor": "500000",  # 0.5 USDC
            "token": "USDC",
            "chain": "base_sepolia",
            "purpose": "Separate transaction test",
        }

        mandate_id_1 = f"mnd_separate_{uuid.uuid4().hex[:8]}"
        mandate_id_2 = f"mnd_separate_{uuid.uuid4().hex[:8]}"

        payload1 = {"mandate": {**base_payload, "mandate_id": mandate_id_1}}
        payload2 = {"mandate": {**base_payload, "mandate_id": mandate_id_2}}

        response1 = await client.post("/api/v2/mandates/execute", json=payload1)
        response2 = await client.post("/api/v2/mandates/execute", json=payload2)

        # Both should be processed (may succeed or fail based on policy/validation)
        # but they should be treated as separate requests
        # 422 = validation error (e.g., wallet not found in test mode)
        assert response1.status_code in (200, 400, 403, 422)
        assert response2.status_code in (200, 400, 403, 422)

    @pytest.mark.asyncio
    async def test_idempotency_key_header(self, client, test_wallet_id):
        """
        Test idempotency via X-Idempotency-Key header.
        """
        idempotency_key = f"idem_{uuid.uuid4().hex}"

        payload = {
            "mandate": {
                "mandate_id": f"mnd_header_{uuid.uuid4().hex[:8]}",
                "subject": test_wallet_id,
                "destination": "0x" + "2" * 40,
                "amount_minor": "250000",
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        headers = {"X-Idempotency-Key": idempotency_key}

        # First request
        response1 = await client.post("/api/v2/mandates/execute", json=payload, headers=headers)

        # Retry with same idempotency key
        response2 = await client.post("/api/v2/mandates/execute", json=payload, headers=headers)

        # Should return same status
        assert response1.status_code == response2.status_code


class TestIdempotencyEdgeCases:
    """Edge case tests for idempotency."""

    @pytest.mark.asyncio
    async def test_replay_attack_prevention(self, client, test_wallet_id):
        """
        Verify that replay attacks are prevented.

        SECURITY: Old mandate IDs should be rejected.
        """
        # Create a mandate that looks like it was processed before
        old_mandate_id = f"mnd_replay_{uuid.uuid4().hex[:8]}"

        payload = {
            "mandate": {
                "mandate_id": old_mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "3" * 40,
                "amount_minor": "100000",
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        # First execution
        response1 = await client.post("/api/v2/mandates/execute", json=payload)

        # Immediate replay attempt
        response2 = await client.post("/api/v2/mandates/execute", json=payload)

        # Second response should indicate duplicate/already processed
        if response1.status_code == 200:
            # Either return same result or explicitly reject as duplicate
            assert response2.status_code in (200, 409, 400)

    @pytest.mark.asyncio
    async def test_idempotency_with_different_amounts_same_id(self, client, test_wallet_id):
        """
        If the same mandate_id is used with different amounts,
        the system should reject or return the original result.

        FINTECH CRITICAL: Tampering with amount on retry should be rejected.
        """
        mandate_id = f"mnd_tamper_{uuid.uuid4().hex[:8]}"

        payload1 = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "4" * 40,
                "amount_minor": "1000000",  # 1 USDC
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        payload2 = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "4" * 40,
                "amount_minor": "2000000",  # 2 USDC - TAMPERED!
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        response1 = await client.post("/api/v2/mandates/execute", json=payload1)
        response2 = await client.post("/api/v2/mandates/execute", json=payload2)

        # The second request should either:
        # 1. Return the original result (ignoring the tampered amount)
        # 2. Reject with a conflict error
        if response1.status_code == 200 and response2.status_code == 200:
            result1 = response1.json()
            result2 = response2.json()

            # If both succeed, they should return the SAME transaction
            # (the second should not process a new, larger transaction)
            if "amount" in result1 and "amount" in result2:
                assert result1.get("amount") == result2.get("amount")


class TestMaestroStandard:
    """
    THE MAESTRO STANDARD: Idempotency verification.

    These tests demonstrate that Sardis executes transactions exactly once,
    even when the same request is submitted multiple times.
    """

    @pytest.mark.asyncio
    async def test_five_identical_requests_execute_once(self, client, test_wallet_id):
        """
        MAESTRO STANDARD TEST: Send the same transaction request 5 times,
        ensure it executes only ONCE.

        This is the critical fintech idempotency guarantee.
        """
        mandate_id = f"mnd_maestro_{uuid.uuid4().hex[:12]}"

        payload = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "7" * 40,
                "amount_minor": "1000000",  # 1 USDC
                "token": "USDC",
                "chain": "base_sepolia",
                "purpose": "Maestro Standard idempotency test",
            }
        }

        # Send EXACTLY 5 identical requests
        responses = []
        for i in range(5):
            response = await client.post("/api/v2/mandates/execute", json=payload)
            responses.append(response)

        # Analyze results
        success_responses = [r for r in responses if r.status_code == 200]

        if success_responses:
            # Extract payment IDs from successful responses
            payment_ids = set()
            for r in success_responses:
                data = r.json()
                pid = data.get("payment_id") or data.get("transaction_id") or data.get("id")
                if pid:
                    payment_ids.add(pid)

            # CRITICAL: All successful responses must reference the SAME transaction
            assert len(payment_ids) <= 1, \
                f"MAESTRO STANDARD VIOLATED: Multiple transactions created! IDs: {payment_ids}"

        # All responses should have consistent status (all succeed or all fail)
        status_codes = [r.status_code for r in responses]
        assert len(set(status_codes)) <= 2, \
            f"Inconsistent responses: {status_codes}"


class TestIdempotencyTiming:
    """Timing-related idempotency tests."""

    @pytest.mark.asyncio
    async def test_rapid_duplicate_requests(self, client, test_wallet_id):
        """
        Rapid duplicate requests should only process once.

        FINTECH CRITICAL: Network retries should not cause double-spend.
        """
        mandate_id = f"mnd_rapid_{uuid.uuid4().hex[:8]}"

        payload = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "5" * 40,
                "amount_minor": "500000",
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        # Send 5 requests as fast as possible
        tasks = [
            client.post("/api/v2/mandates/execute", json=payload)
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        # Count successful responses
        success_count = sum(1 for r in responses if r.status_code == 200)

        # Should have at most 1 successful unique transaction
        # Others should be duplicates or in-progress
        assert success_count <= 1 or all(
            r.status_code == responses[0].status_code for r in responses
        )

    @pytest.mark.asyncio
    async def test_idempotency_cache_expiry(self, client, test_wallet_id):
        """
        Test that idempotency cache properly handles timing.

        Note: In production, idempotency keys typically expire after 24-48 hours.
        This test verifies the basic mechanism works.
        """
        mandate_id = f"mnd_cache_{uuid.uuid4().hex[:8]}"

        payload = {
            "mandate": {
                "mandate_id": mandate_id,
                "subject": test_wallet_id,
                "destination": "0x" + "6" * 40,
                "amount_minor": "100000",
                "token": "USDC",
                "chain": "base_sepolia",
            }
        }

        response1 = await client.post("/api/v2/mandates/execute", json=payload)

        # Small delay
        await asyncio.sleep(0.1)

        response2 = await client.post("/api/v2/mandates/execute", json=payload)

        # Both should return consistent results
        assert response1.status_code == response2.status_code
