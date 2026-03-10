# Coinbase Integration Spec

## Partner: Coinbase (Onramp, CDP Wallets, x402 Protocol)

**Status:** Production-ready
**Primary Integration:** Coinbase Onramp (hosted, free)
**Secondary Integrations:** CDP wallet support, x402 protocol

---

## 1. Overview

Sardis integrates with Coinbase across three touchpoints: fiat-to-crypto onramp for wallet funding, CDP (Coinbase Developer Platform) wallet support for external wallet connections, and x402 protocol support for HTTP-native payments. Together, these integrations provide a complete on-ramp and interoperability layer for agents and users entering the Sardis ecosystem.

### Integration Summary

| Integration | Purpose | Status | Cost |
|-------------|---------|--------|------|
| Coinbase Onramp | Fiat-to-USDC conversion for wallet funding | Production | Free (hosted) |
| CDP Wallet Support | External wallet connection to checkout | Production | Free |
| x402 Protocol | HTTP-native micropayments | Integrated | Per-transaction |

---

## 2. Coinbase Onramp

### 2.1 Architecture

Coinbase Onramp provides a hosted, no-cost fiat onramp experience. Users complete KYC and purchase USDC directly from Coinbase, with funds deposited to a Sardis-managed wallet address.

```
User / Agent Operator
    |
    v
Sardis Checkout UI / Dashboard
    |
    v
Coinbase Onramp (hosted widget)
    |
    +--> User completes KYC (if new)
    +--> User selects payment method (card, bank, Apple Pay)
    +--> User purchases USDC
    |
    v
USDC deposited to Sardis wallet address (on-chain)
    |
    v
Sardis wallet balance updated
```

### 2.2 Onramp Token Flow

The checkout flow uses a secure token exchange to initialize the Coinbase Onramp widget:

1. **Client requests onramp token** from Sardis API
2. **Sardis API validates** the session and payer wallet address
3. **Client initializes** Coinbase Onramp SDK with the token
4. **User completes** purchase flow in Coinbase-hosted UI
5. **USDC arrives** at the settlement address
6. **Sardis confirms** on-chain receipt and updates session

### 2.3 Configuration

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `COINBASE_ONRAMP_APP_ID` | Yes | Coinbase Developer Platform app ID |
| `COINBASE_ONRAMP_API_KEY` | No | API key for server-side token generation |
| `SARDIS_CHECKOUT_CHAIN` | Yes | Target chain (`base` for production, `base_sepolia` for testnet) |

**Frontend Configuration:**

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_CHAIN` | Yes | Chain identifier for the checkout UI |
| `VITE_WALLETCONNECT_PROJECT_ID` | Yes | WalletConnect project ID for external wallet support |

### 2.4 Supported Payment Methods

| Method | Availability | Settlement Time |
|--------|-------------|-----------------|
| Debit card | US, EU, UK | Instant |
| Credit card | US, EU, UK | Instant |
| Bank transfer (ACH) | US | 1-3 business days |
| Apple Pay | US, EU, UK | Instant |
| Google Pay | US, EU, UK | Instant |

### 2.5 Supported Chains and Tokens

| Chain | Token | Onramp Support |
|-------|-------|----------------|
| Base | USDC | Primary (recommended) |
| Ethereum | USDC | Supported |
| Polygon | USDC | Supported |
| Arbitrum | USDC | Supported |
| Optimism | USDC | Supported |

### 2.6 Fee Structure

Coinbase Onramp is **free for the integrator** (Sardis). Coinbase charges the end user a spread on the purchase, typically 1-2% depending on payment method and region.

---

## 3. CDP Wallet Support

### 3.1 External Wallet Connection

Sardis checkout supports CDP (Coinbase Developer Platform) wallets as an external wallet source. Users can connect their Coinbase Wallet to pay for checkout sessions directly.

```
User with Coinbase Wallet
    |
    v
Sardis Checkout UI
    |
    v
WalletConnect / Coinbase Wallet SDK
    |
    v
EIP-191 signature verification (connect-external endpoint)
    |
    v
payer_wallet_address stored on session
    |
    v
User initiates USDC transfer to settlement_address
    |
    v
