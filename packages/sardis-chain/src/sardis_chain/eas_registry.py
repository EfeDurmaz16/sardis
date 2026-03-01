"""EAS (Ethereum Attestation Service) adapter for agent identity.

Replaces custom SardisAgentRegistry.sol with EAS — already audited and
deployed on all chains. Agent identity, reputation, and validation are
stored as on-chain attestations using EAS schemas.

EAS is:
- Audited, open source (MIT)
- Predeploy on OP Stack chains (Base, Optimism)
- Deployed on Ethereum, Polygon, Arbitrum
- Used by Coinbase, Optimism, Worldcoin

References:
- https://attest.org
- https://github.com/ethereum-attestation-service/eas-contracts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from eth_abi import encode

logger = logging.getLogger(__name__)


# ============ EAS Contract Addresses (canonical, already deployed) ============

EAS_ADDRESSES = {
    # OP Stack predeploys (same address)
    "base": "0x4200000000000000000000000000000000000021",
    "optimism": "0x4200000000000000000000000000000000000021",
    # Other chains
    "ethereum": "0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587",
    "polygon": "0x5E634ef5355f45A855d02D66eCD687b1502AF790",
    "arbitrum": "0xbD75f629A22Dc1ceD33dDA0b68c546A1c035c458",
    # Testnets
    "base_sepolia": "0x4200000000000000000000000000000000000021",
    "optimism_sepolia": "0x4200000000000000000000000000000000000021",
    "ethereum_sepolia": "0xC2679fBD37d54388Ce493F1DB75320D236e1815e",
    "arbitrum_sepolia": "0xaEF4103A04090071165F78D45D83A0C0782c2B2a",
}

SCHEMA_REGISTRY_ADDRESSES = {
    "ethereum": "0xA7b39296258348C78294F95B872b282326A97BDF",
    "base": "0x4200000000000000000000000000000000000020",
    "optimism": "0x4200000000000000000000000000000000000020",
    "polygon": "0xA7b39296258348C78294F95B872b282326A97BDF",
    "arbitrum": "0xA310da9c5B885E7fb3fbA9D66E9Ba6Df512b78eB",
    "base_sepolia": "0x4200000000000000000000000000000000000020",
    "optimism_sepolia": "0x4200000000000000000000000000000000000020",
    "ethereum_sepolia": "0x0a7E2Ff54e76B8E6659aedc9103FB21c038050D0",
    "arbitrum_sepolia": "0x55D26f9ae0203EF95494AE4C170eD35f4Cf77797",
}


# ============ EAS Schema Definitions ============
# These schemas will be registered once per chain via SchemaRegistry.register()

# Agent Identity: core agent metadata
AGENT_IDENTITY_SCHEMA = "address agentWallet,string agentURI,string name,string version"

# Agent Reputation: agent-to-agent scoring
AGENT_REPUTATION_SCHEMA = "address fromAgent,address toAgent,uint16 score,string category"

# Agent Validation: trusted validator attestations (KYC, audit, cert)
AGENT_VALIDATION_SCHEMA = "address agent,bool isValid,string validationType,string evidenceURI"


# ============ EAS ABI Selectors ============

# EAS.attest((bytes32 schema, (address recipient, uint64 expirationTime,
#   bool revocable, bytes32 refUID, bytes data, uint256 value)))
_ATTEST_SELECTOR = Web3.keccak(
    text="attest((bytes32,(address,uint64,bool,bytes32,bytes,uint256)))"
)[:4]

# SchemaRegistry.register(string schema, address resolver, bool revocable)
_REGISTER_SCHEMA_SELECTOR = Web3.keccak(
    text="register(string,address,bool)"
)[:4]


@dataclass
class AgentAttestation:
    """Represents an agent identity attestation via EAS."""
    uid: str  # Attestation UID (bytes32)
    agent_wallet: str
    agent_uri: str
    name: str
    version: str
    chain: str
    attester: str


class EASAgentRegistry:
    """
    Agent identity registry using EAS (Ethereum Attestation Service).

    Replaces SardisAgentRegistry.sol (357 LOC, custom, unaudited) with
    EAS (audited, deployed on all chains, ecosystem-wide).

    Features mapped from SardisAgentRegistry:
    - Agent registration -> EAS attestation with AGENT_IDENTITY_SCHEMA
    - Reputation scoring -> EAS attestation with AGENT_REPUTATION_SCHEMA
    - Validator attestations -> EAS attestation with AGENT_VALIDATION_SCHEMA
    """

    def __init__(self, chain: str, sardis_address: str):
        self._chain = chain
        self._sardis_address = sardis_address
        self._eas_address = EAS_ADDRESSES.get(chain, "")
        self._schema_registry = SCHEMA_REGISTRY_ADDRESSES.get(chain, "")

    @property
    def eas_address(self) -> str:
        return self._eas_address

    @property
    def is_available(self) -> bool:
        return bool(self._eas_address)

    def encode_register_schema(self, schema: str, revocable: bool = True) -> bytes:
        """Encode SchemaRegistry.register() calldata.

        Call this once per chain to register Sardis agent schemas.
        """
        params = encode(
            ["string", "address", "bool"],
            [schema, "0x0000000000000000000000000000000000000000", revocable],
        )
        return _REGISTER_SCHEMA_SELECTOR + params

    def encode_register_agent(
        self,
        schema_uid: str,
        agent_wallet: str,
        agent_uri: str,
        name: str,
        version: str = "1.0",
    ) -> bytes:
        """Encode EAS.attest() calldata for agent registration.

        Args:
            schema_uid: UID of the registered AGENT_IDENTITY_SCHEMA
            agent_wallet: Agent's wallet address
            agent_uri: IPFS/HTTP URI to agent metadata
            name: Agent display name
            version: Agent version string
        """
        # Encode the attestation data
        attestation_data = encode(
            ["address", "string", "string", "string"],
            [Web3.to_checksum_address(agent_wallet), agent_uri, name, version],
        )

        # Encode the AttestationRequest struct
        # (bytes32 schema, (address recipient, uint64 expirationTime,
        #   bool revocable, bytes32 refUID, bytes data, uint256 value))
        inner = encode(
            ["address", "uint64", "bool", "bytes32", "bytes", "uint256"],
            [
                Web3.to_checksum_address(agent_wallet),  # recipient
                0,  # expirationTime (0 = never)
                True,  # revocable
                b"\x00" * 32,  # refUID (none)
                attestation_data,  # data
                0,  # value (no ETH)
            ],
        )

        outer = encode(
            ["bytes32", "bytes"],
            [bytes.fromhex(schema_uid[2:] if schema_uid.startswith("0x") else schema_uid), inner],
        )

        return _ATTEST_SELECTOR + outer

    def encode_submit_reputation(
        self,
        schema_uid: str,
        from_agent: str,
        to_agent: str,
        score: int,
        category: str,
    ) -> bytes:
        """Encode EAS.attest() for reputation scoring."""
        attestation_data = encode(
            ["address", "address", "uint16", "string"],
            [
                Web3.to_checksum_address(from_agent),
                Web3.to_checksum_address(to_agent),
                score,
                category,
            ],
        )

        inner = encode(
            ["address", "uint64", "bool", "bytes32", "bytes", "uint256"],
            [
                Web3.to_checksum_address(to_agent),
                0,
                True,
                b"\x00" * 32,
                attestation_data,
                0,
            ],
        )

        outer = encode(
            ["bytes32", "bytes"],
            [bytes.fromhex(schema_uid[2:] if schema_uid.startswith("0x") else schema_uid), inner],
        )

        return _ATTEST_SELECTOR + outer

    def encode_submit_validation(
        self,
        schema_uid: str,
        agent: str,
        is_valid: bool,
        validation_type: str,
        evidence_uri: str,
    ) -> bytes:
        """Encode EAS.attest() for validator attestation."""
        attestation_data = encode(
            ["address", "bool", "string", "string"],
            [Web3.to_checksum_address(agent), is_valid, validation_type, evidence_uri],
        )

        inner = encode(
            ["address", "uint64", "bool", "bytes32", "bytes", "uint256"],
            [
                Web3.to_checksum_address(agent),
                0,
                True,
                b"\x00" * 32,
                attestation_data,
                0,
            ],
        )

        outer = encode(
            ["bytes32", "bytes"],
            [bytes.fromhex(schema_uid[2:] if schema_uid.startswith("0x") else schema_uid), inner],
        )

        return _ATTEST_SELECTOR + outer
