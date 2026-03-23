# FX and Cross-Chain Bridge Guide

How to swap stablecoins and move funds across chains using the Sardis
protocol. This guide covers FX routing, quote execution, bridge
transfers, supported pairs, and fee comparison.

---

## Table of Contents

1. [Overview](#overview)
2. [How FX Routing Works](#how-fx-routing-works)
3. [Getting a Quote](#getting-a-quote)
4. [Executing a Swap](#executing-a-swap)
5. [Cross-Chain Bridge Transfers](#cross-chain-bridge-transfers)
6. [Supported Pairs and Chains](#supported-pairs-and-chains)
7. [Fee Comparison](#fee-comparison)
8. [Best Practices](#best-practices)

---

## Overview

Sardis provides two primitives for moving value between currencies and
chains:

| Primitive | Purpose | API Prefix |
|-----------|---------|------------|
| **FX Swap** | Convert between stablecoin denominations on the same chain | `/fx/*` |
| **Bridge Transfer** | Move a single token from one chain to another | `/bridge/*` |

Both primitives can be composed: swap USDC to EURC on Base, then bridge
EURC from Base to Tempo in two sequential API calls.

---

## How FX Routing Works

The Sardis FX engine automatically selects the best liquidity provider
based on the chain where the swap will execute:

```
                        +-----------------+
    Request arrives --> | FX Router       |
                        +--------+--------+
                                 |
                   +-------------+-------------+
                   |                           |
             chain == "tempo"            chain != "tempo"
                   |                           |
           +-------v-------+          +--------v--------+
           |  Tempo DEX    |          |  Uniswap V3     |
           |  (native)     |          |  (EVM chains)   |
           +---------------+          +-----------------+
```

### Tempo DEX

When the swap chain is `tempo`, Sardis routes through the native Tempo
DEX. Tempo launched in March 2026 with $500M Series A backing and
100K+ TPS. The DEX uses a CLOB (central limit order book) model,
offering tight spreads on high-volume stablecoin pairs.

Advantages:
- Sub-second finality
- Minimal gas fees (Tempo's gas model)
- Deep USDC/EURC and USDC/USDT liquidity

### Uniswap V3 (Other EVM Chains)

For swaps on Base, Ethereum, Polygon, Arbitrum, or Optimism, Sardis
routes through Uniswap V3 concentrated liquidity pools. The router
queries the pool for the best price within the caller's slippage
tolerance.

Advantages:
- Widest chain coverage
- Battle-tested smart contracts
- Permissionless liquidity

---

## Getting a Quote

Before executing a swap, request a quote. Quotes are valid for **30
seconds** and lock in a rate.

### API Request

```
POST /fx/quote
```

```json
{
  "from_currency": "USDC",
  "to_currency": "EURC",
  "from_amount": "1000.00",
  "chain": "tempo",
  "slippage_bps": 50
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `from_currency` | Source stablecoin (e.g., `USDC`, `EURC`, `USDT`) |
| `to_currency` | Target stablecoin |
| `from_amount` | Amount to swap |
| `chain` | Chain for execution. Determines the provider |
| `slippage_bps` | Maximum slippage in basis points (1-1000). Default 50 (0.5%) |

### Response

```json
{
  "quote_id": "fxq_a1b2c3d4e5f6",
  "from_currency": "USDC",
  "to_currency": "EURC",
  "from_amount": "1000.00",
  "to_amount": "921.50",
  "rate": "0.9215",
  "effective_rate": "0.9215",
  "slippage_bps": 50,
  "provider": "tempo_dex",
  "chain": "tempo",
  "status": "quoted",
  "expires_at": "2026-03-23T12:00:30+00:00",
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

The `rate` field is the indicative mid-market rate. The `effective_rate`
is the actual rate after pool impact and fees. For stablecoin pairs
these are typically very close.

### Checking Rates Without Committing

Use `GET /fx/rates` to retrieve all indicative rates without creating a
quote:

```json
{
  "rates": [
    { "from": "USDC", "to": "EURC", "rate": "0.9215", "provider": "tempo_dex" },
    { "from": "EURC", "to": "USDC", "rate": "1.0852", "provider": "tempo_dex" },
    { "from": "USDC", "to": "USDT", "rate": "1.0000", "provider": "tempo_dex" },
    { "from": "USDT", "to": "USDC", "rate": "1.0000", "provider": "tempo_dex" }
  ],
  "updated_at": "2026-03-23T12:00:00+00:00"
}
```

Indicative rates are for display purposes. Always use `POST /fx/quote`
for execution-grade pricing.

---

## Executing a Swap

Once you have a valid quote, execute it before the 30-second expiry.

### API Request

```
POST /fx/execute
```

```json
{
  "quote_id": "fxq_a1b2c3d4e5f6"
}
```

### Lifecycle

```
quoted  -->  executing  -->  completed
                  \
                   -->  failed
```

If the quote has expired, the API returns `410 Gone` and the quote
transitions to `expired`. Request a new quote and retry.

### Successful Response

```json
{
  "quote_id": "fxq_a1b2c3d4e5f6",
  "status": "completed",
  "from_amount": "1000.00",
  "to_amount": "921.50",
  ...
}
```

### Error Cases

| Status | Meaning | Action |
|--------|---------|--------|
| 404 | Quote not found | Check quote_id |
| 409 | Quote already used or cancelled | Fetch a new quote |
| 410 | Quote expired | Fetch a new quote (within 30s this time) |

---

## Cross-Chain Bridge Transfers

Bridge transfers move a token from one blockchain to another. Sardis
abstracts over multiple bridge providers and selects the best one based
on speed, cost, and reliability.

### API Request

```
POST /bridge/transfer
```

```json
{
  "from_chain": "base",
  "to_chain": "tempo",
  "token": "USDC",
  "amount": "500.00",
  "bridge_provider": "relay"
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `from_chain` | Source chain |
| `to_chain` | Destination chain (must differ from source) |
| `token` | Token to bridge (default `USDC`) |
| `amount` | Amount to transfer |
| `bridge_provider` | Provider selection (see table below) |

### Supported Bridge Providers

| Provider | Description | Speed | Fee (bps) |
|----------|-------------|-------|-----------|
| **relay** | Relay Protocol -- intent-based, fastest settlement | ~30s | 5 |
| **across** | Across Protocol -- UMA-backed optimistic bridge | ~60s | 8 |
| **squid** | Squid Router -- Axelar cross-chain messaging | ~120s | 10 |
| **bungee** | Bungee (Socket) -- multi-bridge aggregator | ~90s | 12 |
| **layerzero** | LayerZero -- omnichain messaging protocol | ~180s | 15 |

The default provider is `relay` for its combination of low fees and
fast settlement.

### Response

```json
{
  "transfer_id": "brt_a1b2c3d4e5f6",
  "from_chain": "base",
  "to_chain": "tempo",
  "token": "USDC",
  "amount": "500.00",
  "bridge_provider": "relay",
  "bridge_fee": "0.025000",
  "status": "pending",
  "estimated_seconds": 30,
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

### Transfer Lifecycle

```
pending  -->  bridging  -->  completed
                  \
                   -->  failed
```

Poll the transfer status or subscribe to webhooks for updates.

### Composing FX + Bridge

To swap AND bridge in one flow (e.g., convert USDC to EURC on Base,
then bridge EURC to Tempo):

```python
# Step 1: Swap on Base
quote = await client.fx.quote(
    from_currency="USDC",
    to_currency="EURC",
    from_amount="1000.00",
    chain="base",
)
swap = await client.fx.execute(quote_id=quote.quote_id)

# Step 2: Bridge the output to Tempo
transfer = await client.bridge.transfer(
    from_chain="base",
    to_chain="tempo",
    token="EURC",
    amount=swap.to_amount,
    bridge_provider="relay",
)
```

---

## Supported Pairs and Chains

### FX Pairs

| From | To | Indicative Rate | Provider |
|------|----|-----------------|----------|
| USDC | EURC | 0.9215 | tempo_dex / uniswap_v3 |
| EURC | USDC | 1.0852 | tempo_dex / uniswap_v3 |
| USDC | USDT | 1.0000 | tempo_dex / uniswap_v3 |
| USDT | USDC | 1.0000 | tempo_dex / uniswap_v3 |

Rates are indicative and fluctuate based on market conditions. Always
request a quote for execution-grade pricing.

### Chains for FX

| Chain | DEX Provider | Notes |
|-------|-------------|-------|
| Tempo | Tempo DEX (native) | Fastest, lowest fees |
| Base | Uniswap V3 | Deep USDC liquidity |
| Ethereum | Uniswap V3 | Highest gas costs |
| Polygon | Uniswap V3 | Low gas |
| Arbitrum | Uniswap V3 | Low gas, fast finality |
| Optimism | Uniswap V3 | Low gas, OP Stack |

### Chains for Bridge

All chains above can serve as source or destination for bridge
transfers. The token must be available on both chains.

| Token | Tempo | Base | Ethereum | Polygon | Arbitrum | Optimism |
|-------|-------|------|----------|---------|----------|----------|
| USDC | yes | yes | yes | yes | yes | yes |
| EURC | yes | yes | yes | yes | -- | -- |
| USDT | -- | -- | yes | yes | yes | yes |

---

## Fee Comparison

### FX Swap Fees

FX swaps incur the underlying DEX's swap fee plus gas:

| Provider | Swap Fee | Gas (typical) | Total for $1000 |
|----------|----------|---------------|-----------------|
| Tempo DEX | ~1 bp | negligible | ~$0.10 |
| Uniswap V3 (Base) | ~5 bp | ~$0.02 | ~$0.52 |
| Uniswap V3 (Ethereum) | ~5 bp | ~$2-10 | ~$2.50-$10.50 |
| Uniswap V3 (Polygon) | ~5 bp | ~$0.01 | ~$0.51 |
| Uniswap V3 (Arbitrum) | ~5 bp | ~$0.01 | ~$0.51 |

### Bridge Fees

Bridge fees are calculated as basis points of the transfer amount:

| Provider | Fee (bps) | Fee on $1000 | Time |
|----------|-----------|-------------|------|
| Relay | 5 | $0.50 | ~30s |
| Across | 8 | $0.80 | ~60s |
| Squid | 10 | $1.00 | ~120s |
| Bungee | 12 | $1.20 | ~90s |
| LayerZero | 15 | $1.50 | ~180s |

### Cheapest Path Examples

**$5,000 USDC from Ethereum to Tempo as EURC:**

| Strategy | Total Fees | Time |
|----------|-----------|------|
| Bridge USDC (Relay) + Swap on Tempo | ~$2.60 | ~35s |
| Swap on Ethereum + Bridge EURC (Relay) | ~$12.75 | ~35s |
| Bridge USDC (Across) + Swap on Tempo | ~$4.10 | ~65s |

Recommendation: Bridge first, swap on Tempo. The Tempo DEX has the
lowest swap fees, and bridging USDC has the deepest liquidity.

**$500 USDC from Base to Arbitrum:**

| Provider | Fee | Time |
|----------|-----|------|
| Relay | $0.25 | ~30s |
| Across | $0.40 | ~60s |

Recommendation: Relay for same-token transfers under $10K.

---

## Best Practices

1. **Always quote before executing.** Indicative rates from
   `GET /fx/rates` are for display only. Use `POST /fx/quote` for
   binding pricing.

2. **Execute within the 30-second window.** Quotes expire quickly to
   protect against price movements. Build your UI to execute
   immediately after the user confirms.

3. **Use Relay as the default bridge provider.** It offers the lowest
   fees (5 bps) and fastest settlement (~30s) for most transfers.

4. **Bridge first, then swap on Tempo.** When converting currencies
   across chains, move the original token to Tempo first and swap
   there. Tempo DEX fees are significantly lower than Uniswap on
   Ethereum.

5. **Set appropriate slippage.** For stablecoin pairs, 50 bps (0.5%)
   is usually sufficient. For volatile periods or large amounts,
   increase to 100-200 bps.

6. **Handle expiry gracefully.** If a quote expires (410 response),
   fetch a new one and retry. Do not cache quote IDs across sessions.

7. **Compose with mandates.** Mandate bounds apply to the final
   settled amount. If your mandate limits spending to USDC, perform
   the FX swap first, then use the USDC output with the mandate.

8. **Monitor bridge transfers.** Bridge transfers are asynchronous.
   Use webhooks or poll the transfer status endpoint to confirm
   completion before proceeding with downstream logic.
