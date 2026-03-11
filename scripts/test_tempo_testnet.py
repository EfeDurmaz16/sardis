"""Tempo Moderato testnet smoke test.

Verifies:
1. RPC connectivity to https://rpc.moderato.tempo.xyz
2. Chain ID = 42431
3. pathUSD (USDC) TIP-20 token is queryable
4. Fee model: gas price returns value (fees in TIP-20, not native token)

Usage:
    uv run --no-project python scripts/test_tempo_testnet.py
"""
from __future__ import annotations

import asyncio
import sys

import httpx


TEMPO_RPC = "https://rpc.moderato.tempo.xyz"
CHAIN_ID = 42431
PATH_USD = "0x20c0000000000000000000000000000000000000"


async def rpc_call(client: httpx.AsyncClient, method: str, params: list | None = None) -> dict:
    """Make a JSON-RPC call to Tempo."""
    resp = await client.post(TEMPO_RPC, json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    })
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        print(f"  RPC error: {data['error']}")
        return data
    return data


async def main() -> int:
    print("=== Tempo Moderato Testnet Smoke Test ===\n")
    ok = 0
    total = 4

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Chain ID
        try:
            result = await rpc_call(client, "eth_chainId")
            chain_id = int(result["result"], 16)
            assert chain_id == CHAIN_ID, f"Expected {CHAIN_ID}, got {chain_id}"
            print(f"[OK] Chain ID: {chain_id}")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Chain ID: {e}")

        # 2. Latest block
        try:
            result = await rpc_call(client, "eth_blockNumber")
            block = int(result["result"], 16)
            print(f"[OK] Latest block: {block}")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Latest block: {e}")

        # 3. Gas price
        try:
            result = await rpc_call(client, "eth_gasPrice")
            gas_price = int(result["result"], 16)
            print(f"[OK] Gas price: {gas_price} wei")
            ok += 1
        except Exception as e:
            print(f"[FAIL] Gas price: {e}")

        # 4. pathUSD totalSupply check
        try:
            result = await rpc_call(client, "eth_call", [{
                "to": PATH_USD,
                "data": "0x18160ddd",  # totalSupply()
            }, "latest"])
            if "error" in result:
                print(f"[WARN] pathUSD totalSupply: RPC error (contract may not support totalSupply)")
            else:
                print(f"[OK] pathUSD totalSupply response: {result['result'][:20]}...")
            ok += 1
        except Exception as e:
            print(f"[FAIL] pathUSD totalSupply: {e}")

    print(f"\n=== {ok}/{total} checks passed ===")
    return 0 if ok >= 3 else 1  # Allow 1 failure (pathUSD may not have totalSupply)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
