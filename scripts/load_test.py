#!/usr/bin/env python3
"""
Load testing script for Sardis API.

Usage:
    python scripts/load_test.py --url http://localhost:8000 --duration 60 --concurrency 10
    
Requirements:
    pip install httpx asyncio argparse
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

import httpx


@dataclass
class RequestResult:
    """Result of a single request."""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    success: bool
    error: str | None = None


@dataclass
class LoadTestResults:
    """Aggregated load test results."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_s: float = 0
    requests_per_second: float = 0
    
    # Latency stats (ms)
    latency_min: float = 0
    latency_max: float = 0
    latency_avg: float = 0
    latency_p50: float = 0
    latency_p95: float = 0
    latency_p99: float = 0
    
    # Per-endpoint stats
    endpoint_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Errors
    errors: Dict[str, int] = field(default_factory=dict)


class LoadTester:
    """Load tester for Sardis API."""

    # Test endpoints with weights (higher = more frequent)
    ENDPOINTS = [
        ("GET", "/health", 5),
        ("GET", "/api/v2/health", 5),
        ("GET", "/api/v2/transactions/chains", 3),
        ("GET", "/api/v2/marketplace/categories", 3),
        ("GET", "/api/v2/marketplace/services", 2),
        ("GET", "/api/v2/webhooks/event-types", 2),
        ("GET", "/api/v2/holds", 2),
        ("GET", "/api/v2/ledger/recent?limit=10", 1),
    ]

    def __init__(
        self,
        base_url: str,
        duration_seconds: int = 60,
        concurrency: int = 10,
        api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.duration_seconds = duration_seconds
        self.concurrency = concurrency
        self.api_key = api_key
        self.results: List[RequestResult] = []
        self._running = False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SardisLoadTest/1.0",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _select_endpoint(self) -> tuple[str, str]:
        """Select a random endpoint based on weights."""
        total_weight = sum(w for _, _, w in self.ENDPOINTS)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        for method, path, weight in self.ENDPOINTS:
            cumulative += weight
            if r <= cumulative:
                return method, path
        
        return self.ENDPOINTS[0][0], self.ENDPOINTS[0][1]

    async def _make_request(self, client: httpx.AsyncClient) -> RequestResult:
        """Make a single request."""
        method, path = self._select_endpoint()
        url = f"{self.base_url}{path}"
        
        start_time = time.perf_counter()
        try:
            if method == "GET":
                response = await client.get(url, headers=self._get_headers())
            elif method == "POST":
                response = await client.post(url, headers=self._get_headers(), json={})
            else:
                response = await client.request(method, url, headers=self._get_headers())
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            return RequestResult(
                endpoint=path,
                method=method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=200 <= response.status_code < 400,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return RequestResult(
                endpoint=path,
                method=method,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )

    async def _worker(self, client: httpx.AsyncClient, worker_id: int):
        """Worker that continuously makes requests."""
        while self._running:
            result = await self._make_request(client)
            self.results.append(result)
            
            # Small random delay to avoid thundering herd
            await asyncio.sleep(random.uniform(0.01, 0.05))

    async def run(self) -> LoadTestResults:
        """Run the load test."""
        print(f"\n🚀 Starting load test")
        print(f"   URL: {self.base_url}")
        print(f"   Duration: {self.duration_seconds}s")
        print(f"   Concurrency: {self.concurrency}")
        print()

        self._running = True
        self.results = []
        
        start_time = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Start workers
            workers = [
                asyncio.create_task(self._worker(client, i))
                for i in range(self.concurrency)
            ]
            
            # Progress reporting
            progress_task = asyncio.create_task(self._report_progress())
            
            # Wait for duration
            await asyncio.sleep(self.duration_seconds)
            
            # Stop workers
            self._running = False
            progress_task.cancel()
            
            # Wait for workers to finish
            await asyncio.gather(*workers, return_exceptions=True)
        
        total_duration = time.perf_counter() - start_time
        
        return self._calculate_results(total_duration)

    async def _report_progress(self):
        """Report progress during test."""
        try:
            while self._running:
                await asyncio.sleep(5)
                if self.results:
                    recent = self.results[-100:]
                    success_rate = sum(1 for r in recent if r.success) / len(recent) * 100
                    avg_latency = statistics.mean(r.duration_ms for r in recent)
                    print(f"   Progress: {len(self.results)} requests, {success_rate:.1f}% success, {avg_latency:.1f}ms avg")
        except asyncio.CancelledError:
            pass

    def _calculate_results(self, total_duration: float) -> LoadTestResults:
        """Calculate aggregated results."""
        if not self.results:
            return LoadTestResults()
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        latencies = [r.duration_ms for r in self.results]
        
        # Sort latencies for percentiles
        latencies_sorted = sorted(latencies)
        
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])
        
        # Per-endpoint stats
        endpoint_stats = {}
        for endpoint in set(r.endpoint for r in self.results):
            endpoint_results = [r for r in self.results if r.endpoint == endpoint]
            endpoint_latencies = [r.duration_ms for r in endpoint_results]
            endpoint_stats[endpoint] = {
                "count": len(endpoint_results),
                "success_rate": sum(1 for r in endpoint_results if r.success) / len(endpoint_results) * 100,
                "avg_latency_ms": statistics.mean(endpoint_latencies),
            }
        
        # Error counts
        errors = {}
        for r in failed:
            error_key = r.error or f"HTTP {r.status_code}"
            errors[error_key] = errors.get(error_key, 0) + 1
        
        return LoadTestResults(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            total_duration_s=total_duration,
            requests_per_second=len(self.results) / total_duration,
            latency_min=min(latencies),
            latency_max=max(latencies),
            latency_avg=statistics.mean(latencies),
            latency_p50=percentile(latencies_sorted, 50),
            latency_p95=percentile(latencies_sorted, 95),
            latency_p99=percentile(latencies_sorted, 99),
            endpoint_stats=endpoint_stats,
            errors=errors,
        )


