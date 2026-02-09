"""Tests for LedgerResource."""
import pytest
from decimal import Decimal


MOCK_LEDGER_ENTRY = {
    "tx_id": "ltx_123",
    "mandate_id": "mandate_456",
    "from_wallet": "wallet_sender",
    "to_wallet": "wallet_receiver",
    "amount": "100.00",
    "currency": "USDC",
    "chain": "base_sepolia",
    "chain_tx_hash": "0xabc123def456",
    "audit_anchor": "anchor_789",
    "created_at": "2025-01-20T00:00:00Z",
}


class TestListEntries:
    """Tests for listing ledger entries."""

    async def test_list_all_entries(self, client, httpx_mock):
        """Should list all ledger entries."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries?limit=50&offset=0",
            method="GET",
            json={"entries": [MOCK_LEDGER_ENTRY]},
        )

        entries = await client.ledger.list_entries()
        assert len(entries) == 1
        assert entries[0].tx_id == "ltx_123"
        assert entries[0].amount == Decimal("100.00")

    async def test_list_entries_with_wallet_filter(self, client, httpx_mock):
        """Should list entries filtered by wallet."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries?limit=50&offset=0&wallet_id=wallet_sender",
            method="GET",
            json={"entries": [MOCK_LEDGER_ENTRY]},
        )

        entries = await client.ledger.list_entries(wallet_id="wallet_sender")
        assert len(entries) == 1

    async def test_list_entries_with_pagination(self, client, httpx_mock):
        """Should list entries with pagination."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries?limit=10&offset=5",
            method="GET",
            json={"entries": [MOCK_LEDGER_ENTRY]},
        )

        entries = await client.ledger.list_entries(limit=10, offset=5)
        assert len(entries) == 1

    async def test_list_empty_entries(self, client, httpx_mock):
        """Should handle empty entry list."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries?limit=50&offset=0",
            method="GET",
            json={"entries": []},
        )

        entries = await client.ledger.list_entries()
        assert len(entries) == 0


class TestGetEntry:
    """Tests for getting a ledger entry."""

    async def test_get_entry(self, client, httpx_mock):
        """Should get a ledger entry by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries/ltx_123",
            method="GET",
            json=MOCK_LEDGER_ENTRY,
        )

        entry = await client.ledger.get_entry("ltx_123")
        assert entry.tx_id == "ltx_123"
        assert entry.mandate_id == "mandate_456"
        assert entry.chain == "base_sepolia"

    async def test_get_entry_without_optional_fields(self, client, httpx_mock):
        """Should handle entry without optional fields."""
        minimal_entry = {
            "tx_id": "ltx_456",
            "amount": "50.00",
            "currency": "USDC",
            "created_at": "2025-01-20T00:00:00Z",
        }
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries/ltx_456",
            method="GET",
            json=minimal_entry,
        )

        entry = await client.ledger.get_entry("ltx_456")
        assert entry.tx_id == "ltx_456"
        assert entry.mandate_id is None
        assert entry.chain is None


class TestVerifyEntry:
    """Tests for verifying ledger entries."""

    async def test_verify_valid_entry(self, client, httpx_mock):
        """Should verify a valid entry."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries/ltx_123/verify",
            method="GET",
            json={"valid": True, "anchor": "merkle::abc123"},
        )

        result = await client.ledger.verify_entry("ltx_123")
        assert result["valid"] is True
        assert result["anchor"] == "merkle::abc123"

    async def test_verify_invalid_entry(self, client, httpx_mock):
        """Should return invalid for tampered entry."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/ledger/entries/ltx_tampered/verify",
            method="GET",
            json={"valid": False, "reason": "Hash mismatch"},
        )

        result = await client.ledger.verify_entry("ltx_tampered")
        assert result["valid"] is False
