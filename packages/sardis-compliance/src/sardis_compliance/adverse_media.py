"""
Adverse media screening module.

Provides screening capabilities for negative news and adverse media:
- Financial crimes (fraud, money laundering, bribery)
- Regulatory actions and enforcement
- Criminal proceedings
- Reputational risks
- ESG (Environmental, Social, Governance) issues

Integration with external media screening providers:
- Dow Jones Adverse Media
- LexisNexis WorldCompliance
- Refinitiv World-Check
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MediaCategory(str, Enum):
    """Categories of adverse media."""
    FINANCIAL_CRIME = "financial_crime"  # Fraud, money laundering, embezzlement
    CORRUPTION = "corruption"  # Bribery, kickbacks
    TERRORISM = "terrorism"  # Terrorism financing, extremism
    ORGANIZED_CRIME = "organized_crime"  # Organized crime links
    REGULATORY_ACTION = "regulatory_action"  # Fines, sanctions, enforcement
    CRIMINAL_PROCEEDINGS = "criminal_proceedings"  # Arrests, convictions
    CIVIL_LITIGATION = "civil_litigation"  # Lawsuits, settlements
    REPUTATIONAL = "reputational"  # General negative news
    ESG = "esg"  # Environmental, social, governance issues
    SANCTIONS_EVASION = "sanctions_evasion"  # Attempts to evade sanctions
    OTHER = "other"


class MediaSeverity(str, Enum):
    """Severity level of adverse media."""
    CRITICAL = "critical"  # Confirmed criminal activity, major fraud
    HIGH = "high"  # Serious allegations, regulatory actions
    MEDIUM = "medium"  # Investigations, civil matters
    LOW = "low"  # Minor issues, old news
    INFORMATIONAL = "informational"  # FYI only


@dataclass
class MediaArticle:
    """A single media article or news item."""
    article_id: str
    title: str
    source: str
    published_date: datetime
    category: MediaCategory
    severity: MediaSeverity
    summary: str
    url: Optional[str] = None
    is_verified: bool = False  # Whether the information has been verified
    confidence_score: float = 0.0  # 0.0 to 1.0
    entities_mentioned: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_days(self) -> int:
        """Calculate age of article in days."""
        delta = datetime.now(timezone.utc) - self.published_date
        return delta.days

    @property
    def is_recent(self) -> bool:
        """Check if article is recent (within 2 years)."""
        return self.age_days <= 730


@dataclass
class AdverseMediaResult:
    """Result of adverse media screening."""
    has_adverse_media: bool
    subject_id: str
    subject_name: str
    screened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    articles: List[MediaArticle] = field(default_factory=list)
    highest_severity: MediaSeverity = MediaSeverity.INFORMATIONAL
    categories_found: List[MediaCategory] = field(default_factory=list)
    provider: str = "mock"
    requires_review: bool = False
    risk_score: float = 0.0  # 0-100
    reason: Optional[str] = None

    @property
    def article_count(self) -> int:
        """Number of articles found."""
        return len(self.articles)

    @property
    def recent_articles(self) -> List[MediaArticle]:
        """Get only recent articles."""
        return [a for a in self.articles if a.is_recent]

    @property
    def critical_articles(self) -> List[MediaArticle]:
        """Get only critical/high severity articles."""
        return [
            a for a in self.articles
            if a.severity in (MediaSeverity.CRITICAL, MediaSeverity.HIGH)
        ]


@dataclass
class AdverseMediaRequest:
    """Request for adverse media screening."""
    subject_id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    organization: Optional[str] = None
    include_historical: bool = True  # Include articles older than 2 years
    categories: List[MediaCategory] = field(default_factory=lambda: list(MediaCategory))
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdverseMediaProvider(ABC):
    """Abstract interface for adverse media screening providers."""

    @abstractmethod
    async def screen_individual(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen an individual for adverse media."""
        pass

    @abstractmethod
    async def screen_organization(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen an organization for adverse media."""
        pass

    @abstractmethod
    async def get_article_details(
        self,
        article_id: str,
    ) -> Optional[MediaArticle]:
        """Get detailed information about a specific article."""
        pass


class DowJonesMediaProvider(AdverseMediaProvider):
    """
    Dow Jones Adverse Media provider.

    Integrates with Dow Jones Risk & Compliance API for adverse media screening.
    API Reference: https://developer.dowjones.com/
    """

    BASE_URL = "https://api.dowjones.com"

    def __init__(
        self,
        api_key: str,
        account_id: str,
        include_historical: bool = True,
    ):
        """
        Initialize Dow Jones provider.

        Args:
            api_key: Dow Jones API key
            account_id: Dow Jones account ID
            include_historical: Include historical articles
        """
        self._api_key = api_key
        self._account_id = account_id
        self._include_historical = include_historical
        self._http_client = None

    async def _get_client(self):
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "X-Account-Id": self._account_id,
                },
                timeout=60,  # Media searches can be slow
            )
        return self._http_client

    async def screen_individual(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen an individual via Dow Jones."""
        client = await self._get_client()

        # Build search payload
        payload = {
            "query": {
                "name": request.name,
                "type": "person",
            },
            "filter": {
                "categories": [c.value for c in request.categories],
                "include_historical": request.include_historical,
            },
        }

        if request.aliases:
            payload["query"]["aliases"] = request.aliases
        if request.country:
            payload["query"]["country"] = request.country

        try:
            response = await client.post("/adverse-media/search", json=payload)
            response.raise_for_status()
            result = response.json()

            return self._parse_result(request, result)

        except Exception as e:
            logger.error(f"Dow Jones adverse media screening failed: {e}")
            # Return result indicating screening failed
            return AdverseMediaResult(
                has_adverse_media=False,
                subject_id=request.subject_id,
                subject_name=request.name,
                provider="dowjones",
                requires_review=True,
                reason=f"Screening failed - manual review required: {str(e)}",
            )

    async def screen_organization(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen an organization via Dow Jones."""
        client = await self._get_client()

        payload = {
            "query": {
                "name": request.name,
                "type": "organization",
            },
            "filter": {
                "categories": [c.value for c in request.categories],
                "include_historical": request.include_historical,
            },
        }

        try:
            response = await client.post("/adverse-media/search", json=payload)
            response.raise_for_status()
            result = response.json()

            return self._parse_result(request, result)

        except Exception as e:
            logger.error(f"Dow Jones org screening failed: {e}")
            return AdverseMediaResult(
                has_adverse_media=False,
                subject_id=request.subject_id,
                subject_name=request.name,
                provider="dowjones",
                requires_review=True,
                reason=f"Screening failed - manual review required: {str(e)}",
            )

    async def get_article_details(
        self,
        article_id: str,
    ) -> Optional[MediaArticle]:
        """Get detailed article information."""
        client = await self._get_client()

        try:
            response = await client.get(f"/adverse-media/articles/{article_id}")
            response.raise_for_status()
            data = response.json()

            return self._parse_article(data)

        except Exception as e:
            logger.error(f"Failed to get article details: {e}")
            return None

    def _parse_result(
        self,
        request: AdverseMediaRequest,
        data: Dict[str, Any],
    ) -> AdverseMediaResult:
        """Parse Dow Jones response into AdverseMediaResult."""
        articles = []
        categories_found = set()
        highest_severity = MediaSeverity.INFORMATIONAL

        for hit in data.get("hits", []):
            article = self._parse_article(hit)
            articles.append(article)
            categories_found.add(article.category)

            if self._severity_rank(article.severity) > self._severity_rank(highest_severity):
                highest_severity = article.severity

        # Calculate risk score
        risk_score = self._calculate_risk_score(articles)

        return AdverseMediaResult(
            has_adverse_media=len(articles) > 0,
            subject_id=request.subject_id,
            subject_name=request.name,
            articles=articles,
            highest_severity=highest_severity,
            categories_found=list(categories_found),
            provider="dowjones",
            requires_review=highest_severity in (MediaSeverity.CRITICAL, MediaSeverity.HIGH),
            risk_score=risk_score,
            reason="Adverse media found" if articles else None,
        )

    def _parse_article(self, data: Dict[str, Any]) -> MediaArticle:
        """Parse article data into MediaArticle."""
        category_str = data.get("category", "other")
        try:
            category = MediaCategory(category_str)
        except ValueError:
            category = MediaCategory.OTHER

        severity_str = data.get("severity", "informational")
        try:
            severity = MediaSeverity(severity_str)
        except ValueError:
            severity = MediaSeverity.INFORMATIONAL

        published = data.get("published_date")
        if isinstance(published, str):
            published = datetime.fromisoformat(published.replace("Z", "+00:00"))
        else:
            published = datetime.now(timezone.utc)

        return MediaArticle(
            article_id=data.get("id", ""),
            title=data.get("title", ""),
            source=data.get("source", ""),
            published_date=published,
            category=category,
            severity=severity,
            summary=data.get("summary", ""),
            url=data.get("url"),
            is_verified=data.get("verified", False),
            confidence_score=data.get("confidence", 0.0),
            entities_mentioned=data.get("entities", []),
        )

    def _severity_rank(self, severity: MediaSeverity) -> int:
        """Get numeric rank for severity comparison."""
        ranks = {
            MediaSeverity.INFORMATIONAL: 0,
            MediaSeverity.LOW: 1,
            MediaSeverity.MEDIUM: 2,
            MediaSeverity.HIGH: 3,
            MediaSeverity.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    def _calculate_risk_score(self, articles: List[MediaArticle]) -> float:
        """Calculate overall risk score from articles."""
        if not articles:
            return 0.0

        score = 0.0
        severity_scores = {
            MediaSeverity.CRITICAL: 40,
            MediaSeverity.HIGH: 25,
            MediaSeverity.MEDIUM: 15,
            MediaSeverity.LOW: 5,
            MediaSeverity.INFORMATIONAL: 2,
        }

        for article in articles[:10]:  # Cap at 10 articles
            base_score = severity_scores.get(article.severity, 5)

            # Recency multiplier
            if article.age_days <= 90:
                multiplier = 1.5
            elif article.age_days <= 365:
                multiplier = 1.2
            elif article.age_days <= 730:
                multiplier = 1.0
            else:
                multiplier = 0.7

            # Verification bonus
            if article.is_verified:
                multiplier *= 1.2

            score += base_score * multiplier

        return min(100.0, score)

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockAdverseMediaProvider(AdverseMediaProvider):
    """
    Mock adverse media provider for development and testing.
    """

    # Test data - known adverse media subjects
    KNOWN_SUBJECTS = {
        "bad actor": [
            MediaArticle(
                article_id="art_001",
                title="CEO Charged with Fraud",
                source="Financial Times",
                published_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                category=MediaCategory.FINANCIAL_CRIME,
                severity=MediaSeverity.HIGH,
                summary="Company executive charged with securities fraud",
                is_verified=True,
                confidence_score=0.95,
            ),
        ],
        "corrupt official": [
            MediaArticle(
                article_id="art_002",
                title="Government Official Accepts Bribes",
                source="Reuters",
                published_date=datetime(2023, 6, 1, tzinfo=timezone.utc),
                category=MediaCategory.CORRUPTION,
                severity=MediaSeverity.CRITICAL,
                summary="Official convicted of accepting bribes",
                is_verified=True,
                confidence_score=0.98,
            ),
        ],
    }

    def __init__(self):
        self._custom_results: Dict[str, AdverseMediaResult] = {}

    async def screen_individual(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen with mock logic."""
        name_lower = request.name.lower()

        # Check custom results
        if name_lower in self._custom_results:
            return self._custom_results[name_lower]

        # Check known subjects
        for key, articles in self.KNOWN_SUBJECTS.items():
            if key in name_lower:
                highest_severity = max(
                    articles, key=lambda a: self._severity_rank(a.severity)
                ).severity
                categories = list(set(a.category for a in articles))

                return AdverseMediaResult(
                    has_adverse_media=True,
                    subject_id=request.subject_id,
                    subject_name=request.name,
                    articles=articles,
                    highest_severity=highest_severity,
                    categories_found=categories,
                    provider="mock",
                    requires_review=True,
                    risk_score=75.0,
                    reason="Mock adverse media found",
                )

        return AdverseMediaResult(
            has_adverse_media=False,
            subject_id=request.subject_id,
            subject_name=request.name,
            provider="mock",
        )

    async def screen_organization(
        self,
        request: AdverseMediaRequest,
    ) -> AdverseMediaResult:
        """Screen organization with mock logic."""
        # Same logic as individual for mock
        return await self.screen_individual(request)

    async def get_article_details(
        self,
        article_id: str,
    ) -> Optional[MediaArticle]:
        """Get mock article details."""
        for articles in self.KNOWN_SUBJECTS.values():
            for article in articles:
                if article.article_id == article_id:
                    return article
        return None

    def _severity_rank(self, severity: MediaSeverity) -> int:
        """Get numeric rank for severity."""
        ranks = {
            MediaSeverity.INFORMATIONAL: 0,
            MediaSeverity.LOW: 1,
            MediaSeverity.MEDIUM: 2,
            MediaSeverity.HIGH: 3,
            MediaSeverity.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    def set_result(self, name: str, result: AdverseMediaResult) -> None:
        """Set custom result for testing."""
        self._custom_results[name.lower()] = result


class AdverseMediaService:
    """
    High-level adverse media screening service.

    Features:
    - Individual and organization screening
    - Result caching
    - Category-based filtering
    - Risk assessment integration
    """

    def __init__(
        self,
        provider: Optional[AdverseMediaProvider] = None,
        cache_ttl_seconds: int = 43200,  # 12 hours
        min_severity_for_review: MediaSeverity = MediaSeverity.MEDIUM,
    ):
        """
        Initialize adverse media service.

        Args:
            provider: Media screening provider
            cache_ttl_seconds: Cache TTL for screening results
            min_severity_for_review: Minimum severity that triggers review
        """
        self._provider = provider or MockAdverseMediaProvider()
        self._cache_ttl = cache_ttl_seconds
        self._min_severity = min_severity_for_review
        self._cache: Dict[str, tuple[AdverseMediaResult, datetime]] = {}

    async def screen_individual(
        self,
        subject_id: str,
        name: str,
        aliases: Optional[List[str]] = None,
        country: Optional[str] = None,
        categories: Optional[List[MediaCategory]] = None,
        force_refresh: bool = False,
    ) -> AdverseMediaResult:
        """
        Screen an individual for adverse media.

        Uses cache if available and not expired.
        """
        cache_key = f"individual:{subject_id}:{name.lower()}"

        # Check cache
        if not force_refresh and cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age < self._cache_ttl:
                logger.debug(f"Adverse media cache hit for {subject_id}")
                return result

        # Screen
        request = AdverseMediaRequest(
            subject_id=subject_id,
            name=name,
            aliases=aliases or [],
            country=country,
            categories=categories or list(MediaCategory),
        )

        result = await self._provider.screen_individual(request)

        # Set requires_review based on severity threshold
        if result.has_adverse_media:
            severity_rank = self._severity_rank(result.highest_severity)
            min_rank = self._severity_rank(self._min_severity)
            result.requires_review = severity_rank >= min_rank

        # Cache result
        self._cache[cache_key] = (result, datetime.now(timezone.utc))

        logger.info(
            f"Adverse media screening completed: subject={subject_id}, "
            f"has_media={result.has_adverse_media}, articles={result.article_count}"
        )

        return result

    async def screen_organization(
        self,
        subject_id: str,
        name: str,
        country: Optional[str] = None,
        categories: Optional[List[MediaCategory]] = None,
        force_refresh: bool = False,
    ) -> AdverseMediaResult:
        """
        Screen an organization for adverse media.
        """
        cache_key = f"org:{subject_id}:{name.lower()}"

        if not force_refresh and cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age < self._cache_ttl:
                return result

        request = AdverseMediaRequest(
            subject_id=subject_id,
            name=name,
            country=country,
            categories=categories or list(MediaCategory),
        )

        result = await self._provider.screen_organization(request)

        # Set requires_review
        if result.has_adverse_media:
            severity_rank = self._severity_rank(result.highest_severity)
            min_rank = self._severity_rank(self._min_severity)
            result.requires_review = severity_rank >= min_rank

        self._cache[cache_key] = (result, datetime.now(timezone.utc))

        logger.info(
            f"Org adverse media screening completed: subject={subject_id}, "
            f"has_media={result.has_adverse_media}"
        )

        return result

    async def has_critical_media(
        self,
        subject_id: str,
        name: str,
    ) -> bool:
        """Quick check if subject has critical/high severity adverse media."""
        result = await self.screen_individual(subject_id, name)
        return result.highest_severity in (MediaSeverity.CRITICAL, MediaSeverity.HIGH)

    async def get_article(self, article_id: str) -> Optional[MediaArticle]:
        """Get detailed article information."""
        return await self._provider.get_article_details(article_id)

    def _severity_rank(self, severity: MediaSeverity) -> int:
        """Get numeric rank for severity."""
        ranks = {
            MediaSeverity.INFORMATIONAL: 0,
            MediaSeverity.LOW: 1,
            MediaSeverity.MEDIUM: 2,
            MediaSeverity.HIGH: 3,
            MediaSeverity.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    def clear_cache(self) -> None:
        """Clear the screening cache."""
        self._cache.clear()


def create_adverse_media_service(
    api_key: Optional[str] = None,
    account_id: Optional[str] = None,
    provider_name: str = "dowjones",
) -> AdverseMediaService:
    """
    Factory function to create adverse media service.

    Uses MockAdverseMediaProvider if no API key is provided.

    Args:
        api_key: Provider API key
        account_id: Provider account ID
        provider_name: Provider name ('dowjones' supported)

    Returns:
        Configured AdverseMediaService instance
    """
    if api_key and account_id:
        if provider_name == "dowjones":
            provider = DowJonesMediaProvider(
                api_key=api_key,
                account_id=account_id,
            )
        else:
            logger.warning(f"Unknown media provider: {provider_name}, using mock")
            provider = MockAdverseMediaProvider()
    else:
        logger.warning("No adverse media API credentials provided, using mock provider")
        provider = MockAdverseMediaProvider()

    return AdverseMediaService(provider=provider)
