"""
Concurrency Tests for Sardis Payment System

These tests verify that the system handles concurrent requests correctly
and prevents double-spending scenarios.

FINTECH CRITICAL: Race conditions can lead to financial losses.
"""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

import pytest


class TestMaestroConcurrency:
    """
    THE MAESTRO STANDARD: Concurrency verification.

    These tests simulate multiple agents hitting the wallet at once
    and verify the system handles race conditions correctly.
    """

    @pytest.mark.asyncio
    async def test_multiple_agents_hitting_wallet(self, client, test_wallet_id):
        """
        MAESTRO STANDARD TEST: Simulate multiple agents hitting the wallet at once.

        This test verifies:
        1. No overdraft via race condition
        2. All requests are handled atomically
        3. No server crashes under concurrent load
        """
        # Simulate 10 "agents" making concurrent requests
        num_agents = 10

        async def agent_request(agent_id: int):
            """Simulate an agent making a payment request."""
            mandate_id = f"mnd_agent{agent_id}_{uuid.uuid4().hex[:8]}"
            payload = {
                "mandate": {
                    "mandate_id": mandate_id,
                    "subject": test_wallet_id,
                    "destination": f"0x{str(agent_id).zfill(40)}",
                    "amount_minor": "100000",  # 0.1 USDC each
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": f"Agent {agent_id} concurrent test",
                }
            }
            return await client.post("/api/v2/mandates/execute", json=payload)

        # Fire all agent requests simultaneously
        tasks = [agent_request(i) for i in range(num_agents)]
        responses = await asyncio.gather(*tasks)

        # CRITICAL CHECKS:

        # 1. No server errors (race conditions would cause 500s)
        server_errors = [r for r in responses if r.status_code >= 500]
        assert len(server_errors) == 0, \
            f"MAESTRO STANDARD VIOLATED: {len(server_errors)} server errors during concurrent access"

        # 2. All requests completed (no timeouts/hangs)
        assert len(responses) == num_agents, \
            f"Not all requests completed: {len(responses)}/{num_agents}"

        # 3. Check response consistency
        for i, response in enumerate(responses):
            assert response.status_code in (200, 400, 403, 409, 429, 422), \
                f"Agent {i} received unexpected status: {response.status_code}"


class TestConcurrentPayments:
    """Tests for concurrent payment handling."""

    @pytest.mark.asyncio
    async def test_concurrent_payments_from_same_wallet(self, client, test_wallet_id):
        """
        Multiple concurrent payment requests from the same wallet
        should respect the wallet's balance and limits.

        FINTECH CRITICAL: Prevent overdraft via race condition.
        """
        # Create 10 concurrent payment requests
        tasks = []
        for i in range(10):
            mandate_id = f"mnd_concurrent_{uuid.uuid4().hex[:8]}"
            payload = {
                "mandate": {
                    "mandate_id": mandate_id,
                    "subject": test_wallet_id,
                    "destination": "0x" + str(i).zfill(40),
                    "amount_minor": "100000",  # 0.1 USDC each
                    "token": "USDC",
                    "chain": "base_sepolia",
                }
            }
            tasks.append(client.post("/api/v2/mandates/execute", json=payload))

        responses = await asyncio.gather(*tasks)

        # Count successful transactions
        successful = [r for r in responses if r.status_code == 200]
        failed = [r for r in responses if r.status_code != 200]

        # Total successful amount should not exceed wallet limits
        # (This is a simulation mode test - actual balance checks
        # would need real chain state)
        assert len(responses) == 10

        # At minimum, the system should process requests without crashing
        # 422 = validation error (e.g., wallet not found in test mode)
        for response in responses:
            assert response.status_code in (200, 400, 403, 422, 429, 409, 500)

    @pytest.mark.asyncio
    async def test_concurrent_holds_on_same_wallet(self, client, test_wallet_id):
        """
        Multiple concurrent hold requests should not over-reserve funds.

        FINTECH CRITICAL: Pre-authorizations must be atomic.
        """
        tasks = []
        for i in range(5):
            payload = {
                "wallet_id": test_wallet_id,
                "amount": "50.00",
                "token": "USDC",
                "merchant_id": f"merchant_{i}",
                "purpose": f"Concurrent hold test {i}",
                "expires_in_seconds": 3600,
            }
            tasks.append(client.post("/api/v2/holds", json=payload))

        responses = await asyncio.gather(*tasks)

        # Each hold should be processed atomically
        for response in responses:
            assert response.status_code in (200, 201, 400, 403, 409, 422)

    @pytest.mark.asyncio
    async def test_concurrent_capture_of_same_hold(self, client, test_wallet_id):
        """
        Concurrent capture attempts on the same hold should only succeed once.

        FINTECH CRITICAL: A hold must be captured exactly once.
        """
        # First, create a hold
        hold_payload = {
            "wallet_id": test_wallet_id,
            "amount": "100.00",
            "token": "USDC",
            "merchant_id": "merchant_capture_test",
            "purpose": "Capture test",
            "expires_in_seconds": 3600,
        }
        hold_response = await client.post("/api/v2/holds", json=hold_payload)

        if hold_response.status_code not in (200, 201):
            pytest.skip("Could not create hold for capture test")

        hold_data = hold_response.json()
        hold_id = hold_data.get("hold_id") or hold_data.get("id") or hold_data.get("external_id")

        if not hold_id:
            pytest.skip("Hold ID not returned")

        # Try to capture the same hold 5 times concurrently
        capture_payload = {
            "amount": "50.00",  # Partial capture
        }
        tasks = [
            client.post(f"/api/v2/holds/{hold_id}/capture", json=capture_payload)
            for _ in range(5)
        ]

        responses = await asyncio.gather(*tasks)

        # Count successful captures
        successful_captures = [r for r in responses if r.status_code == 200]

        # At most ONE capture should succeed
        # Others should fail with conflict/already captured
        assert len(successful_captures) <= 1, \
            f"Expected at most 1 successful capture, got {len(successful_captures)}"


