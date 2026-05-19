"""SDK install metrics aggregator.

Fetches download stats from PyPI and npm public APIs to provide
investor-grade metrics for SDK adoption tracking.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Sardis packages to track
PYPI_PACKAGES = [
    "sardis",
    "sardis-cards",
    "sardis-chain",
    "sardis-ramp",
    "sardis-protocol",
    "sardis-ledger",
    "sardis-compliance",
    "sardis-wallet",
]

NPM_PACKAGES = [
    "@sardis/sdk",
    "@sardis/mcp-server",
    "n8n-nodes-sardis",
]


@dataclass
class PackageStats:
    package: str
    registry: str  # "pypi" | "npm"
    last_day: int = 0
    last_week: int = 0
    last_month: int = 0


@dataclass
class AggregateMetrics:
    total_installs: int = 0
    pypi_total: int = 0
    npm_total: int = 0
    packages: list[PackageStats] = field(default_factory=list)
    growth_rate_weekly: float = 0.0
    fetched_at: str = ""


class SDKMetricsService:
    """Fetch and aggregate SDK install metrics from PyPI and npm."""

    def __init__(self, cache_ttl_seconds: int = 300) -> None:
        self._cache: AggregateMetrics | None = None
        self._cache_time: float = 0
        self._cache_ttl = cache_ttl_seconds
        self._pkg_cache: dict[str, PackageStats] = {}
        self._pkg_cache_time: dict[str, float] = {}

    async def _fetch_pypi_stats(self, package: str) -> PackageStats:
        """Fetch download stats from pypistats.org API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://pypistats.org/api/packages/{package}/recent",
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    return PackageStats(
                        package=package,
                        registry="pypi",
                        last_day=data.get("last_day", 0),
                        last_week=data.get("last_week", 0),
                        last_month=data.get("last_month", 0),
                    )
        except Exception as e:
            logger.warning("Failed to fetch PyPI stats for %s: %s", package, e)

        return PackageStats(package=package, registry="pypi")

    async def _fetch_npm_stats(self, package: str) -> PackageStats:
        """Fetch download stats from npm API."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                # npm provides point/last-day, point/last-week, point/last-month
                resp_month = await client.get(
                    f"https://api.npmjs.org/downloads/point/last-month/{package}"
                )
                resp_week = await client.get(
                    f"https://api.npmjs.org/downloads/point/last-week/{package}"
                )
                resp_day = await client.get(
                    f"https://api.npmjs.org/downloads/point/last-day/{package}"
                )

                last_month = resp_month.json().get("downloads", 0) if resp_month.status_code == 200 else 0
                last_week = resp_week.json().get("downloads", 0) if resp_week.status_code == 200 else 0
                last_day = resp_day.json().get("downloads", 0) if resp_day.status_code == 200 else 0

                return PackageStats(
                    package=package,
                    registry="npm",
                    last_day=last_day,
                    last_week=last_week,
                    last_month=last_month,
                )
        except Exception as e:
            logger.warning("Failed to fetch npm stats for %s: %s", package, e)

        return PackageStats(package=package, registry="npm")

    async def get_package_stats(self, package: str) -> PackageStats:
        """Get stats for a single package with caching."""
        now = time.time()
        cached_time = self._pkg_cache_time.get(package, 0)
        if package in self._pkg_cache and (now - cached_time) < self._cache_ttl:
            return self._pkg_cache[package]

        if package in PYPI_PACKAGES or not package.startswith("@"):
            stats = await self._fetch_pypi_stats(package)
        else:
            stats = await self._fetch_npm_stats(package)

        self._pkg_cache[package] = stats
        self._pkg_cache_time[package] = now
        return stats

    async def get_aggregate_metrics(self) -> AggregateMetrics:
        """Get aggregate metrics across all tracked packages with caching."""
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        all_stats: list[PackageStats] = []

        # Fetch all package stats
        for pkg in PYPI_PACKAGES:
            stats = await self._fetch_pypi_stats(pkg)
            all_stats.append(stats)
            self._pkg_cache[pkg] = stats
            self._pkg_cache_time[pkg] = now

        for pkg in NPM_PACKAGES:
            stats = await self._fetch_npm_stats(pkg)
            all_stats.append(stats)
            self._pkg_cache[pkg] = stats
            self._pkg_cache_time[pkg] = now

        pypi_total = sum(s.last_month for s in all_stats if s.registry == "pypi")
        npm_total = sum(s.last_month for s in all_stats if s.registry == "npm")
        total = pypi_total + npm_total

        # Calculate week-over-week growth rate
        weekly_total = sum(s.last_week for s in all_stats)
        # Approximate previous week from month - current week
        prev_weeks_avg = (sum(s.last_month for s in all_stats) - weekly_total) / 3 if total > 0 else 0
        growth = ((weekly_total - prev_weeks_avg) / prev_weeks_avg * 100) if prev_weeks_avg > 0 else 0.0

        from datetime import UTC, datetime

        result = AggregateMetrics(
            total_installs=total,
            pypi_total=pypi_total,
            npm_total=npm_total,
            packages=all_stats,
            growth_rate_weekly=round(growth, 2),
            fetched_at=datetime.now(UTC).isoformat(),
        )

        self._cache = result
        self._cache_time = now
        return result
