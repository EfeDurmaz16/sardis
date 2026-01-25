"""
PEP (Politically Exposed Persons) screening module.

Provides screening capabilities for:
- Heads of state, government officials
- Senior politicians and party officials
- Senior judicial or military figures
- Senior executives of state-owned corporations
- Close family members and associates (RCA - Related Close Associates)

Integration with external PEP databases:
- Dow Jones Risk & Compliance
- World-Check (Refinitiv)
- ComplyAdvantage
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PEPCategory(str, Enum):
    """PEP classification categories."""
    FOREIGN_PEP = "foreign_pep"  # Foreign government officials
    DOMESTIC_PEP = "domestic_pep"  # Domestic government officials
    INTERNATIONAL_ORG = "international_org"  # Officials of international organizations
    RCA = "rca"  # Relatives and Close Associates
    SOE = "soe"  # State-Owned Enterprise executives
    NOT_PEP = "not_pep"


class PEPRiskLevel(str, Enum):
    """Risk level for PEP matches."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PEPStatus(str, Enum):
    """Current status of PEP position."""
    CURRENT = "current"
    FORMER = "former"
    UNKNOWN = "unknown"


@dataclass
class PEPMatch:
    """A single PEP match result."""
    match_id: str
    name: str
    category: PEPCategory
    status: PEPStatus
    position: str
    country: str
    confidence_score: float  # 0.0 to 1.0
    risk_level: PEPRiskLevel
    source: str
    last_updated: Optional[datetime] = None
    related_entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_risk(self) -> bool:
        """Check if this is a high-risk PEP match."""
        return self.risk_level in (PEPRiskLevel.HIGH, PEPRiskLevel.VERY_HIGH)


@dataclass
class PEPScreeningResult:
    """Result of PEP screening."""
    is_pep: bool
    subject_id: str
    subject_name: str
    screened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    matches: List[PEPMatch] = field(default_factory=list)
    highest_risk: PEPRiskLevel = PEPRiskLevel.LOW
    provider: str = "mock"
    requires_enhanced_due_diligence: bool = False
    reason: Optional[str] = None

    @property
    def match_count(self) -> int:
        """Number of matches found."""
        return len(self.matches)

    @property
    def has_current_pep(self) -> bool:
        """Check if any match is a current PEP."""
        return any(m.status == PEPStatus.CURRENT for m in self.matches)

    @property
    def has_foreign_pep(self) -> bool:
        """Check if any match is a foreign PEP."""
        return any(m.category == PEPCategory.FOREIGN_PEP for m in self.matches)


@dataclass
class PEPScreeningRequest:
    """Request for PEP screening."""
    subject_id: str  # Internal reference ID
    name: str
    date_of_birth: Optional[str] = None  # YYYY-MM-DD format
    country: Optional[str] = None  # ISO 3166-1 alpha-2
    nationality: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PEPProvider(ABC):
    """Abstract interface for PEP screening providers."""

    @abstractmethod
    async def screen_individual(
        self,
        request: PEPScreeningRequest,
    ) -> PEPScreeningResult:
        """Screen an individual for PEP status."""
        pass

    @abstractmethod
    async def screen_batch(
        self,
        requests: List[PEPScreeningRequest],
    ) -> List[PEPScreeningResult]:
        """Screen multiple individuals for PEP status."""
        pass

    @abstractmethod
    async def get_match_details(
        self,
        match_id: str,
    ) -> Optional[PEPMatch]:
        """Get detailed information about a specific match."""
        pass


