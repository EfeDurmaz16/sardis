# Sardis Deployment Manifest

> Single source of truth for all contract deployments across chains.
> Last updated: 2026-03-08

## Deployment Overview

Sardis deploys **2 custom contracts** per chain. All other infrastructure is pre-deployed.

| Contract | Type | Lifecycle | Chains Deployed |
|----------|------|-----------|-----------------|
| SardisLedgerAnchor | Custom (Sardis) | `pending_deploy` | None yet |
| RefundProtocol | Custom (Circle fork) | `pending_deploy` | None yet |
| Zodiac Roles Module | Pre-deployed (Gnosis Guild) | `canonical_live` | All EVM chains |
| Circle Paymaster | Pre-deployed (Circle) | `canonical_live` | All EVM chains |
| Safe Proxy Factory | Pre-deployed (Safe) | `canonical_live` | All EVM chains |
| Safe Singleton v1.4.1 | Pre-deployed (Safe) | `canonical_live` | All EVM chains |
| Safe 4337 Module | Pre-deployed (Safe) | `canonical_live` | All EVM chains |
| EntryPoint v0.7 | Pre-deployed (EF) | `canonical_live` | All EVM chains |

---

## Pre-Deployed Infrastructure (All Chains)

These addresses are identical across all supported EVM chains. Sardis does not deploy or maintain these contracts.

| Contract | Address | Source |
|----------|---------|--------|
| Zodiac Roles Module | `0x9646fDAD06d3e24444381f44362a3B0eB343D337` | Gnosis Guild |
| Circle Paymaster | `0x0578cFB241215b77442a541325d6A4E6dFE700Ec` | Circle |
| Safe Proxy Factory | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` | Safe |
| Safe Singleton v1.4.1 | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | Safe |
| Safe 4337 Module | `0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226` | Safe |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | Uniswap |
| EntryPoint v0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | EF / Infinitism |

---

## Mainnet Chains

### Base (Chain ID: 8453) -- PRIMARY

| Contract | Address | Lifecycle | Source |
|----------|---------|-----------|--------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom |
| RefundProtocol | -- | `pending_deploy` | Custom |
| Zodiac Roles Module | `0x9646fDAD...D337` | `canonical_live` | Pre-deployed |

**Status:** Pending deployment. See `scripts/deploy-mainnet-contracts.sh`.

### Ethereum (Chain ID: 1)

| Contract | Address | Lifecycle | Source |
|----------|---------|-----------|--------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom |
| RefundProtocol | -- | `pending_deploy` | Custom |

**Status:** Pending. Deploy after Base mainnet is stable.

### Polygon (Chain ID: 137)

| Contract | Address | Lifecycle | Source |
|----------|---------|-----------|--------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom |
| RefundProtocol | -- | `pending_deploy` | Custom |

**Status:** Pending. Deploy after Base mainnet is stable.

### Arbitrum (Chain ID: 42161)

| Contract | Address | Lifecycle | Source |
|----------|---------|-----------|--------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom |
| RefundProtocol | -- | `pending_deploy` | Custom |

**Status:** Pending. Deploy after Base mainnet is stable.

### Optimism (Chain ID: 10)

| Contract | Address | Lifecycle | Source |
|----------|---------|-----------|--------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom |
| RefundProtocol | -- | `pending_deploy` | Custom |

**Status:** Pending. Deploy after Base mainnet is stable.

---

## Testnet Chains

### Base Sepolia (Chain ID: 84532)

| Contract | Address | Lifecycle | Source | Notes |
|----------|---------|-----------|--------|-------|
| SardisLedgerAnchor | -- | `pending_deploy` | Custom | |
| RefundProtocol | -- | `pending_deploy` | Custom | |
| WalletFactory (legacy) | `0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7` | `deprecated` | Custom | Old contract, pre-Safe migration |
| Escrow (legacy) | `0x5cf752B512FE6066a8fc2E6ce555c0C755aB5932` | `deprecated` | Custom | Old contract, replaced by RefundProtocol |

**Deployer:** `0x57bfF0E18C994c14a7f034CC5aBda9e7341Fb906`
**Block:** 36783677 | **Timestamp:** 2026-01-25T12:07:22Z

### Ethereum Sepolia | Polygon Amoy | Arbitrum Sepolia | Optimism Sepolia

All testnets besides Base Sepolia have no contracts deployed yet. Status: `pending_deploy`.

---

## Deprecated Contracts (Source Only, Never Deploy)

| Contract | File | Replacement |
|----------|------|-------------|
| SardisPolicyModule | `src/SardisPolicyModule.sol` | Zodiac Roles (pre-deployed) |
| SardisVerifyingPaymaster | `src/SardisVerifyingPaymaster.sol` | Circle Paymaster (pre-deployed) |
| SardisWalletFactory | `deprecated/SardisWalletFactory.sol` | Safe Proxy Factory (pre-deployed) |
| SardisAgentWallet | `deprecated/SardisAgentWallet.sol` | Safe Smart Accounts (pre-deployed) |
| SardisEscrow | `deprecated/SardisEscrow.sol` | RefundProtocol (custom deploy) |

---

## Lifecycle Definitions

| Value | Meaning |
|-------|---------|
| `canonical_live` | Production contract, actively used |
| `pending_deploy` | Ready for deployment, not yet on-chain |
| `experimental` | Testing/development only |
| `deprecated` | Superseded, do not deploy |

Source: `packages/sardis-core/src/sardis_v2_core/config.py` -- `ContractLifecycle` enum.
