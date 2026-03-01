"""Agent Card generation for A2A/AP2 protocol compatibility."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .erc8004 import AgentIdentity

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentCard:
    """
    Agent Card following A2A/AP2 agent card specification.

    Agent cards are discoverable identity documents that enable
    agent-to-agent communication and payment protocols.
    """

    agent_id: str
    name: str
    description: str
    version: str
    owner: str  # Ethereum address or DID
    capabilities: list[str] = field(default_factory=list)
    protocols: list[str] = field(default_factory=lambda: ["a2a", "ap2"])
    endpoints: dict[str, str] = field(default_factory=dict)
    public_key: str | None = None  # For signature verification
    ens_name: str | None = None
    chain_id: int = 1
    created_at: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Export as JSON-serializable dict."""
        card = {
            "@context": "https://sardis.sh/agent-card/v1",
            "type": "AgentCard",
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "owner": self.owner,
            "capabilities": self.capabilities,
            "protocols": self.protocols,
            "endpoints": self.endpoints,
            "chain_id": self.chain_id,
            "created_at": self.created_at,
        }

        if self.public_key:
            card["public_key"] = self.public_key

        if self.ens_name:
            card["ens_name"] = self.ens_name

        return card

    @property
    def fingerprint(self) -> str:
        """Generate card fingerprint (hash of canonical JSON)."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> AgentCard:
        """Parse from JSON dict."""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data["description"],
            version=data["version"],
            owner=data["owner"],
            capabilities=data.get("capabilities", []),
            protocols=data.get("protocols", ["a2a", "ap2"]),
            endpoints=data.get("endpoints", {}),
            public_key=data.get("public_key"),
            ens_name=data.get("ens_name"),
            chain_id=data.get("chain_id", 1),
            created_at=data.get("created_at", 0),
        )


def generate_agent_card(
    identity: AgentIdentity,
    capabilities: list[str] | None = None,
    public_key: str | None = None,
    endpoints: dict[str, str] | None = None,
) -> dict:
    """
    Generate A2A/AP2 agent card from ERC-8004 identity.

    Args:
        identity: ERC-8004 agent identity
        capabilities: Optional capability overrides
        public_key: Optional public key for signature verification
        endpoints: Optional service endpoints

    Returns:
        Agent card as JSON dict
    """
    metadata = identity.metadata

    card = AgentCard(
        agent_id=identity.agent_id,
        name=metadata.get("name", f"Agent {identity.agent_id}"),
        description=metadata.get("description", ""),
        version=metadata.get("version", "1.0.0"),
        owner=identity.owner_address,
        capabilities=capabilities or metadata.get("capabilities", []),
        protocols=metadata.get("protocols_supported", ["a2a", "ap2"]),
        endpoints=endpoints or metadata.get("service_endpoints", {}),
        public_key=public_key,
        ens_name=identity.ens_name,
        chain_id=identity.chain_id,
        created_at=identity.created_at,
    )

    return card.to_dict()


def verify_agent_card(card: dict) -> bool:
    """
    Verify agent card integrity and signature.

    Args:
        card: Agent card dict

    Returns:
        True if valid, False otherwise
    """
    # Basic structure validation
    required_fields = ["agent_id", "name", "description", "version", "owner"]
    if not all(field in card for field in required_fields):
        return False

    # Validate context
    if card.get("@context") != "https://sardis.sh/agent-card/v1":
        return False

    # Validate type
    if card.get("type") != "AgentCard":
        return False

    # Validate protocols
    protocols = card.get("protocols", [])
    if not isinstance(protocols, list) or not protocols:
        return False

    # Signature verification if public_key and signature present
    public_key = card.get("public_key")
    signature = card.get("signature")

    if public_key and signature:
        if not _verify_card_signature(card, public_key, signature):
            return False

    return True


def _canonical_card_json(card: dict) -> bytes:
    """Build canonical JSON for signature verification (excludes signature field)."""
    card_copy = {k: v for k, v in card.items() if k != "signature"}
    return json.dumps(card_copy, sort_keys=True, separators=(",", ":")).encode()


def _verify_card_signature(card: dict, public_key: str, signature: str) -> bool:
    """
    Verify agent card signature using Ed25519 or ECDSA-P256.

    Supports public_key formats:
      - "ed25519:<hex>" - Ed25519 public key (hex-encoded)
      - "ecdsa-p256:<hex>" - ECDSA P-256 public key (hex-encoded, uncompressed)
      - 64-char hex string - assumed Ed25519

    Signature is base64-encoded.
    """
    try:
        sig_bytes = base64.b64decode(signature)
    except Exception:
        logger.debug("Invalid base64 signature in agent card")
        return False

    message = _canonical_card_json(card)

    # Determine algorithm and raw key bytes
    if public_key.startswith("ed25519:"):
        return _verify_ed25519(bytes.fromhex(public_key[8:]), message, sig_bytes)
    elif public_key.startswith("ecdsa-p256:"):
        return _verify_ecdsa_p256(bytes.fromhex(public_key[11:]), message, sig_bytes)
    elif len(public_key) == 64:
        # 64 hex chars = 32 bytes = Ed25519 public key
        return _verify_ed25519(bytes.fromhex(public_key), message, sig_bytes)
    else:
        logger.debug("Unsupported public_key format in agent card: %s...", public_key[:20])
        return False


def _verify_ed25519(key_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify Ed25519 signature."""
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        verify_key = VerifyKey(key_bytes)
        verify_key.verify(message, signature)
        return True
    except (BadSignatureError, ValueError, Exception) as e:
        logger.debug("Ed25519 verification failed: %s", e)
        return False


def _verify_ecdsa_p256(key_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify ECDSA P-256 (ES256) signature."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes

        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), key_bytes,
        )
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception as e:
        logger.debug("ECDSA-P256 verification failed: %s", e)
        return False


def bind_ens_name(card: dict, ens_name: str) -> dict:
    """
    Bind ENS name to agent card.

    Args:
        card: Agent card dict
        ens_name: ENS name (e.g., "myagent.eth")

    Returns:
        Updated agent card with ENS binding
    """
    card["ens_name"] = ens_name

    # Add ENS resolution endpoint
    if "endpoints" not in card:
        card["endpoints"] = {}

    card["endpoints"]["ens_resolver"] = f"https://ens.eth/resolve/{ens_name}"

    return card


def resolve_agent_card_uri(agent_id: str, chain_id: int = 1) -> str:
    """
    Generate standard agent card URI.

    Args:
        agent_id: Agent token ID
        chain_id: Chain ID where agent is registered

    Returns:
        Agent card URI
    """
    return f"https://sardis.sh/api/v2/agents/identity/{agent_id}/card?chain={chain_id}"
