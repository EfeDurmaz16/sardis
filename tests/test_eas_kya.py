"""Tests for EAS KYA attestation module."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sardis_protocol.eas_kya import (
    VALID_TRUST_LEVELS,
    EASKYAClient,
    KYAAttestation,
    decode_kya_data,
    encode_kya_data,
)

# ── Encoding / Decoding ──────────────────────────────────────────────────


class TestEncodeDecodeKYA:
    """Test ABI encoding and decoding roundtrips."""

    def test_encode_decode_roundtrip(self):
        agent_id = "agent_abc123"
        trust_level = "MEDIUM"
        policy_hash = "0x" + "ab" * 32

        encoded = encode_kya_data(agent_id, trust_level, policy_hash)
        decoded_agent, decoded_trust, decoded_hash = decode_kya_data(encoded)

        assert decoded_agent == agent_id
        assert decoded_trust == "MEDIUM"
        assert decoded_hash == policy_hash

    def test_encode_all_trust_levels(self):
        for level in VALID_TRUST_LEVELS:
            encoded = encode_kya_data("agent_1", level, "0x" + "00" * 32)
            _, decoded_level, _ = decode_kya_data(encoded)
            assert decoded_level == level

    def test_encode_rejects_invalid_trust_level(self):
        with pytest.raises(ValueError, match="Invalid trust level"):
            encode_kya_data("agent_1", "INVALID", "0x" + "00" * 32)

    def test_encode_rejects_bad_policy_hash(self):
        with pytest.raises(ValueError, match="policy_hash must be 32 bytes"):
            encode_kya_data("agent_1", "LOW", "0xshort")

    def test_encode_without_0x_prefix(self):
        ph = "ab" * 32
        encoded = encode_kya_data("agent_1", "HIGH", ph)
        _, _, decoded_hash = decode_kya_data(encoded)
        assert decoded_hash == "0x" + ph

    def test_decode_too_short_data(self):
        with pytest.raises(ValueError, match="too short"):
            decode_kya_data("0x" + "00" * 10)

    def test_roundtrip_long_agent_id(self):
        agent_id = "agent_" + "x" * 200
        trust_level = "LOW"
        policy_hash = "0x" + "ff" * 32

        encoded = encode_kya_data(agent_id, trust_level, policy_hash)
        decoded_agent, decoded_trust, decoded_hash = decode_kya_data(encoded)

        assert decoded_agent == agent_id
        assert decoded_trust == "LOW"
        assert decoded_hash == policy_hash


# ── KYAAttestation dataclass ─────────────────────────────────────────────


class TestKYAAttestation:
    def test_uid_hex(self):
        uid = bytes.fromhex("ab" * 32)
        att = KYAAttestation(
            agent_id="a1",
            trust_level="LOW",
            policy_hash="0x" + "00" * 32,
            attestation_uid=uid,
        )
        assert att.uid_hex == "0x" + "ab" * 32

    def test_default_fields(self):
        att = KYAAttestation(
            agent_id="a1",
            trust_level="HIGH",
            policy_hash="0x" + "00" * 32,
            attestation_uid=b"\x00" * 32,
        )
        assert att.attester == ""
        assert att.revoked is False
        assert att.timestamp == 0


# ── EASKYAClient ─────────────────────────────────────────────────────────


class TestEASKYAClient:
    @pytest.fixture
    def mock_rpc(self):
        rpc = AsyncMock()
        rpc.eth_call = AsyncMock(return_value="0x" + "00" * 64)
        rpc.get_transaction_receipt = AsyncMock(return_value=None)
        return rpc

    @pytest.fixture
    def client(self, mock_rpc):
        schema_uid = "0x" + "11" * 32
        return EASKYAClient(rpc_client=mock_rpc, schema_uid=schema_uid)

    @pytest.mark.asyncio
    async def test_create_attestation_simulation_mode(self, client):
        """Without a signer, create_attestation returns a deterministic UID."""
        att = await client.create_attestation(
            agent_id="agent_test",
            trust_level="MEDIUM",
            policy_hash="0x" + "cc" * 32,
        )
        assert att.agent_id == "agent_test"
        assert att.trust_level == "MEDIUM"
        assert att.policy_hash == "0x" + "cc" * 32
        assert len(att.attestation_uid) == 32

        # Same inputs should produce same deterministic UID
        att2 = await client.create_attestation(
            agent_id="agent_test",
            trust_level="MEDIUM",
            policy_hash="0x" + "cc" * 32,
        )
        assert att.attestation_uid == att2.attestation_uid

    @pytest.mark.asyncio
    async def test_create_attestation_with_signer(self, client, mock_rpc):
        """With a signer, create_attestation sends a real transaction."""
        signer = AsyncMock()
        signer.sign_and_send = AsyncMock(return_value="0x" + "aa" * 32)

        uid_bytes = bytes.fromhex("bb" * 32)
        mock_rpc.get_transaction_receipt = AsyncMock(return_value={
            "logs": [{"topics": ["0xevent", "0x" + "bb" * 32]}]
        })

        att = await client.create_attestation(
            agent_id="agent_live",
            trust_level="HIGH",
            policy_hash="0x" + "dd" * 32,
            signer=signer,
        )
        assert att.agent_id == "agent_live"
        assert att.attestation_uid == uid_bytes
        signer.sign_and_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_attestation_returns_none_on_error(self, client, mock_rpc):
        """verify_attestation returns None when RPC fails."""
        mock_rpc.eth_call = AsyncMock(side_effect=RuntimeError("RPC down"))
        result = await client.verify_attestation(b"\x00" * 32)
        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_attestation_simulation(self, client):
        """Revoke without signer succeeds."""
        result = await client.revoke_attestation(b"\x00" * 32)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_attestation_with_signer(self, client):
        signer = AsyncMock()
        signer.sign_and_send = AsyncMock(return_value="0x" + "ff" * 32)
        result = await client.revoke_attestation(b"\x00" * 32, signer=signer)
        assert result is True
        signer.sign_and_send.assert_called_once()


# ── Trust level mapping ──────────────────────────────────────────────────


class TestTrustLevelMapping:
    def test_kya_to_trust_mapping(self):
        from sardis_v2_core.spending_policy import TrustLevel, trust_level_for_kya

        assert trust_level_for_kya("none") == TrustLevel.LOW
        assert trust_level_for_kya("basic") == TrustLevel.LOW
        assert trust_level_for_kya("verified") == TrustLevel.MEDIUM
        assert trust_level_for_kya("attested") == TrustLevel.HIGH
        assert trust_level_for_kya("unknown") == TrustLevel.LOW

    def test_trust_to_kya_mapping(self):
        from sardis_v2_core.spending_policy import TrustLevel, kya_level_for_trust

        assert kya_level_for_trust(TrustLevel.LOW) == "basic"
        assert kya_level_for_trust(TrustLevel.MEDIUM) == "verified"
        assert kya_level_for_trust(TrustLevel.HIGH) == "attested"
        assert kya_level_for_trust(TrustLevel.UNLIMITED) == "attested"
