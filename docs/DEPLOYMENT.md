# Sardis Deployment Guide

## Smart Contract Configuration

Sardis requires deployed smart contracts on each supported chain. Contract addresses can be configured via environment variables or hardcoded in the codebase.

### Environment Variables (Recommended)

Set these environment variables for each chain you want to support:

```bash
# Base Sepolia (Testnet)
SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
SARDIS_BASE_SEPOLIA_ESCROW_ADDRESS=0x...

# Polygon Amoy (Testnet)
SARDIS_POLYGON_AMOY_WALLET_FACTORY_ADDRESS=0x...
SARDIS_POLYGON_AMOY_ESCROW_ADDRESS=0x...

# Ethereum Sepolia (Testnet)
SARDIS_ETHEREUM_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
SARDIS_ETHEREUM_SEPOLIA_ESCROW_ADDRESS=0x...

# Arbitrum Sepolia (Testnet)
SARDIS_ARBITRUM_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
SARDIS_ARBITRUM_SEPOLIA_ESCROW_ADDRESS=0x...

# Optimism Sepolia (Testnet)
SARDIS_OPTIMISM_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
SARDIS_OPTIMISM_SEPOLIA_ESCROW_ADDRESS=0x...
```

### Supported Chains

| Chain | Chain ID | Status | Notes |
|-------|----------|--------|-------|
| Base | 8453 | ✅ Supported | Primary chain |
| Base Sepolia | 84532 | ✅ Supported | Testnet |
| Polygon | 137 | ✅ Supported | |
| Polygon Amoy | 80002 | ✅ Supported | Testnet |
| Ethereum | 1 | ✅ Supported | Higher gas costs |
| Ethereum Sepolia | 11155111 | ✅ Supported | Testnet |
| Arbitrum | 42161 | ✅ Supported | |
| Arbitrum Sepolia | 421614 | ✅ Supported | Testnet |
| Optimism | 10 | ✅ Supported | |
| Optimism Sepolia | 11155420 | ✅ Supported | Testnet |
| Solana | - | ❌ Not Implemented | Requires Anchor programs |

### Contract Deployment Order

1. Deploy `SardisWalletFactory` contract
2. Deploy `SardisEscrow` contract
3. Configure escrow address in wallet factory
4. Verify contracts on block explorer
5. Set environment variables

## Compliance Configuration

### Audit Trail Storage

⚠️ **CRITICAL**: The default `ComplianceAuditStore` uses in-memory storage which is NOT suitable for production.

For production, configure PostgreSQL:

```bash
DATABASE_URL=postgresql://user:pass@host:5432/sardis
```

Required for regulatory compliance:
- 7 year retention (US)
- 5 year retention (EU)
- Immutable audit logs
- No DELETE capability

### KYC Provider (Persona)

```bash
PERSONA_API_KEY=persona_live_...
PERSONA_WEBHOOK_SECRET=persona_whs_...
```

### Sanctions Screening (Elliptic)

```bash
ELLIPTIC_API_KEY=...
ELLIPTIC_API_SECRET=...
```

## MPC Wallet Configuration

### Turnkey (Recommended)

```bash
TURNKEY_API_PUBLIC_KEY=...
TURNKEY_API_PRIVATE_KEY=...
TURNKEY_ORGANIZATION_ID=...
```

### Local EOA (Development Only)

```bash
SARDIS_EOA_PRIVATE_KEY=0x...
SARDIS_EOA_ADDRESS=0x...
```

## Environment Modes

```bash
# Development (simulated transactions)
SARDIS_ENVIRONMENT=dev
SARDIS_CHAIN_MODE=simulated

# Testnet (real transactions on testnets)
SARDIS_ENVIRONMENT=staging
SARDIS_CHAIN_MODE=testnet

# Production (real transactions on mainnets)
SARDIS_ENVIRONMENT=prod
SARDIS_CHAIN_MODE=mainnet
```

## Pre-Flight Checklist

Before going to production:

- [ ] All contract addresses configured for target chains
- [ ] PostgreSQL configured for audit trail
- [ ] KYC provider (Persona) API keys set
- [ ] Sanctions provider (Elliptic) API keys set
- [ ] MPC provider (Turnkey) configured
- [ ] Rate limiting enabled
- [ ] Monitoring/alerting configured
- [ ] Smart contracts audited
- [ ] Compliance review completed
