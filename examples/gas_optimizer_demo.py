"""
Gas Optimizer Demo - Multi-chain gas estimation and route finding.

This example demonstrates how to use the GasOptimizer to:
1. Estimate gas costs for transactions on different chains
2. Find the cheapest route for a transfer across multiple chains
3. Monitor gas prices across all supported chains
"""
import asyncio
from decimal import Decimal

from sardis_chain.gas_optimizer import get_gas_optimizer


async def demo_gas_estimation():
    """Demo: Estimate gas for individual chains."""
    print("=" * 60)
    print("Gas Estimation Demo")
    print("=" * 60)

    optimizer = get_gas_optimizer(cache_ttl_seconds=30)

    # Test different chains
    chains = ["ethereum", "base", "polygon", "arbitrum", "optimism"]

    for chain in chains:
        estimate = await optimizer.estimate_gas(
            chain=chain,
            token="USDC",
            amount=Decimal("100"),
            destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        )

        print(f"\n{chain.upper()}:")
        print(f"  Gas Price: {estimate.gas_price_gwei:.6f} gwei")
        print(f"  Gas Units: {estimate.estimated_gas_units:,}")
        print(f"  Cost (USD): ${estimate.estimated_cost_usd:.4f}")
        print(f"  Time: ~{estimate.estimated_time_seconds}s")
        print(f"  Congestion: {estimate.congestion_level}")


async def demo_route_finding():
    """Demo: Find cheapest route across chains."""
    print("\n" + "=" * 60)
    print("Route Finding Demo")
    print("=" * 60)

    optimizer = get_gas_optimizer()

    # Find cheapest route for a USDC transfer
    routes = await optimizer.find_cheapest_route(
        token="USDC",
        amount=Decimal("500"),
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        source_chains=["ethereum", "base", "polygon", "arbitrum", "optimism"],
    )

    print(f"\nFound {len(routes)} routes, ranked by cost:\n")

    for i, route in enumerate(routes, 1):
        recommended = "⭐ RECOMMENDED" if route.recommended else ""
        print(f"{i}. {route.source_chain.upper()} {recommended}")
        print(f"   Gas Cost: ${route.estimated_gas_cost_usd:.6f}")
        print(f"   Total Cost: ${route.estimated_total_cost_usd:.6f}")
        print(f"   Time: ~{route.estimated_time_seconds}s")
        print()


async def demo_gas_price_monitoring():
    """Demo: Monitor gas prices across all chains."""
    print("=" * 60)
    print("Gas Price Monitoring Demo")
    print("=" * 60)

    optimizer = get_gas_optimizer()

    prices = await optimizer.get_gas_prices()

    print(f"\nCurrent gas prices across {len(prices)} chains:\n")

    # Sort by gas cost
    sorted_chains = sorted(
        prices.items(),
        key=lambda x: x[1].estimated_cost_usd
    )

    for chain, estimate in sorted_chains:
        print(f"{chain:20} {estimate.gas_price_gwei:10.6f} gwei  "
              f"${estimate.estimated_cost_usd:8.6f}  "
              f"({estimate.congestion_level})")


async def demo_cache_behavior():
    """Demo: Show caching behavior."""
    print("\n" + "=" * 60)
    print("Cache Behavior Demo")
    print("=" * 60)

    optimizer = get_gas_optimizer(cache_ttl_seconds=5)

    print("\nFetching gas price for Base (first call)...")
    price1 = await optimizer._get_gas_price("base")
    print(f"Price: {price1} gwei")

    print("\nFetching again immediately (should use cache)...")
    price2 = await optimizer._get_gas_price("base")
    print(f"Price: {price2} gwei")
    print(f"Same as before: {price1 == price2}")

    print("\nWaiting 6 seconds for cache to expire...")
    await asyncio.sleep(6)

    print("Fetching again (cache expired, will fetch fresh)...")
    price3 = await optimizer._get_gas_price("base")
    print(f"Price: {price3} gwei")
    print(f"May differ due to market conditions")


async def main():
    """Run all demos."""
    await demo_gas_estimation()
    await demo_route_finding()
    await demo_gas_price_monitoring()
    await demo_cache_behavior()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
