"""FIDES Trust Graph adapter — async HTTP client for the FIDES trust network.

Wraps FIDES HTTP API as a drop-in for TrustGraphService interface.
Methods are async; callers should use inspect.isawaitable() for compatibility.

Graceful degradation: on failure, returns 0.0 / empty TrustPathResult (never blocks payments).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from .trust_graph import TrustPathNode, TrustPathResult

logger = logging.getLogger("sardis.core.fides_adapter")


@dataclass(frozen=True)
class FidesAttestation:
    """Result of submitting a trust attestation to FIDES."""
    success: bool
    attestation_id: str | None = None
    error: str | None = None


class FidesTrustGraphAdapter:
    """Async adapter bridging FIDES HTTP API to TrustGraphService interface.

    FIDES endpoints:
      GET  /v1/trust/{from_did}/{to_did} -> {found, path, cumulativeTrust, hops}
      GET  /v1/trust/{did}/score -> {did, score, directTrusters, transitiveTrusters}
      POST /v1/trust -> submit attestation
    """

    def __init__(
        self,
        trust_url: str = "http://localhost:3200",
        timeout_seconds: int = 5,
    ) -> None:
        self._trust_url = trust_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._trust_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get_trust_score(self, from_did: str, to_did: str) -> float:
        """Get transitive trust score between two DIDs.

        Returns 0.0 on any failure (graceful degradation).
        """
        if from_did == to_did:
            return 1.0
        try:
            client = await self._get_client()
            resp = await client.get(f"/v1/trust/{from_did}/{to_did}")
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("cumulativeTrust", 0.0))
        except Exception:
            logger.warning(
                "FIDES trust score lookup failed for %s -> %s, returning 0.0",
                from_did, to_did, exc_info=True,
            )
            return 0.0

    async def find_path(self, from_did: str, to_did: str) -> TrustPathResult:
        """Find trust path between two DIDs via FIDES BFS traversal.

        Returns empty TrustPathResult on any failure.
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"/v1/trust/{from_did}/{to_did}")
            resp.raise_for_status()
            data = resp.json()

            if not data.get("found", False):
                return TrustPathResult(
                    from_did=from_did, to_did=to_did, found=False, reason="no_path",
                )

            path_nodes = [
                TrustPathNode(did=node["did"], trust_level=int(node.get("trustLevel", 0)))
                for node in data.get("path", [])
            ]

            return TrustPathResult(
                from_did=from_did,
                to_did=to_did,
                found=True,
                path=path_nodes,
                cumulative_trust=float(data.get("cumulativeTrust", 0.0)),
                hops=int(data.get("hops", 0)),
            )
        except Exception:
            logger.warning(
                "FIDES path lookup failed for %s -> %s, returning empty path",
                from_did, to_did, exc_info=True,
            )
            return TrustPathResult(
                from_did=from_did, to_did=to_did, found=False, reason="fides_unavailable",
            )

    async def get_agent_score(self, did: str) -> dict[str, Any]:
        """Get standalone trust score for a single DID.

        Returns score info dict or empty dict on failure.
        """
        try:
            client = await self._get_client()
            resp = await client.get(f"/v1/trust/{did}/score")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning(
                "FIDES agent score lookup failed for %s", did, exc_info=True,
            )
            return {}

    async def submit_attestation(
        self,
        issuer_did: str,
        subject_did: str,
        trust_level: int,
        signature: str,
        payload: dict[str, Any] | None = None,
    ) -> FidesAttestation:
        """Submit a trust attestation to the FIDES network."""
        try:
            client = await self._get_client()
            body = {
                "issuerDid": issuer_did,
                "subjectDid": subject_did,
                "trustLevel": trust_level,
                "signature": signature,
                "payload": payload or {},
            }
            resp = await client.post("/v1/trust", json=body)
            resp.raise_for_status()
            data = resp.json()
            return FidesAttestation(
                success=True,
                attestation_id=data.get("attestationId"),
            )
        except Exception as e:
            logger.warning(
                "FIDES attestation submission failed: %s", e, exc_info=True,
            )
            return FidesAttestation(success=False, error=str(e))