class ComplyAdvantagePEPProvider(PEPProvider):
    """
    ComplyAdvantage PEP screening provider.

    API Reference: https://docs.complyadvantage.com/
    """

    BASE_URL = "https://api.complyadvantage.com"

    def __init__(
        self,
        api_key: str,
        fuzziness: float = 0.6,  # Name matching threshold
    ):
        """
        Initialize ComplyAdvantage provider.

        Args:
            api_key: ComplyAdvantage API key
            fuzziness: Name matching fuzziness (0.0 to 1.0)
        """
        self._api_key = api_key
        self._fuzziness = fuzziness
        self._http_client = None

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        return self._http_client

    async def screen_individual(
        self,
        request: PEPScreeningRequest,
    ) -> PEPScreeningResult:
        """Screen an individual via ComplyAdvantage."""
        client = await self._get_client()

        # Build search payload
        payload = {
            "search_term": request.name,
            "fuzziness": self._fuzziness,
            "filters": {
                "types": ["pep"],
            },
            "client_ref": request.subject_id,
        }

        if request.date_of_birth:
            payload["filters"]["birth_year"] = int(request.date_of_birth[:4])

        if request.country:
            payload["filters"]["countries"] = [request.country]

        try:
            response = await client.post("/searches", json=payload)
            response.raise_for_status()
            result = response.json()

            # Parse response
            hits = result.get("content", {}).get("data", {}).get("hits", [])
            matches = []
            highest_risk = PEPRiskLevel.LOW

            for hit in hits:
                doc = hit.get("doc", {})
                match = self._parse_match(doc)
                matches.append(match)

                if match.risk_level.value > highest_risk.value:
                    highest_risk = match.risk_level

            is_pep = len(matches) > 0
            requires_edd = any(m.is_high_risk or m.has_current_pep for m in matches) if matches else False

            return PEPScreeningResult(
                is_pep=is_pep,
                subject_id=request.subject_id,
                subject_name=request.name,
                matches=matches,
                highest_risk=highest_risk,
                provider="complyadvantage",
                requires_enhanced_due_diligence=requires_edd,
                reason="PEP match found" if is_pep else None,
            )

        except Exception as e:
            logger.error(f"ComplyAdvantage PEP screening failed: {e}")
            # Fail closed - treat as high risk on error
            return PEPScreeningResult(
                is_pep=False,
                subject_id=request.subject_id,
                subject_name=request.name,
                highest_risk=PEPRiskLevel.HIGH,
                provider="complyadvantage",
                requires_enhanced_due_diligence=True,
                reason=f"Screening failed - manual review required: {str(e)}",
            )

    async def screen_batch(
        self,
        requests: List[PEPScreeningRequest],
    ) -> List[PEPScreeningResult]:
        """Screen multiple individuals."""
        results = []
        for request in requests:
            result = await self.screen_individual(request)
            results.append(result)
        return results

    async def get_match_details(
        self,
        match_id: str,
    ) -> Optional[PEPMatch]:
        """Get detailed match information."""
        client = await self._get_client()

        try:
            response = await client.get(f"/searches/{match_id}")
            response.raise_for_status()
            result = response.json()

            doc = result.get("content", {}).get("data", {})
            return self._parse_match(doc) if doc else None

        except Exception as e:
            logger.error(f"Failed to get match details: {e}")
            return None

    def _parse_match(self, doc: Dict[str, Any]) -> PEPMatch:
        """Parse ComplyAdvantage match document."""
        entity_type = doc.get("entity_type", "unknown")

        # Determine PEP category
        types = doc.get("types", [])
        category = PEPCategory.NOT_PEP
        if "pep" in types:
            if doc.get("is_foreign"):
                category = PEPCategory.FOREIGN_PEP
            elif "rca" in types:
                category = PEPCategory.RCA
            else:
                category = PEPCategory.DOMESTIC_PEP

        # Determine risk level based on position and status
        risk_level = PEPRiskLevel.MEDIUM
        if category == PEPCategory.FOREIGN_PEP:
            risk_level = PEPRiskLevel.HIGH

        is_active = doc.get("pep_status", "").lower() == "active"
        if is_active and category in (PEPCategory.FOREIGN_PEP, PEPCategory.DOMESTIC_PEP):
            risk_level = PEPRiskLevel.VERY_HIGH

        return PEPMatch(
            match_id=doc.get("id", ""),
            name=doc.get("name", ""),
            category=category,
            status=PEPStatus.CURRENT if is_active else PEPStatus.FORMER,
            position=doc.get("positions", [{}])[0].get("name", "Unknown"),
            country=doc.get("countries", [""])[0],
            confidence_score=doc.get("match_score", 0) / 100.0,
            risk_level=risk_level,
            source="complyadvantage",
            related_entities=doc.get("associates", []),
            metadata={
                "aka": doc.get("aka", []),
                "sources": doc.get("sources", []),
            },
        )

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockPEPProvider(PEPProvider):
    """
    Mock PEP provider for development and testing.
    """

    # Test data - known PEPs for testing
    KNOWN_PEPS = {
        "john smith": PEPMatch(
            match_id="pep_001",
            name="John Smith",
            category=PEPCategory.DOMESTIC_PEP,
            status=PEPStatus.CURRENT,
            position="Senator",
            country="US",
            confidence_score=0.95,
            risk_level=PEPRiskLevel.HIGH,
            source="mock",
        ),
        "jane doe": PEPMatch(
            match_id="pep_002",
            name="Jane Doe",
            category=PEPCategory.FOREIGN_PEP,
            status=PEPStatus.FORMER,
            position="Former Minister of Finance",
            country="GB",
            confidence_score=0.88,
            risk_level=PEPRiskLevel.MEDIUM,
            source="mock",
        ),
    }

    def __init__(self):
        self._custom_results: Dict[str, PEPScreeningResult] = {}

    async def screen_individual(
        self,
        request: PEPScreeningRequest,
    ) -> PEPScreeningResult:
        """Screen an individual with mock logic."""
        name_lower = request.name.lower()

        # Check custom results
        if name_lower in self._custom_results:
            return self._custom_results[name_lower]

        # Check known PEPs
        matches = []
        for key, match in self.KNOWN_PEPS.items():
            if key in name_lower or name_lower in key:
                matches.append(match)

        if matches:
            highest_risk = max(matches, key=lambda m: m.risk_level.value).risk_level
            return PEPScreeningResult(
                is_pep=True,
                subject_id=request.subject_id,
                subject_name=request.name,
                matches=matches,
                highest_risk=highest_risk,
                provider="mock",
                requires_enhanced_due_diligence=highest_risk in (PEPRiskLevel.HIGH, PEPRiskLevel.VERY_HIGH),
                reason="Mock PEP match found",
            )

        return PEPScreeningResult(
            is_pep=False,
            subject_id=request.subject_id,
            subject_name=request.name,
            provider="mock",
        )

    async def screen_batch(
        self,
        requests: List[PEPScreeningRequest],
    ) -> List[PEPScreeningResult]:
        """Screen multiple individuals."""
        results = []
        for request in requests:
            result = await self.screen_individual(request)
            results.append(result)
        return results

    async def get_match_details(
        self,
        match_id: str,
    ) -> Optional[PEPMatch]:
        """Get match details from mock data."""
        for match in self.KNOWN_PEPS.values():
            if match.match_id == match_id:
                return match
        return None

    def set_result(self, name: str, result: PEPScreeningResult) -> None:
        """Set custom result for testing."""
        self._custom_results[name.lower()] = result


