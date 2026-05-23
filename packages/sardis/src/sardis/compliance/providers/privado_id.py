"""Privado ID (formerly Polygon ID) zero-knowledge identity provider.

Integrates Privado ID's iden3 protocol for privacy-preserving identity
verification using W3C Verifiable Credentials and ZK proofs.

Enables KYC compliance without revealing underlying PII — users prove
credential properties (age > 18, not sanctioned) via zkSNARK proofs.

Architecture:
    [KYC Provider] → Issues VC to user wallet
    [Sardis]       → Generates auth request (query)
    [User Wallet]  → Generates ZK proof
    [Sardis]       → Verifies proof off-chain or on-chain

Reference: https://docs.privado.id/
Issue: #138
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ============ Constants ============

PRIVADO_API_URLS = {
    "mainnet": "https://issuer-node.privado.id",
    "testnet": "https://issuer-node.polygonid.me",
}

DEFAULT_ENVIRONMENT = "testnet"

# Supported proof types
PROOF_TYPE_SIG = "BJJSignature2021"
PROOF_TYPE_MTP = "Iden3SparseMerkleTreeProof"

# Common credential schemas
CREDENTIAL_SCHEMAS = {
    "kyc_age": "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v4.jsonld",
    "kyc_country": "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/kyc-v4.jsonld",
    "proof_of_humanity": "https://raw.githubusercontent.com/iden3/claim-schema-vocab/main/schemas/json-ld/proof-of-humanity.jsonld",
}

# Query operators for ZK proof requests
class QueryOperator(Enum):
    """Supported query operators for credential verification."""
    NOOP = 0        # No operation
    EQUALS = 1      # ==
    LESS_THAN = 2   # <
    GREATER_THAN = 3  # >
    IN = 4          # in [set]
    NOT_IN = 5      # not in [set]
    NOT_EQUALS = 6  # !=
    LESS_THAN_EQ = 7    # <=
    GREATER_THAN_EQ = 8  # >=
    EXISTS = 9      # field exists
    BETWEEN = 10    # between [a, b]
    SD = 16         # selective disclosure


# ============ Enums ============

class CredentialStatus(str, Enum):
    """Status of a Verifiable Credential."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


class ProofVerificationStatus(str, Enum):
    """Result of ZK proof verification."""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


# ============ Data Models ============

@dataclass
class CredentialQuery:
    """A query for ZK proof verification.

    Defines what the user must prove about their credentials.
    Example: "Prove your age > 18 from a KYC credential"
    """
    schema_url: str
    credential_type: str
    field_name: str
    operator: QueryOperator
    value: list[int] = field(default_factory=list)
    proof_type: str = PROOF_TYPE_SIG

    def to_dict(self) -> dict[str, Any]:
        """Convert to Privado ID query format."""
        query: dict[str, Any] = {
            "allowedIssuers": ["*"],
            "type": self.credential_type,
            "context": self.schema_url,
            "credentialSubject": {
                self.field_name: {
                    "$operator": self.operator.value,
                }
            },
        }
        if self.value:
            query["credentialSubject"][self.field_name]["$value"] = (
                self.value[0] if len(self.value) == 1 else self.value
            )
        return query


