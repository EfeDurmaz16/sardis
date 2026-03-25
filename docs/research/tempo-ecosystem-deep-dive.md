# Tempo Ecosystem Deep Dive

> Research compiled 2026-03-26 from official Tempo documentation (docs.tempo.xyz).
> Tempo Mainnet launched 2026-03-18.

---

## 1. Wallet Providers

Tempo's wallet ecosystem is organized into four categories: **Embedded**, **Custodial & Institutional**, **Self-Custodial**, and **Agentic**.

### 1.1 Embedded Wallets

These are wallets that can be integrated directly into applications, providing seamless UX without users needing external wallet software.

#### Blockradar
- **URL:** https://blockradar.co
- **What it does:** Non-custodial wallet infrastructure for fintechs running stablecoin payments. Focused on merchant settlement, cross-border payouts, compliance, treasury operations, and multi-chain liquidity.
- **Key features:** Unified API for issuing wallets (users, merchants, treasury), fiat inflows via virtual accounts, gasless stablecoin transactions, automatic AML checks, configurable balance sweeps, cross-chain swap and bridge.
- **Integration:** API or Blockradar Dashboard (https://dashboard.blockradar.co/)
- **Docs:** https://docs.blockradar.co/

#### Crossmint
- **URL:** https://crossmint.com
- **What it does:** All-in-one platform with unified APIs for wallets, stablecoin orchestration, checkout flows, and tokenization.
- **Key features:** Gasless, seed-phrase-free UX; bank-grade security and compliance; no-code dashboards; single interface for payments to asset management on Tempo.
- **Integration:** Crossmint console (https://crossmint.com/console)
- **Docs:** Wallets (https://docs.crossmint.com/wallets/), Stablecoin Orchestration (https://docs.crossmint.com/stablecoin-orchestration/), Payments (https://docs.crossmint.com/payments), Tokenization (https://docs.crossmint.com/minting)
- **Solution Guide (Fintech):** https://docs.crossmint.com/solutions/overview#fintech

#### Dynamic
- **URL:** https://dynamic.xyz
- **What it does:** Combines authentication, smart wallets, and key management into a flexible SDK. Onboards users with familiar login methods and provisions Tempo-compatible wallets.
- **Integration:** Enable Tempo testnet in the Dynamic dashboard (https://app.dynamic.xyz/dashboard/chains-and-networks). Create account at https://www.dynamic.xyz/get-started.

#### Para (formerly Capsule)
- **URL:** https://getpara.com
- **What it does:** Comprehensive wallet and authentication suite for fintech and crypto apps. Flexible login methods, MPC-backed wallets, fast authentication, infrastructure for automating onchain activity.
- **Status:** Adding Tempo chain support.
- **Integration:** Para Dev Portal (https://developer.getpara.com/), Docs (https://docs.getpara.com/v2/introduction/welcome).

#### Privy
- **URL:** https://privy.io
- **What it does:** Secure key management and embedded wallets. Self-custodial wallets for users, treasury wallet management.
- **Tempo-native features:** Gas sponsorship, webhooks for onchain events, delegated signatures, simple wallet funding.
- **Integration:** Create an Ethereum wallet with Privy and pass `"caip2": "eip155:4217"` when making transactions.
- **Recipe:** https://docs.privy.io/recipes/evm/tempo
- **Example App:** https://github.com/privy-io/examples/tree/main/examples/privy-next-tempo (peer-to-peer payments using Tempo transaction memos)
- **Docs:** Create wallet (https://docs.privy.io/wallets/wallets/create/create-a-wallet#param-chain-type-1), Send transaction (https://docs.privy.io/wallets/using-wallets/ethereum/send-a-transaction#usage-9)

#### Turnkey
- **URL:** https://turnkey.com
- **What it does:** Programmable key management and non-custodial wallet infrastructure. Granular signing policies, automated transaction flows.
- **Key features:** Secure Tempo transaction signing, automated wallet operations, custom logic around key usage, sponsor-style workflows for gasless/subsidized transactions.
- **Integration:** Create account at https://app.turnkey.com/dashboard, follow the Embedded Wallet Kit guide (https://docs.turnkey.com/sdks/react/getting-started).
- **Example:** `with-tempo` example in Turnkey SDK (https://github.com/tkhq/sdk/tree/main/examples/with-tempo).

### 1.2 Custodial & Institutional Wallets

#### BitGo
- **URL:** https://bitgo.com
- **What it does:** Institutional-grade custody, trading, and wallet infrastructure. Custodial and self-custody wallet solutions.
- **Key features:** Robust security and compliance controls, US qualified custodian, globally licensed and regulated.
- **Docs:** https://developers.bitgo.com/

#### Cubist
- **URL:** https://cubist.dev
- **What it does:** High-performance institutional-grade infrastructure for wallets, tokenization, payments, and private smart contracts.
- **Key features:** Treasury management, automated internal operations, cryptographic audit trails for regulators, familiar auth methods and gas sponsorship for end users and AI agents.
- **Tempo page:** https://cubist.dev/use-cases/payments-tokenization

#### DFNS
- **URL:** https://dfns.co
- **What it does:** Programmable key management and wallet-as-a-service. Distributed MPC key generation, policy-based access controls.
- **Integration:** DFNS dashboard (https://app.dfns.io), Docs (https://docs.dfns.co/)

#### Fireblocks
- **URL:** https://fireblocks.com
- **What it does:** Enterprise-grade digital asset infrastructure for custody, transfers, and tokenization. MPC-based signing, policy engine, and transaction API.
- **Integration:** Fireblocks console (https://console.fireblocks.io/), Dev docs (https://developers.fireblocks.com/)

#### Utila
- **URL:** https://utila.io
- **What it does:** Secure MPC wallet infrastructure and asset-management tooling for stablecoin teams. Multi-wallet, multi-chain treasury operations with configurable approval engines.
- **Integration:** https://utila.io/product/payments/, Request demo (https://utila.io/request-a-demo/)

### 1.3 Self-Custodial Wallets

#### OKX Wallet
- **URL:** https://www.okx.com/web3
- **What it does:** Self-custodial multi-chain wallet with native Tempo support. Store, swap, and manage Tempo-based assets with built-in DEX aggregation, staking, and DApp connectivity.

### 1.4 Agentic Wallets

#### Enact
- **URL:** https://enact.finance
- **What it does:** Programmable wallet infrastructure for teams and AI agents. Set policies once (spending limits, multisig thresholds, approval windows, automation rules) and let agents execute autonomously with onchain verifiability.
- **Key features:** Self-custodial passkey wallet, multiple signers, onchain policy deployment.
- **Integration:** Enact CLI (https://docs.enact.finance/) or Enact app (https://app.enact.finance/)

#### Sponge
- **URL:** https://paysponge.com
- **What it does:** Financial infrastructure for AI agents. Hold, send, and swap crypto autonomously on Tempo.
- **Key features:** Configurable spending controls, allowlists, audit logging, first-class support for Claude and other AI frameworks via MCP and SDK.
- **Docs:** https://paysponge.com/docs

---

## 2. Orchestration (Issuance & Orchestration)

Orchestration providers handle stablecoin issuance, movement between fiat and crypto rails, and cross-border transfers.

### Brale
- **URL:** https://brale.xyz
- **What it does:** Infrastructure for issuing, transferring, and managing stablecoins across chains. On/off-ramps, payouts, cross-ecosystem stablecoin movement.
- **Two APIs:**
  1. **Stablecoin Movement & Account Management** (https://docs.brale.xyz/#stablecoin-movement--account-management-apibralexyz): Orchestrating stablecoin workflows — issuance, transfers, custody management, financial institution integration.
  2. **Stablecoin Market Data** (https://docs.brale.xyz/#stablecoin-market-data-databralexyz): Public read-only API for token metadata, stablecoin definitions, and price feeds.
- **Workflows:** Minting, redemption, swaps, payouts, treasury operations.
- **Signup:** https://app.brale.xyz/buy/signup/

### Bridge (a Stripe Company)
- **URL:** https://bridge.xyz
- **What it does:** Stablecoin orchestration for moving money between fiat and crypto rails. APIs for issuance, wallets, and cross-border stablecoin transfers.
- **Tempo Integration Guide:** https://apidocs.bridge.xyz/get-started/guides/move-money/tempo-integration-guide

---

## 3. Bridges & Exchanges

Bridges enable cross-chain asset movement to and from Tempo.

### Across
- **URL:** https://across.to
- **Type:** Intent-based with optimistic verification
- **Features:** Fast, capital-efficient bridging; near-instant cross-chain transfers with competitive fees.
- **App:** https://app.across.to/
- **Docs:** https://docs.across.to/

### Bungee
- **URL:** https://bungee.exchange
- **Type:** Bridge and DEX aggregator
- **Features:** Aggregates bridge and DEX liquidity for cost-efficient cross-chain transfers and swaps. Widget or API integration.
- **App:** https://bungee.exchange
- **Docs:** https://docs.bungee.exchange/

### LayerZero / Stargate
- **URL:** https://layerzero.network / https://stargate.finance
- **Type:** Omnichain interoperability protocol
- **Features:** Secure low-level message passing; Stargate enables native 1:1 asset transfers (USDC) into and out of Tempo.
- **Dedicated guide:** https://docs.tempo.xyz/guide/bridge-usdc-stargate (with contract addresses, code examples, EndpointDollar details)

### Relay
- **URL:** https://relay.link
- **Type:** Relayer-based instant bridging
- **Features:** Fast finality, low fees; relayers fill orders on destination chain.
- **Docs:** https://docs.relay.link/

### Squid
- **URL:** https://squidrouter.com
- **Type:** Intent-based cross-chain routing
- **Features:** Aggregates DEXs, bridges, and market makers; optimal routes with sub-5s execution; API, SDK, or widget integration.
- **App:** https://app.squidrouter.com/
- **Docs:** https://docs.squidrouter.com/

### Uniswap
- **URL:** https://hub.uniswap.org
- **Type:** DEX
- **Features:** $4T+ all-time volume, 99%+ uptime, 200ms routing latency, 10M+ assets.
- **Developer Platform:** https://developers.uniswap.org/dashboard/welcome

### 0x
- **URL:** https://0x.org
- **Type:** DEX aggregation and smart order routing
- **Features:** Institutional-grade execution, low revert rates, sub-250ms response times, built-in monetization.
- **Dashboard:** https://dashboard.0x.org/create-account
- **Docs:** https://0x.org/docs/0x-swap-api/introduction

---

## 4. Embedded Passkey Wallets

### How It Works

Tempo has **native passkey account support** built into the protocol via a custom `Tempo Transaction` type that supports WebAuthn P256 signatures. This is not an abstraction layer -- it is a first-class transaction type.

**Key properties:**
- **WebAuthn credentials** are bound to a specific domain (the Relying Party). Credentials created for `example.com` only work on that domain and its subdomains.
- **Biometric authentication:** Fingerprint, Face ID, Touch ID -- whatever the device supports.
- **Key storage:** Device's secure enclave, synced across devices via iCloud Keychain or Google Password Manager.
- **No seed phrases, no passwords.**

### Integration Steps

1. **Set up Wagmi** with the Tempo SDK (https://docs.tempo.xyz/sdk/typescript#wagmi-setup)
2. **Configure the WebAuthn Connector** in Wagmi config:

```typescript
import { createConfig, http } from 'wagmi'
import { tempo } from 'viem/chains'
import { KeyManager, webAuthn } from 'wagmi/tempo'

export const config = createConfig({
  chains: [tempo],
  connectors: [webAuthn({
    keyManager: KeyManager.localStorage(), // Use KeyManager.http() for production
  })],
  multiInjectedProviderDiscovery: false,
  transports: {
    [tempo.id]: http(),
  },
})
```

3. **Display Sign In/Sign Up buttons** using `useConnect` and `useConnectors` hooks:

```typescript
import { useConnect, useConnectors } from 'wagmi'

export function Example() {
  const connect = useConnect()
  const [connector] = useConnectors()

  return (
    <div>
      <button onClick={() => connect.connect({
        connector,
        capabilities: { type: 'sign-up' },
      })}>Sign up</button>
      <button onClick={() => connect.connect({ connector })}>Sign in</button>
    </div>
  )
}
```

### Key Manager Options

- **`KeyManager.localStorage()`** -- Stores public keys on client device. NOT recommended for production (keys lost on storage clear or device switch).
- **`KeyManager.http()`** -- Remote key manager. Recommended for production. Docs: https://wagmi.sh/tempo/keyManagers/http

### Domain-Binding Caveat

Because WebAuthn credentials are domain-bound, users cannot reuse the same passkey account on other applications. For cross-app compatibility, use the "Connect to wallets" approach (MetaMask, etc.) instead.

### Example Repository

- **Clone:** `pnpx gitpick tempoxyz/examples/tree/main/examples/accounts`
- **Source:** https://github.com/tempoxyz/examples/tree/main/examples/accounts

### Can Sardis Use This?

**Yes, but with caveats:**
- Sardis could embed Tempo passkey accounts for Tempo-native payments, creating a passwordless wallet experience.
- Credentials would be bound to `sardis.sh` (or whichever domain), meaning users would have a Sardis-specific Tempo wallet.
- For production: use `KeyManager.http()` backed by Sardis's own key server.
- Alternative: Use the "Connect to wallets" approach to connect to Tempo Wallet or MetaMask, which gives users a single identity across apps.

---

## 5. Add-Funds Flow

### Methods to Fund a Tempo Wallet

#### A. Tempo Wallet Web App (wallet.tempo.xyz)
1. Sign up or log in with passkey at https://wallet.tempo.xyz
2. Click "Add funds" on the home screen
3. Choose: fiat onramp or bridge from another chain

#### B. Tempo CLI
```bash
# Install
curl -fsSL https://tempo.xyz/install | bash

# Authenticate
tempo wallet login

# Fund (opens faucet on testnet, bridge/onramp on mainnet)
tempo wallet fund

# Transfer tokens
tempo wallet transfer <amount> <token> <to>
```

#### C. With an AI Agent
```bash
# Claude Code
claude -p "Read https://tempo.xyz/SKILL.md and fund my Tempo Wallet"

# Also supports Amp and Codex CLI
```

#### D. Bridge from Another Chain
Supported bridges: LayerZero/Stargate, Squid, Relay, Across, Bungee (see Section 3).

#### E. Testnet Faucet
The faucet provides test stablecoins (1M each):

| Asset    | Address                                      | Amount |
|----------|----------------------------------------------|--------|
| pathUSD  | `0x20c0000000000000000000000000000000000000` | 1M     |
| AlphaUSD | `0x20c0000000000000000000000000000000000001` | 1M     |
| BetaUSD  | `0x20c0000000000000000000000000000000000002` | 1M     |
| ThetaUSD | `0x20c0000000000000000000000000000000000003` | 1M     |

**Verify balance:**
```bash
cast erc20 balance 0x20c0000000000000000000000000000000000001 \
  <YOUR_ADDRESS> \
  --rpc-url https://rpc.moderato.tempo.xyz
```

### Programmatic Funding

For programmatic wallet funding, the primary paths are:
1. **Bridge API integration** -- Use Stargate, Squid, or Relay SDKs to bridge USDC from Base/Ethereum to Tempo.
2. **Direct transfer** -- If you already have funds on Tempo, use standard ERC-20 transfer or `tempo wallet transfer`.
3. **Bridge (Stripe Company)** -- Use Bridge's Tempo Integration Guide for fiat-to-Tempo stablecoin flows.
4. **Brale API** -- For programmatic stablecoin issuance and movement.

---

## 6. CLI Reference Summary

### Wallet Commands

| Command | Description |
|---------|-------------|
| `tempo wallet login` | Connect or create wallet via browser auth |
| `tempo wallet logout` | Disconnect and clear local credentials |
| `tempo wallet whoami` | Print readiness, address, balances, key state |
| `tempo wallet keys` | List keys and their spending limits |
| `tempo wallet fund` | Fund wallet (faucet on testnet, bridge on mainnet) |
| `tempo wallet transfer <amount> <token> <to>` | Transfer tokens |
| `tempo wallet services` | List all MPP-registered services |
| `tempo wallet services --search <query>` | Filter services by keyword |
| `tempo wallet services <id>` | Show service endpoints, methods, schemas |
| `tempo wallet sessions list` | List active payment sessions |
| `tempo wallet sessions sync` | Reconcile local sessions with onchain state |
| `tempo wallet sessions close --all` | Close all sessions |
| `tempo wallet sessions close --orphaned` | Close unreachable sessions |
| `tempo wallet mpp-sign` | Sign an MPP payment challenge (internal) |

### Access Keys
Each wallet can have multiple access keys with independent spending limits -- useful for constraining what an agent or script can spend.

### Payment Sessions (MPP)
- Pay-as-you-go services use sessions: wallet deposits into escrow contract, then pays per request using signed vouchers off-chain.
- Sub-100ms latency, near-zero per-request fees.
- `sync` reconciles local records with onchain state.
- `close --orphaned` cleans up sessions with unreachable counterparties.
- Use `--dry-run` to preview before executing.

---

## 7. Sardis Integration Recommendations

### Recommended Wallet Strategy

**Primary: Turnkey (already in use by Sardis)**
- Sardis already uses Turnkey for MPC wallet signing. Turnkey has a dedicated `with-tempo` example.
- Sardis can sign Tempo transactions using existing Turnkey infrastructure.
- Turnkey supports sponsor-style workflows for gasless transactions.

**Secondary: Embedded Passkey Accounts**
- For Sardis's checkout flow, embedding Tempo passkey accounts could provide a seamless UX.
- Use the Wagmi `webAuthn` connector with `KeyManager.http()` backed by Sardis's server.
- Good for: Sardis-branded wallet experience, passwordless onboarding.
- Limitation: Domain-bound -- users get a Sardis-specific Tempo wallet.

**Agentic: Enact or Sponge**
- For AI agent wallets, Enact (onchain policies) or Sponge (Claude MCP support) are strong options.
- Sponge's Claude MCP integration aligns well with Sardis's OpenAI Agents SDK.
- Enact's policy model (spending limits, multisig, automation rules) maps to Sardis's spending mandate architecture.

### Recommended Bridge Strategy

**Primary: Stargate (LayerZero)**
- Native USDC bridging with 1:1 transfers.
- Tempo has a dedicated bridging guide with contract addresses.
- Best for: Sardis wallet funding, merchant settlement from Base to Tempo.

**Secondary: Relay or Across**
- Fast finality, low fees.
- Good for: User-facing bridge experience in checkout.

**Aggregator: Squid**
- Best for: Letting users bridge from any chain/token in one step.
- Widget or API integration.

### Recommended Orchestration Strategy

**Bridge (Stripe Company)**
- Sardis already has MPP early access via Stripe. Bridge has a dedicated Tempo Integration Guide.
- Best for: Fiat-to-Tempo stablecoin flows, cross-border payments.

**Brale**
- If Sardis needs to issue its own stablecoin or handle complex treasury operations.
- Best for: Advanced stablecoin workflows.

### Tempo Chain Details (for integration)

- **Chain ID:** 4217 (based on Privy's `eip155:4217` CAIP-2 identifier)
- **Testnet RPC:** `https://rpc.moderato.tempo.xyz`
- **Block Explorer:** https://explore.tempo.xyz
- **Faucet:** https://docs.tempo.xyz/quickstart/faucet
- **Web Wallet:** https://wallet.tempo.xyz
- **GitHub:** https://github.com/tempoxyz
- **CLI Install:** `curl -fsSL https://tempo.xyz/install | bash`

### Quick Integration Checklist

1. [ ] Add Tempo chain config (chain ID 4217, RPC, explorer)
2. [ ] Test Turnkey `with-tempo` example for transaction signing
3. [ ] Integrate Stargate bridge for USDC funding from Base to Tempo
4. [ ] Evaluate embedded passkeys for checkout flow (domain-bound caveat)
5. [ ] Test CLI funding flow: `tempo wallet fund`
6. [ ] Explore Sponge/Enact for agentic wallet policies
7. [ ] Integrate Bridge (Stripe) for fiat-to-Tempo flows
8. [ ] Test MPP payment sessions for machine-to-machine payments

---

## Sources

All information sourced from official Tempo documentation at docs.tempo.xyz, accessed 2026-03-26:

- https://docs.tempo.xyz/ecosystem/wallets
- https://docs.tempo.xyz/ecosystem/orchestration
- https://docs.tempo.xyz/ecosystem/bridges
- https://docs.tempo.xyz/cli/wallet
- https://docs.tempo.xyz/guide/use-accounts/add-funds
- https://docs.tempo.xyz/guide/use-accounts/embed-passkeys
- https://docs.tempo.xyz/guide/getting-funds