def print_results(results: LoadTestResults):
    """Print load test results."""
    print("\n" + "=" * 60)
    print("📊 LOAD TEST RESULTS")
    print("=" * 60)
    
    print(f"\n📈 Summary")
    print(f"   Total Requests:     {results.total_requests:,}")
    print(f"   Successful:         {results.successful_requests:,} ({results.successful_requests/results.total_requests*100:.1f}%)")
    print(f"   Failed:             {results.failed_requests:,} ({results.failed_requests/results.total_requests*100:.1f}%)")
    print(f"   Duration:           {results.total_duration_s:.1f}s")
    print(f"   Requests/sec:       {results.requests_per_second:.1f}")
    
    print(f"\n⏱️  Latency (ms)")
    print(f"   Min:                {results.latency_min:.1f}")
    print(f"   Max:                {results.latency_max:.1f}")
    print(f"   Avg:                {results.latency_avg:.1f}")
    print(f"   P50:                {results.latency_p50:.1f}")
    print(f"   P95:                {results.latency_p95:.1f}")
    print(f"   P99:                {results.latency_p99:.1f}")
    
    print(f"\n📍 Per-Endpoint Stats")
    for endpoint, stats in sorted(results.endpoint_stats.items()):
        print(f"   {endpoint}")
        print(f"      Requests: {stats['count']:,}, Success: {stats['success_rate']:.1f}%, Avg: {stats['avg_latency_ms']:.1f}ms")
    
    if results.errors:
        print(f"\n❌ Errors")
        for error, count in sorted(results.errors.items(), key=lambda x: -x[1]):
            print(f"   {error}: {count}")
    
    print("\n" + "=" * 60)
    
    # Pass/Fail assessment
    success_rate = results.successful_requests / results.total_requests * 100
    if success_rate >= 99 and results.latency_p95 < 500:
        print("✅ PASSED - Service is healthy")
    elif success_rate >= 95 and results.latency_p95 < 1000:
        print("⚠️  WARNING - Service is degraded")
    else:
        print("❌ FAILED - Service needs attention")
    
    print()


async def main():
    parser = argparse.ArgumentParser(description="Load test Sardis API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", help="Output file for JSON results")
    
    args = parser.parse_args()
    
    tester = LoadTester(
        base_url=args.url,
        duration_seconds=args.duration,
        concurrency=args.concurrency,
        api_key=args.api_key,
    )
    
    results = await tester.run()
    print_results(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "config": {
                    "url": args.url,
                    "duration": args.duration,
                    "concurrency": args.concurrency,
                },
                "results": {
                    "total_requests": results.total_requests,
                    "successful_requests": results.successful_requests,
                    "failed_requests": results.failed_requests,
                    "requests_per_second": results.requests_per_second,
                    "latency_ms": {
                        "min": results.latency_min,
                        "max": results.latency_max,
                        "avg": results.latency_avg,
                        "p50": results.latency_p50,
                        "p95": results.latency_p95,
                        "p99": results.latency_p99,
                    },
                    "endpoint_stats": results.endpoint_stats,
                    "errors": results.errors,
                },
            }, f, indent=2)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