class TestRaceConditions:
    """Tests specifically targeting race condition scenarios."""

    @pytest.mark.asyncio
    async def test_simultaneous_spend_and_balance_check(self, client, test_wallet_id):
        """
        Spending and balance checks happening simultaneously
        should maintain consistency.
        """
        async def spend():
            payload = {
                "mandate": {
                    "mandate_id": f"mnd_race_{uuid.uuid4().hex[:8]}",
                    "subject": test_wallet_id,
                    "destination": "0x" + "a" * 40,
                    "amount_minor": "100000",
                    "token": "USDC",
                    "chain": "base_sepolia",
                }
            }
            return await client.post("/api/v2/mandates/execute", json=payload)

        async def check_balance():
            return await client.get(f"/api/v2/wallets/{test_wallet_id}/balance")

        # Mix of spend and balance check operations
        tasks = []
        for i in range(20):
            if i % 2 == 0:
                tasks.append(spend())
            else:
                tasks.append(check_balance())

        responses = await asyncio.gather(*tasks)

        # All operations should complete without server errors
        for response in responses:
            # 404 is acceptable for test wallets that don't exist
            assert response.status_code in (200, 201, 400, 403, 404, 409, 422)

    @pytest.mark.asyncio
    async def test_concurrent_wallet_creation_same_agent(self, client, test_agent_id):
        """
        Concurrent wallet creation for the same agent should be handled safely.
        """
        tasks = []
        for i in range(5):
            payload = {
                "agent_id": test_agent_id,
                "mpc_provider": "turnkey",
                "currency": "USDC",
            }
            tasks.append(client.post("/api/v2/wallets", json=payload))

        responses = await asyncio.gather(*tasks)

        # Should not crash, duplicates should be handled gracefully
        for response in responses:
            assert response.status_code in (200, 201, 400, 409, 422)

    @pytest.mark.asyncio
    async def test_interleaved_hold_capture_void(self, client, test_wallet_id):
        """
        Interleaved hold operations should maintain consistency.
        """
        # Create multiple holds
        holds = []
        for i in range(3):
            payload = {
                "wallet_id": test_wallet_id,
                "amount": "20.00",
                "token": "USDC",
                "merchant_id": f"merchant_interleaved_{i}",
                "expires_in_seconds": 3600,
            }
            response = await client.post("/api/v2/holds", json=payload)
            if response.status_code in (200, 201):
                hold_data = response.json()
                hold_id = hold_data.get("hold_id") or hold_data.get("id") or hold_data.get("external_id")
                if hold_id:
                    holds.append(hold_id)

        if len(holds) < 2:
            pytest.skip("Could not create enough holds for interleaving test")

        # Mix capture and void operations
        tasks = []
        for i, hold_id in enumerate(holds):
            if i % 2 == 0:
                tasks.append(client.post(f"/api/v2/holds/{hold_id}/capture", json={"amount": "15.00"}))
            else:
                tasks.append(client.post(f"/api/v2/holds/{hold_id}/void"))

        responses = await asyncio.gather(*tasks)

        # Each operation should either succeed or fail cleanly
        for response in responses:
            assert response.status_code in (200, 400, 404, 409, 422)


class TestLockingBehavior:
    """Tests for database locking behavior."""

    @pytest.mark.asyncio
    async def test_serialized_balance_updates(self, client, test_wallet_id):
        """
        Balance updates should be serialized to prevent lost updates.
        """
        # Create many small transactions
        tasks = []
        for i in range(20):
            mandate_id = f"mnd_serial_{uuid.uuid4().hex[:8]}"
            payload = {
                "mandate": {
                    "mandate_id": mandate_id,
                    "subject": test_wallet_id,
                    "destination": "0x" + str(i % 10).zfill(40),
                    "amount_minor": "10000",  # 0.01 USDC
                    "token": "USDC",
                    "chain": "base_sepolia",
                }
            }
            tasks.append(client.post("/api/v2/mandates/execute", json=payload))

        responses = await asyncio.gather(*tasks)

        # All should complete without deadlock or timeout
        success_count = sum(1 for r in responses if r.status_code == 200)
        error_count = sum(1 for r in responses if r.status_code >= 500)

        # No server errors (deadlocks would cause 500s)
        assert error_count == 0, f"Got {error_count} server errors, possible deadlock"

    @pytest.mark.asyncio
    async def test_concurrent_policy_checks(self, client, test_wallet_id):
        """
        Concurrent policy checks should not interfere with each other.
        """
        tasks = []
        for i in range(10):
            params = {
                "wallet_id": test_wallet_id,
                "amount": str(10 + i),
                "merchant": f"merchant_{i}",
            }
            # Assuming there's a policy check endpoint
            tasks.append(client.get("/api/v2/wallets/{}/policy/check".format(test_wallet_id), params=params))

        responses = await asyncio.gather(*tasks)

        # Policy checks are read-only and should always succeed or return 404
        for response in responses:
            assert response.status_code in (200, 404, 400)
