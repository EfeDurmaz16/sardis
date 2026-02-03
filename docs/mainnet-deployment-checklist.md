# Mainnet Deployment Pre-Flight Checklist

## Smart Contracts

The deployment script is at `contracts/script/DeployMainnet.s.sol`.

### Before Deploying

- [ ] All Foundry tests pass: `cd contracts && forge test`
- [ ] Slither static analysis clean: `slither contracts/src/`
- [ ] Gas report reviewed: `forge test --gas-report`
- [ ] Constructor arguments verified (owner address, token addresses)
- [ ] OpenZeppelin contract versions pinned in `foundry.toml`
- [ ] Deployer wallet has sufficient native token for gas (ETH/MATIC)
- [ ] Multi-sig set as contract owner (not EOA)

### Deployment Order

1. `SardisWalletFactory` — factory for agent wallets
2. `SardisAgentWallet` — implementation contract
3. `SardisEscrow` — escrow for marketplace transactions

### Post-Deployment

- [ ] Verify all contracts on block explorer (`forge verify-contract`)
- [ ] Transfer ownership to multi-sig
- [ ] Test a small transaction end-to-end
- [ ] Record deployed addresses in `contracts/deployments/`

## Backend API

- [ ] `DATABASE_URL` points to production Neon instance with SSL
- [ ] All required env vars set (see `docs/secret-management.md`)
- [ ] Database migrations applied: schema matches `SCHEMA_SQL`
- [ ] Health check passes: `curl https://api.sardis.io/health`
- [ ] Rate limiting configured for production load
- [ ] Sentry monitoring active with `SENTRY_DSN`

## Chain Configuration

Update `packages/sardis-core/src/sardis_v2_core/config.py` with mainnet:

| Chain | Chain ID | Verified |
|-------|----------|----------|
| Ethereum | 1 | [ ] |
| Base | 8453 | [ ] |
| Polygon | 137 | [ ] |
| Arbitrum | 42161 | [ ] |
| Optimism | 10 | [ ] |

- [ ] RPC URLs configured (Alchemy/Infura production keys)
- [ ] Token contract addresses verified on mainnet
- [ ] Gas estimation tested on each chain

## External Services

- [ ] Turnkey: production organization, MPC wallets created
- [ ] Persona: production template ID, KYC flow tested
- [ ] Elliptic: production API key, sanctions screening verified
- [ ] Lithic: production card program approved
- [ ] Stripe: production API key, webhook endpoints configured

## Monitoring & Alerts

- [ ] Sentry alerts configured for error spikes
- [ ] Uptime monitoring on `/health` and `/ready`
- [ ] Database connection pool alerts (Neon dashboard)
- [ ] Webhook delivery failure alerts

## Rollback Plan

1. Vercel instant rollback to previous deployment
2. Database: Neon point-in-time restore (30-day retention)
3. Contracts: pause functionality via multi-sig (if implemented)

## Final Sign-Off

- [ ] Load test completed (`tests/load/k6_load_test.js`)
- [ ] Security audit report reviewed
- [ ] All team members briefed on deployment
- [ ] Incident response channel ready
