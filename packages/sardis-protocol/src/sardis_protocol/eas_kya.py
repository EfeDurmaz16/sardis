"""EAS-based Know Your Agent (KYA) attestation module.

Provides on-chain agent identity attestations using the Ethereum Attestation
Service (EAS), which is pre-deployed on Base at a fixed address.

KYA attestations bind an agent's identity to a trust level and policy hash,
enabling on-chain verification of agent capabilities before transaction
execution.

EAS contracts (pre-deployed on Base):
  - EAS: 0x4200000000000000000000000000000000000021
  - SchemaRegistry: 0x4200000000000000000000000000000000000020

Schema: "string agentId, string trustLevel, bytes32 policyHash"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Base pre-deployed EAS addresses (same for all OP Stack L2s)
EAS_ADDRESS = "0x4200000000000000000000000000000000000021"
SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"

# KYA schema: agentId (string), trustLevel (string), policyHash (bytes32)
KYA_SCHEMA = "string agentId, string trustLevel, bytes32 policyHash"

# Valid trust levels
VALID_TRUST_LEVELS = {"LOW", "MEDIUM", "HIGH", "UNLIMITED"}


@dataclass
class KYAAttestation:
    """Represents a KYA attestation on-chain."""

    agent_id: str
    trust_level: str  # LOW / MEDIUM / HIGH / UNLIMITED
    policy_hash: str  # bytes32 hex string
    attestation_uid: bytes
    attester: str = ""
    revoked: bool = False
    timestamp: int = 0

    @property
    def uid_hex(self) -> str:
        return "0x" + self.attestation_uid.hex()


def encode_kya_data(agent_id: str, trust_level: str, policy_hash: str) -> str:
    """ABI-encode KYA attestation data.

    Encodes (string agentId, string trustLevel, bytes32 policyHash) per the
    Solidity ABI encoding specification.

    Args:
        agent_id: The agent identifier string.
        trust_level: One of LOW, MEDIUM, HIGH, UNLIMITED.
        policy_hash: 32-byte hex-encoded policy hash (with or without 0x prefix).

    Returns:
        ABI-encoded hex string (with 0x prefix).
    """
    if trust_level.upper() not in VALID_TRUST_LEVELS:
        raise ValueError(
            f"Invalid trust level '{trust_level}'. Must be one of {VALID_TRUST_LEVELS}"
        )

    # Normalize policy hash
    ph = policy_hash.removeprefix("0x")
    if len(ph) != 64:
        raise ValueError("policy_hash must be 32 bytes (64 hex chars)")

    # ABI encoding for (string, string, bytes32):
    # - offset to agentId string data
    # - offset to trustLevel string data
    # - bytes32 policyHash (inline)
    # - agentId length + padded data
    # - trustLevel length + padded data

    def _encode_string(s: str) -> str:
        encoded = s.encode("utf-8").hex()
        length = len(s)
        # Pad to 32-byte boundary
        padded = encoded.ljust(((len(encoded) + 63) // 64) * 64, "0")
        return hex(length)[2:].zfill(64) + padded

    agent_id_encoded = _encode_string(agent_id)
    trust_level_encoded = _encode_string(trust_level.upper())

    # Offsets: 3 words (96 bytes) for the head, then dynamic data
    agent_id_offset = 96  # 3 * 32
    trust_level_offset = agent_id_offset + len(agent_id_encoded) // 2

    head = (
        hex(agent_id_offset)[2:].zfill(64)
        + hex(trust_level_offset)[2:].zfill(64)
        + ph.zfill(64)
    )
    return "0x" + head + agent_id_encoded + trust_level_encoded


def decode_kya_data(data: str) -> tuple[str, str, str]:
    """Decode ABI-encoded KYA attestation data.

    Args:
        data: ABI-encoded hex string (with or without 0x prefix).

    Returns:
        Tuple of (agent_id, trust_level, policy_hash_hex).
    """
    raw = data.removeprefix("0x")
    if len(raw) < 192:  # minimum: 3 words head
        raise ValueError("Data too short for KYA attestation")

    # Parse head: offset1, offset2, bytes32
    agent_id_offset = int(raw[0:64], 16) * 2  # convert byte offset to hex offset
    trust_level_offset = int(raw[64:128], 16) * 2
    policy_hash = raw[128:192]

    def _decode_string(offset: int) -> str:
        length = int(raw[offset : offset + 64], 16)
        string_hex = raw[offset + 64 : offset + 64 + length * 2]
        return bytes.fromhex(string_hex).decode("utf-8")

    agent_id = _decode_string(agent_id_offset)
    trust_level = _decode_string(trust_level_offset)

    return agent_id, trust_level, "0x" + policy_hash


class EASKYAClient:
    """Client for creating and verifying KYA attestations via EAS.

    Uses the chain executor to interact with the EAS contract on Base.
    """

    def __init__(
        self,
        rpc_client: Any,
        schema_uid: str,
        *,
        eas_address: str = EAS_ADDRESS,
    ):
        self._rpc = rpc_client
        self._schema_uid = schema_uid.removeprefix("0x").zfill(64)
        self._eas_address = eas_address

    async def create_attestation(
        self,
        agent_id: str,
        trust_level: str,
        policy_hash: str,
        *,
        signer: Any = None,
        recipient: str = "0x0000000000000000000000000000000000000000",
    ) -> KYAAttestation:
        """Create a KYA attestation on-chain via EAS.attest().

        Args:
            agent_id: Agent identifier.
            trust_level: Trust level (LOW/MEDIUM/HIGH/UNLIMITED).
            policy_hash: 32-byte hex policy hash.
            signer: MPC signer for transaction signing.
            recipient: Attestation recipient address.

        Returns:
            KYAAttestation with the on-chain UID.
        """
        attestation_data = encode_kya_data(agent_id, trust_level, policy_hash)

        # EAS.attest((bytes32 schema, (address recipient, uint64 expirationTime,
        #   bool revocable, bytes32 refUID, bytes data, uint256 value)))
        # Function selector: 0xf17325e7
        schema_padded = self._schema_uid.zfill(64)
        recipient_padded = recipient.removeprefix("0x").lower().zfill(64)
        expiration = "0" * 64  # no expiration
        revocable = "0" * 63 + "1"  # revocable = true
        ref_uid = "0" * 64  # no referenced attestation
        value = "0" * 64  # no ETH value

        # Encode the AttestationRequest struct
        # offset to AttestationRequestData
        data_offset = hex(64)[2:].zfill(64)  # 32 bytes for schema + 32 for struct offset
        # AttestationRequestData has dynamic `data` field
        inner_data_offset = hex(192)[2:].zfill(64)  # 6 * 32 = offset to data within struct
        data_content = attestation_data.removeprefix("0x")
        data_length = hex(len(data_content) // 2)[2:].zfill(64)
        data_padded = data_content.ljust(((len(data_content) + 63) // 64) * 64, "0")

        calldata = (
            "0xf17325e7"
            + schema_padded
            + data_offset
            + recipient_padded
            + expiration
            + revocable
            + ref_uid
            + inner_data_offset
            + value
            + data_length
            + data_padded
        )

        logger.info(
            "Creating KYA attestation: agent=%s trust=%s",
            agent_id, trust_level,
        )

        if signer:
            tx_hash = await self._send_transaction(calldata, signer)
            # Parse attestation UID from transaction receipt logs
            uid = await self._get_attestation_uid_from_receipt(tx_hash)
        else:
            # Simulation mode: return a deterministic UID
            import hashlib
            uid_hash = hashlib.sha256(
                f"{agent_id}:{trust_level}:{policy_hash}".encode()
            ).digest()
            uid = uid_hash

        return KYAAttestation(
            agent_id=agent_id,
            trust_level=trust_level.upper(),
            policy_hash=policy_hash,
            attestation_uid=uid,
        )

    async def verify_attestation(self, uid: bytes) -> KYAAttestation | None:
        """Verify a KYA attestation by reading it from EAS.

        Args:
            uid: 32-byte attestation UID.

        Returns:
            KYAAttestation if valid and not revoked, None otherwise.
        """
        # EAS.getAttestation(bytes32 uid) -> Attestation struct
        # Function selector: 0xa3112a64
        uid_hex = uid.hex().zfill(64)
        calldata = "0xa3112a64" + uid_hex

        try:
            result = await self._rpc.eth_call(
                {"to": self._eas_address, "data": calldata},
                "latest",
            )
            return self._parse_attestation_result(result, uid)
        except Exception as e:
            logger.error("Failed to verify attestation %s: %s", uid.hex(), e)
            return None

    async def revoke_attestation(self, uid: bytes, *, signer: Any = None) -> bool:
        """Revoke a KYA attestation via EAS.revoke().

        Args:
            uid: 32-byte attestation UID.
            signer: MPC signer for transaction signing.

        Returns:
            True if revocation succeeded.
        """
        # EAS.revoke((bytes32 schema, (bytes32 uid, uint256 value)))
        # Function selector: 0x46926267
        schema_padded = self._schema_uid.zfill(64)
        uid_hex = uid.hex().zfill(64)
        data_offset = hex(64)[2:].zfill(64)
        value = "0" * 64

        calldata = "0x46926267" + schema_padded + data_offset + uid_hex + value

        logger.info("Revoking KYA attestation: uid=%s", uid.hex())

        if signer:
            await self._send_transaction(calldata, signer)
        return True

    def _parse_attestation_result(
        self, result: str, uid: bytes
    ) -> KYAAttestation | None:
        """Parse the Attestation struct returned by EAS.getAttestation()."""
        raw = result.removeprefix("0x")
        if len(raw) < 512:  # minimum attestation struct size
            return None

        # Attestation struct layout:
        # bytes32 uid, bytes32 schema, uint64 time, uint64 expirationTime,
        # uint64 revocationTime, bytes32 refUID, address recipient,
        # address attester, bool revocable, bytes data
        revocation_time = int(raw[256:320], 16) if len(raw) > 320 else 0
        attester_raw = raw[448:512] if len(raw) > 512 else "0" * 64
        attester = "0x" + attester_raw[-40:]

        if revocation_time > 0:
            logger.info("Attestation %s is revoked", uid.hex())
            return KYAAttestation(
                agent_id="",
                trust_level="",
                policy_hash="",
                attestation_uid=uid,
                attester=attester,
                revoked=True,
            )

        # Find and decode the attestation data
        # The data field is dynamic, located at the offset specified in the struct
        try:
            # Data offset is at position 9 in the struct (index 576 hex chars)
            data_offset_hex = raw[576:640] if len(raw) > 640 else None
            if data_offset_hex:
                data_offset = int(data_offset_hex, 16) * 2
                data_length = int(raw[data_offset : data_offset + 64], 16)
                data_hex = raw[data_offset + 64 : data_offset + 64 + data_length * 2]
                agent_id, trust_level, policy_hash = decode_kya_data(data_hex)
                return KYAAttestation(
                    agent_id=agent_id,
                    trust_level=trust_level,
                    policy_hash=policy_hash,
                    attestation_uid=uid,
                    attester=attester,
                )
        except Exception as e:
            logger.warning("Failed to decode attestation data: %s", e)

        return None

    async def _send_transaction(self, calldata: str, signer: Any) -> str:
        """Send a transaction to the EAS contract."""
        tx_params = {
            "to": self._eas_address,
            "data": calldata,
            "value": "0x0",
        }
        return await signer.sign_and_send(tx_params)

    async def _get_attestation_uid_from_receipt(self, tx_hash: str) -> bytes:
        """Extract attestation UID from transaction receipt logs."""
        receipt = await self._rpc.get_transaction_receipt(tx_hash)
        if receipt and receipt.get("logs"):
            # The Attested event is the first log, topic[1] is the UID
            for log in receipt["logs"]:
                if len(log.get("topics", [])) >= 2:
                    uid_hex = log["topics"][1].removeprefix("0x")
                    return bytes.fromhex(uid_hex)
        raise RuntimeError(f"Could not extract attestation UID from tx {tx_hash}")