@dataclass
class AuthRequest:
    """Authentication request sent to user wallet for ZK proof generation."""
    request_id: str
    query: CredentialQuery
    reason: str = ""
    scope: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to Privado ID auth request format."""
        scope_item = {
            "id": 1,
            "circuitId": "credentialAtomicQueryV3",
            "query": self.query.to_dict(),
        }
        return {
            "id": self.request_id,
            "typ": "application/iden3-zkp-json",
            "type": "https://iden3-communication.io/authorization/1.0/request",
            "body": {
                "reason": self.reason or "Sardis identity verification",
                "scope": [scope_item] + self.scope,
            },
        }


@dataclass
class ProofVerificationResult:
    """Result of verifying a ZK proof."""
    status: ProofVerificationStatus
    credential_type: str = ""
    issuer_did: str = ""
    proof_valid: bool = False
    revocation_checked: bool = False
    credential_revoked: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_valid(self) -> bool:
        """Whether the proof is valid and credential not revoked."""
        return (
            self.status == ProofVerificationStatus.VALID
            and self.proof_valid
            and not self.credential_revoked
        )


@dataclass
class IssuedCredential:
    """A credential issued to a holder."""
    credential_id: str
    issuer_did: str
    holder_did: str
    credential_type: str
    schema_url: str
    status: CredentialStatus = CredentialStatus.ACTIVE
    claims: dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


class PrivadoIDError(Exception):
    """Error from Privado ID API or verification."""
    pass


# ============ Common Queries ============

def build_age_query(min_age: int = 18) -> CredentialQuery:
    """Build a query to prove user is at least min_age years old."""
    return CredentialQuery(
        schema_url=CREDENTIAL_SCHEMAS["kyc_age"],
        credential_type="KYCAgeCredential",
        field_name="birthday",
        operator=QueryOperator.LESS_THAN,
        # Birthday must be before (current_year - min_age)
        value=[_birthday_threshold(min_age)],
    )


def build_country_query(
    allowed_countries: list[int] | None = None,
    blocked_countries: list[int] | None = None,
) -> CredentialQuery:
    """Build a query to prove user's country is/isn't in a set.

    Country codes use ISO 3166-1 numeric codes (e.g., 840=US, 276=DE).
    """
    if blocked_countries:
        return CredentialQuery(
            schema_url=CREDENTIAL_SCHEMAS["kyc_country"],
            credential_type="KYCCountryOfResidenceCredential",
            field_name="countryCode",
            operator=QueryOperator.NOT_IN,
            value=blocked_countries,
        )
    return CredentialQuery(
        schema_url=CREDENTIAL_SCHEMAS["kyc_country"],
        credential_type="KYCCountryOfResidenceCredential",
        field_name="countryCode",
        operator=QueryOperator.IN,
        value=allowed_countries or [],
    )


def build_humanity_query() -> CredentialQuery:
    """Build a query to prove user is human (Sybil resistance)."""
    return CredentialQuery(
        schema_url=CREDENTIAL_SCHEMAS["proof_of_humanity"],
        credential_type="ProofOfHumanity",
        field_name="isHuman",
        operator=QueryOperator.EQUALS,
        value=[1],
    )


def _birthday_threshold(min_age: int) -> int:
    """Calculate birthday threshold date as integer (YYYYMMDD)."""
    now = datetime.now(UTC)
    threshold_year = now.year - min_age
    return threshold_year * 10000 + now.month * 100 + now.day


# ============ Provider ============

class PrivadoIDProvider:
    """Privado ID zero-knowledge identity verification provider.

    Integrates with Privado ID's issuer node and verifier APIs for
    privacy-preserving credential verification.

    Configuration via environment variables:
        PRIVADO_ID_ISSUER_URL      — Issuer node API URL
        PRIVADO_ID_ISSUER_USER     — Issuer API username
        PRIVADO_ID_ISSUER_PASSWORD — Issuer API password
        PRIVADO_ID_ENVIRONMENT     — "mainnet" or "testnet" (default: testnet)

    Usage:
        provider = PrivadoIDProvider()
        auth_req = provider.create_auth_request(build_age_query(18))
        # ... user generates ZK proof in wallet ...
        result = await provider.verify_proof(proof_data)
    """

    def __init__(
        self,
        issuer_url: str | None = None,
        issuer_user: str | None = None,
        issuer_password: str | None = None,
        environment: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        env = environment or os.getenv("PRIVADO_ID_ENVIRONMENT", DEFAULT_ENVIRONMENT)
        self._issuer_url = (
            issuer_url
            or os.getenv("PRIVADO_ID_ISSUER_URL")
            or PRIVADO_API_URLS.get(env, PRIVADO_API_URLS[DEFAULT_ENVIRONMENT])
        )
        self._issuer_user = issuer_user or os.getenv("PRIVADO_ID_ISSUER_USER", "")
        self._issuer_password = issuer_password or os.getenv("PRIVADO_ID_ISSUER_PASSWORD", "")
        self._timeout = timeout
        # In-memory auth request tracking
        self._pending_requests: dict[str, AuthRequest] = {}

    @property
    def is_configured(self) -> bool:
        """Whether the provider has valid credentials."""
        return bool(self._issuer_url and self._issuer_user and self._issuer_password)

    def _auth(self) -> tuple[str, str]:
        """Return HTTP basic auth tuple."""
        return (self._issuer_user, self._issuer_password)

    def create_auth_request(
        self,
        query: CredentialQuery,
        reason: str = "",
        request_id: str | None = None,
    ) -> AuthRequest:
        """Create an authentication request for ZK proof generation.

        The resulting auth request should be sent to the user's wallet
        (via QR code or deep link). The wallet generates a ZK proof
        and sends it back.

        Args:
            query: The credential query defining what to prove.
            reason: Human-readable reason for the request.
            request_id: Optional custom request ID.
        """
        rid = request_id or hashlib.sha256(
            f"{query.credential_type}:{datetime.now(UTC).isoformat()}".encode()
        ).hexdigest()[:16]

        auth_req = AuthRequest(
            request_id=rid,
            query=query,
            reason=reason,
        )
        self._pending_requests[rid] = auth_req
        return auth_req

    async def issue_credential(
        self,
        holder_did: str,
        credential_type: str,
        schema_url: str,
        claims: dict[str, Any],
        expiration: str | None = None,
    ) -> IssuedCredential:
        """Issue a Verifiable Credential to a holder.

        Args:
            holder_did: DID of the credential holder.
            credential_type: Type of credential (e.g., "KYCAgeCredential").
            schema_url: JSON-LD schema URL.
            claims: Credential claim data.
            expiration: Optional expiration date (ISO 8601).

        Returns:
            IssuedCredential with credential ID.

        Raises:
            PrivadoIDError: On API errors.
        """
        if not self.is_configured:
            raise PrivadoIDError("Privado ID provider not configured")

        payload: dict[str, Any] = {
            "credentialSchema": schema_url,
            "type": credential_type,
            "credentialSubject": {
                "id": holder_did,
                **claims,
            },
        }
        if expiration:
            payload["expiration"] = expiration

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._issuer_url}/v1/credentials",
                    auth=self._auth(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise PrivadoIDError(
                f"Privado ID credential issuance error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise PrivadoIDError(f"Privado ID issuance request failed: {e}") from e

        return IssuedCredential(
            credential_id=data.get("id", ""),
            issuer_did=data.get("issuer", ""),
            holder_did=holder_did,
            credential_type=credential_type,
            schema_url=schema_url,
            claims=claims,
        )

    async def revoke_credential(self, credential_id: str, nonce: int = 0) -> bool:
        """Revoke a previously issued credential.

        Args:
            credential_id: The credential ID to revoke.
            nonce: Revocation nonce.

        Returns:
            True if revocation succeeded.
        """
        if not self.is_configured:
            raise PrivadoIDError("Privado ID provider not configured")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._issuer_url}/v1/credentials/revoke/{nonce}",
                    auth=self._auth(),
                )
                resp.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            raise PrivadoIDError(
                f"Privado ID revocation error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise PrivadoIDError(f"Privado ID revocation failed: {e}") from e

    async def verify_proof(
        self,
        proof_data: dict[str, Any],
        request_id: str | None = None,
    ) -> ProofVerificationResult:
        """Verify a ZK proof submitted by a user wallet.

        The proof_data should contain the ZK proof generated by the
        wallet in response to an auth request.

        Args:
            proof_data: The ZK proof payload from the wallet.
            request_id: The auth request ID this proof responds to.

        Returns:
            ProofVerificationResult with verification status.

        Raises:
            PrivadoIDError: On API errors.
        """
        if not self.is_configured:
            raise PrivadoIDError("Privado ID provider not configured")

        # Extract proof fields
        proof_body = proof_data.get("body", {})
        scope_responses = proof_body.get("scope", [])

        if not scope_responses:
            return ProofVerificationResult(
                status=ProofVerificationStatus.INVALID,
                details={"error": "No proof scope in response"},
            )

        # Verify via issuer node's callback endpoint
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._issuer_url}/v1/agent",
                    auth=self._auth(),
                    json=proof_data,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 422):
                return ProofVerificationResult(
                    status=ProofVerificationStatus.INVALID,
                    details={"error": f"Invalid proof: {e.response.status_code}"},
                )
            raise PrivadoIDError(
                f"Privado ID verification error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise PrivadoIDError(f"Privado ID verification failed: {e}") from e

        # Parse verification result
        verified = data.get("verified", False)
        credential_type = ""
        issuer_did = ""

        if scope_responses:
            first_scope = scope_responses[0]
            credential_type = first_scope.get("type", "")
            issuer_did = first_scope.get("issuer", "")

        # Clean up pending request
        if request_id and request_id in self._pending_requests:
            del self._pending_requests[request_id]

        return ProofVerificationResult(
            status=ProofVerificationStatus.VALID if verified else ProofVerificationStatus.INVALID,
            credential_type=credential_type,
            issuer_did=issuer_did,
            proof_valid=verified,
            revocation_checked=True,
            credential_revoked=data.get("revoked", False),
            details=data,
        )

    async def check_credential_status(
        self,
        credential_id: str,
    ) -> CredentialStatus:
        """Check the revocation status of a credential.

        Args:
            credential_id: The credential ID to check.

        Returns:
            Current CredentialStatus.
        """
        if not self.is_configured:
            raise PrivadoIDError("Privado ID provider not configured")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._issuer_url}/v1/credentials/{credential_id}",
                    auth=self._auth(),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            raise PrivadoIDError(
                f"Privado ID status check error: {e.response.status_code}"
            ) from e
        except Exception as e:
            raise PrivadoIDError(f"Privado ID status check failed: {e}") from e

        revoked = data.get("revoked", False)
        if revoked:
            return CredentialStatus.REVOKED
        return CredentialStatus.ACTIVE

    async def health_check(self) -> bool:
        """Check if the Privado ID issuer node is reachable."""
        if not self.is_configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._issuer_url}/status",
                    auth=self._auth(),
                )
                return resp.status_code in (200, 401, 403, 404)
        except Exception:
            return False