confirm-external-payment endpoint validates on-chain receipt
```

### 3.2 Wallet Verification

External wallets (including Coinbase Wallet) are verified via EIP-191 signature:

1. Checkout UI prompts wallet to sign a challenge message
2. Sardis API verifies the signature matches the claimed address
3. `payer_wallet_address` is stored on the checkout session
4. Onramp token endpoint validates address match before issuing tokens

### 3.3 Payment Flow for External Wallets

1. User connects Coinbase Wallet via WalletConnect or Coinbase Wallet SDK
2. Sardis displays the `settlement_address` for the merchant
3. User approves USDC transfer from Coinbase Wallet to settlement address
4. Client calls `confirm-external-payment` with transaction hash
5. Sardis verifies on-chain transfer and marks session as paid

### 3.4 Frontend Stack

```
wagmi + viem (Ethereum interactions)
    |
    +-- WalletConnect (primary connection method)
    +-- Coinbase Wallet SDK (native Coinbase connection)
    |
    v
Sardis Checkout React Component
```

---

## 4. x402 Protocol Support

### 4.1 Overview

x402 is an HTTP-native payment protocol that uses the HTTP 402 (Payment Required) status code for machine-to-machine micropayments. Sardis supports x402 for agent-to-service payments where the agent needs to pay for API access or computational resources.

### 4.2 How It Works

```
AI Agent --> HTTP Request --> Service Provider
                                |
                                v
                          HTTP 402 Payment Required
                          Headers:
                            X-Payment-Protocol: x402
                            X-Payment-Amount: 0.001
                            X-Payment-Token: USDC
                            X-Payment-Address: 0x...
                                |
                                v
AI Agent --> Sardis SDK --> Policy Check --> On-chain Payment
                                |
                                v
                          HTTP Request (with payment proof)
                          Headers:
                            X-Payment-Proof: 0x... (tx hash)
                                |
                                v
                          HTTP 200 OK (service delivered)
```

### 4.3 Sardis x402 Client

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Agent makes an HTTP request that may require payment
response = await client.http.request(
    url="https://api.example.com/expensive-endpoint",
    method="GET",
    wallet_id="wal_abc123",
    max_payment=Decimal("1.00"),  # Max auto-approve amount
)
```

The Sardis SDK intercepts HTTP 402 responses, evaluates the payment request against the agent's spending policy, and if approved, executes the on-chain payment and retries the request with proof of payment.

### 4.4 Policy Integration

x402 payments are subject to the same spending policy engine as all other Sardis transactions:
- Amount limits (per-transaction, daily, monthly)
- Merchant/service allowlists
- Token and chain restrictions
- Natural language policy rules

### 4.5 Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SARDIS_X402_ENABLED` | No | Enable x402 auto-payment (default: false) |
| `SARDIS_X402_MAX_AUTO_APPROVE` | No | Maximum amount for auto-approval without human confirmation |

---

## 5. Cross-Chain Settlement via CCTP V2

Coinbase's USDC and the Cross-Chain Transfer Protocol (CCTP) V2 are integral to Sardis's multi-chain architecture:

### 5.1 CCTP V2 Architecture

- **Unified addresses:** Same USDC contract address semantics across all supported chains
- **Permissionless:** No bridge approval required for transfers
- **Native burn-and-mint:** Circle-operated, no wrapped tokens

### 5.2 Sardis Usage

| Flow | CCTP Role |
|------|-----------|
| Onramp on Base, spend on Polygon | CCTP bridges USDC cross-chain |
| Multi-chain agent wallets | CCTP enables balance consolidation |
| Checkout settlement | CCTP routes to merchant's preferred chain |

---

## 6. Related Files

| File | Purpose |
|------|---------|
| `packages/sardis-api/src/sardis_api/routers/merchant_checkout.py` | Checkout session management, onramp token endpoint |
| `packages/sardis-api/src/sardis_api/routers/onchain_payments.py` | On-chain payment verification |
| `packages/sardis-api/src/sardis_api/routers/wallets.py` | Wallet management, external wallet connection |
| `packages/sardis-core/src/sardis_v2_core/config.py` | Chain configuration, Coinbase settings |
| `packages/sardis-protocol/src/sardis_protocol/schemas.py` | x402 payment schemas |
| `dashboard/` | Dashboard with onramp widget integration |
| `packages/sardis-checkout/` | Checkout UI with Coinbase Onramp and external wallet support |
