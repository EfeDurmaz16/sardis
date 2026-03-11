"""Solana devnet smoke test.

Verifies:
1. RPC connectivity to Solana devnet
2. Blockhash retrieval works
3. Rent exemption query works
4. Uses sardis_chain.solana.SolanaClient

Usage:
    uv run --no-project python scripts/test_solana_devnet.py
"""
from __future__ import annotations

import asyncio
import sys

# Add package paths for standalone execution
sys.path.insert(0, "packages/sardis-chain/src")
sys.path.insert(0, "packages/sardis-core/src")
sys.path.insert(0, "packages/sardis-ledger/src")

from sardis_chain.solana.client import SolanaClient, SolanaConfig


DEVNET_RPC = "https://api.devnet.solana.com"


async def main() -> int:
    print("=== Solana Devnet Smoke Test ===\n")
    ok = 0
    total = 3

    config = SolanaConfig(rpc_url=DEVNET_RPC)
    client = SolanaClient(config)

    try:
        # 1. Get latest blockhash
        try:
            blockhash = await client.get_latest_blockhash()
            print(f"[OK] Latest blockhash: {blockhash[:16]}...")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Blockhash: {e}")

        # 2. Check balance of system program (basic connectivity)
        try:
            balance = await client.get_balance("11111111111111111111111111111111")
            print(f"[OK] System program balance: {balance} lamports")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Balance check: {e}")

        # 3. Rent exemption check (token account size = 165 bytes)
        try:
            rent = await client.get_minimum_balance_for_rent_exemption(165)
            print(f"[OK] Rent exemption for token account: {rent} lamports")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Rent exemption: {e}")

    finally:
        await client.close()

    print(f"\n=== {ok}/{total} checks passed ===")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