class PEPService:
    """
    High-level PEP screening service.

    Features:
    - Individual and batch screening
    - Result caching
    - Risk-based decision making
    - Audit logging
    """

    def __init__(
        self,
        provider: Optional[PEPProvider] = None,
        cache_ttl_seconds: int = 86400,  # 24 hours
        require_edd_for_pep: bool = True,
    ):
        """
        Initialize PEP service.

        Args:
            provider: PEP screening provider
            cache_ttl_seconds: Cache TTL for screening results
            require_edd_for_pep: Require Enhanced Due Diligence for all PEPs
        """
        self._provider = provider or MockPEPProvider()
        self._cache_ttl = cache_ttl_seconds
        self._require_edd_for_pep = require_edd_for_pep
        self._cache: Dict[str, tuple[PEPScreeningResult, datetime]] = {}

    async def screen_individual(
        self,
        subject_id: str,
        name: str,
        date_of_birth: Optional[str] = None,
        country: Optional[str] = None,
        force_refresh: bool = False,
    ) -> PEPScreeningResult:
        """
        Screen an individual for PEP status.

        Uses cache if available and not expired.
        """
        cache_key = f"{subject_id}:{name.lower()}"

        # Check cache
        if not force_refresh and cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age < self._cache_ttl:
                logger.debug(f"PEP screening cache hit for {subject_id}")
                return result

        # Screen
        request = PEPScreeningRequest(
            subject_id=subject_id,
            name=name,
            date_of_birth=date_of_birth,
            country=country,
        )

        result = await self._provider.screen_individual(request)

        # Apply EDD requirement
        if self._require_edd_for_pep and result.is_pep:
            result.requires_enhanced_due_diligence = True

        # Cache result
        self._cache[cache_key] = (result, datetime.now(timezone.utc))

        logger.info(
            f"PEP screening completed: subject={subject_id}, "
            f"is_pep={result.is_pep}, matches={result.match_count}"
        )

        return result

    async def screen_batch(
        self,
        subjects: List[Dict[str, Any]],
    ) -> List[PEPScreeningResult]:
        """
        Screen multiple individuals for PEP status.

        Args:
            subjects: List of dicts with 'subject_id', 'name', and optional 'date_of_birth', 'country'

        Returns:
            List of screening results in same order as input
        """
        requests = []
        for subject in subjects:
            requests.append(PEPScreeningRequest(
                subject_id=subject["subject_id"],
                name=subject["name"],
                date_of_birth=subject.get("date_of_birth"),
                country=subject.get("country"),
            ))

        results = await self._provider.screen_batch(requests)

        # Apply EDD requirement and cache
        for result in results:
            if self._require_edd_for_pep and result.is_pep:
                result.requires_enhanced_due_diligence = True

            cache_key = f"{result.subject_id}:{result.subject_name.lower()}"
            self._cache[cache_key] = (result, datetime.now(timezone.utc))

        logger.info(f"Batch PEP screening completed: {len(results)} subjects")

        return results

    async def is_pep(
        self,
        subject_id: str,
        name: str,
    ) -> bool:
        """Quick check if someone is a PEP."""
        result = await self.screen_individual(subject_id, name)
        return result.is_pep

    async def requires_edd(
        self,
        subject_id: str,
        name: str,
    ) -> bool:
        """Check if Enhanced Due Diligence is required."""
        result = await self.screen_individual(subject_id, name)
        return result.requires_enhanced_due_diligence

    def clear_cache(self) -> None:
        """Clear the screening cache."""
        self._cache.clear()


def create_pep_service(
    api_key: Optional[str] = None,
    provider_name: str = "complyadvantage",
) -> PEPService:
    """
    Factory function to create PEP service.

    Uses MockPEPProvider if no API key is provided.

    Args:
        api_key: Provider API key
        provider_name: Provider name ('complyadvantage' supported)

    Returns:
        Configured PEPService instance
    """
    if api_key:
        if provider_name == "complyadvantage":
            provider = ComplyAdvantagePEPProvider(api_key=api_key)
        else:
            logger.warning(f"Unknown PEP provider: {provider_name}, using mock")
            provider = MockPEPProvider()
    else:
        logger.warning("No PEP API key provided, using mock provider")
        provider = MockPEPProvider()

    return PEPService(provider=provider)
