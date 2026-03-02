"""Coinbase Verifications integration (EAS-based on-chain identity).

Coinbase Verifications provides on-chain identity attestations via EAS
on Base. Verified users receive attestations that confirm identity
verification status without revealing personal data on-chain.

This module checks whether a wallet address has valid Coinbase
Verifications attestations, enabling enhanced trust levels and
higher spending limits for verified agents.

Reference: https://docs.coinbase.com/verifications
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Coinbase Verifications EAS schema on Base
# Schema: "bool isVerified"
COINBASE_VERIFICATIONS_SCHEMA_UID = (
    "0xf8b05c79f090979bf4a80270aba232dff11a10d9ca55c4f88de95317970f0de9"
)

# Coinbase Verifications attester address on Base
COINBASE_ATTESTER = "0x357458739F90461b99789350868CD7CF330Dd7EE"

# EAS GraphQL endpoint on Base
EAS_GRAPHQL_BASE = "https://base.easscan.org/graphql"


class CoinbaseVerificationError(Exception):
    """Error querying Coinbase Verifications."""
    pass


@dataclass
class VerificationResult:
    """Result of a Coinbase Verification check."""

    address: str
    is_verified: bool
    attestation_uid: Optional[str] = None
    attester: Optional[str] = None
    timestamp: Optional[int] = None


@dataclass
class Attestation:
    """A single EAS attestation."""

    uid: str
    schema_uid: str
    attester: str
    recipient: str
    revoked: bool
    timestamp: int
    data: str = ""


class CoinbaseVerificationsClient:
    """On-chain identity verification via Coinbase Verifications (EAS-based).

    Checks if a wallet address has been verified through Coinbase's
    identity verification process. Verified addresses receive EAS
    attestations on Base that can be checked on-chain or via the
    EAS GraphQL API.
    """

    def __init__(
        self,
        *,
        graphql_url: str = EAS_GRAPHQL_BASE,
        schema_uid: str = COINBASE_VERIFICATIONS_SCHEMA_UID,
        attester: str = COINBASE_ATTESTER,
        timeout_seconds: float = 15.0,
    ):
        self._graphql_url = graphql_url
        self._schema_uid = schema_uid
        self._attester = attester
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def check_verification(self, address: str) -> VerificationResult:
        """Check if an address has a valid Coinbase Verification.

        Args:
            address: EVM wallet address to check.

        Returns:
            VerificationResult indicating verification status.
        """
        attestations = await self.get_attestations(address)

        # Find the most recent non-revoked attestation
        for att in attestations:
            if not att.revoked and att.attester.lower() == self._attester.lower():
                return VerificationResult(
                    address=address,
                    is_verified=True,
                    attestation_uid=att.uid,
                    attester=att.attester,
                    timestamp=att.timestamp,
                )

        return VerificationResult(
            address=address,
            is_verified=False,
        )

    async def get_attestations(self, address: str) -> list[Attestation]:
        """Get all Coinbase Verification attestations for an address.

        Queries the EAS GraphQL API for attestations matching the
        Coinbase Verifications schema.

        Args:
            address: Recipient wallet address.

        Returns:
            List of attestations (may be empty).
        """
        query = """
        query GetAttestations($recipient: String!, $schemaId: String!) {
            attestations(
                where: {
                    recipient: { equals: $recipient }
                    schemaId: { equals: $schemaId }
                }
                orderBy: { timeCreated: desc }
                take: 10
            ) {
                id
                attester
                recipient
                revoked
                timeCreated
                schemaId
                decodedDataJson
            }
        }
        """
        variables = {
            "recipient": address.lower(),
            "schemaId": self._schema_uid,
        }

        try:
            resp = await self._client.post(
                self._graphql_url,
                json={"query": query, "variables": variables},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise CoinbaseVerificationError(
                f"EAS GraphQL error: {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            raise CoinbaseVerificationError("EAS GraphQL timeout") from e
        except Exception as e:
            raise CoinbaseVerificationError(f"EAS query failed: {e}") from e

        attestations_data = (
            data.get("data", {}).get("attestations", [])
        )

        result = []
        for att in attestations_data:
            result.append(Attestation(
                uid=att.get("id", ""),
                schema_uid=att.get("schemaId", ""),
                attester=att.get("attester", ""),
                recipient=att.get("recipient", ""),
                revoked=att.get("revoked", False),
                timestamp=att.get("timeCreated", 0),
                data=att.get("decodedDataJson", ""),
            ))

        return result

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
