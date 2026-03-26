# CDP Embedded Wallets + Tempo Demo App Analysis

**Source:** https://github.com/coinbase/cdp-wallet-demo-apps/tree/main/apps/react-wagmi-tempo
**Date:** 2026-03-26
**Stack:** React 19.1, Vite, wagmi 2.17, viem 2.47, @coinbase/cdp-* 0.0.41

---

## 1. Wallet Creation on Tempo

### Chain Configuration

The demo uses `tempoModerato` from `viem/chains` (Tempo's testnet). The entire wagmi + CDP stack is wired to this single chain.

```ts
// src/config.ts
import { tempoModerato } from "viem/chains";

export const cdpConfig: Config = {
  projectId: import.meta.env.VITE_CDP_PROJECT_ID,
  ethereum: { createOnLogin: "eoa" },  // CRITICAL: no smart accounts on Tempo
  authMethods: ["email"],
  showCoinbaseFooter: true,
};

const connector = createCDPEmbeddedWalletConnector({
  cdpConfig,
  providerConfig: {
    chains: [tempoModerato],
    transports: { [tempoModerato.id]: http() },
  },
});

export const wagmiConfig = createConfig({
  connectors: [connector],
  chains: [tempoModerato],
  transports: { [tempoModerato.id]: http() },
});
```

### Key Findings

- **EOA only.** Tempo has native account abstraction and does NOT support ERC-4337 smart accounts. The `createOnLogin: "eoa"` setting is mandatory.
- **Single env var.** Only `VITE_CDP_PROJECT_ID` is needed. No API keys, no server-side secrets. The CDP Portal project ID enables everything.
- **Auto-provisioning.** CDP creates the EOA wallet automatically on first sign-in. No explicit `createWallet` call needed -- `useAccount()` returns the address after auth.
- **Auth is email-based.** `authMethods: ["email"]` triggers a Coinbase-hosted email OTP flow via `<AuthButton />`.

### Provider Stack (main.tsx)

```
CDPReactProvider (config + theme)
  -> WagmiProvider (wagmiConfig)
    -> QueryClientProvider (react-query)
      -> App
```

The `CDPReactProvider` wraps everything. It injects the CDP auth context and the embedded wallet signer. The wagmi provider sits inside it, consuming the CDP connector.

---

## 2. Wallet Funding

### No Programmatic Funding

The demo does NOT integrate FundButton, FundCard, Coinbase Onramp, or any on-chain faucet contract. Funding is entirely out-of-band:

- A link to the Tempo faucet docs is rendered in `Balances.tsx`:
  ```
  https://docs.tempo.xyz/quickstart/faucet?tab-1=fund-an-address
  ```
- Users must manually visit the faucet, paste their address, and request testnet tokens.

### Why No Native Funding

Tempo has **no native gas token**. All value is in ERC-20 stablecoins (pathUSD, AlphaUSD, BetaUSD, ThetaUSD). The standard CDP FundButton is designed around ETH funding on Base/Ethereum, so it does not apply. Tempo's gas model likely uses a paymaster or gasless approach (the demo's fallback gas values of `1000n` wei suggest gas is near-zero or subsidized).

### Comparison with Base Demo

The base `react-wagmi` app also has no automated funding -- it links to the CDP Base Sepolia faucet. Neither demo integrates Coinbase Onramp or FundButton.

---

## 3. Transaction Sending on Tempo

### Two-Step Sign-Then-Broadcast Pattern

This is the most architecturally significant difference from the standard wagmi flow. On standard chains, wagmi's `useSendTransaction` handles everything. On Tempo, the demo uses a manual two-step process:

**Step 1: Build and sign via CDP backend**
```ts
import { useSignEvmTransaction } from "@coinbase/cdp-hooks";

const { signEvmTransaction } = useSignEvmTransaction();

// Gather chain state in parallel
const [nonce, fees, gasLimit] = await Promise.all([
  tempoClient.getTransactionCount({ address: eoaAddress }),
  tempoClient.estimateFeesPerGas().catch(() => ({
    maxFeePerGas: 1000n,
    maxPriorityFeePerGas: 1000n,
  })),
  tempoClient.estimateGas({
    account: eoaAddress,
    to: selectedToken.address,
    data,
    value: 0n,
  }).catch(() => 60000n),
]);

// CDP signs the transaction server-side
const { signedTransaction } = await signEvmTransaction({
  evmAccount: eoaAddress,
  transaction: {
    to: selectedToken.address,
    value: 0n,
    data,           // ERC-20 transfer calldata
    chainId: tempoModerato.id,
    type: "eip1559",
    nonce,
    gas: gasLimit,
    maxFeePerGas: fees.maxFeePerGas ?? 1000n,
    maxPriorityFeePerGas: fees.maxPriorityFeePerGas ?? 1000n,
  },
});
```

**Step 2: Broadcast raw transaction via viem public client**
```ts
const hash = await tempoClient.sendRawTransaction({
  serializedTransaction: signedTransaction as Hex,
});

await tempoClient.waitForTransactionReceipt({ hash });
```

### Why Two Steps?

CDP Embedded Wallets keep the private key on Coinbase's servers. The `signEvmTransaction` hook sends the unsigned transaction to CDP's backend, which signs it and returns the serialized signed bytes. You then broadcast those bytes yourself via viem's `sendRawTransaction`. This is necessary because:

1. The wagmi connector's built-in `sendTransaction` may not properly support Tempo's RPC.
2. The two-step pattern gives full control over gas estimation, nonce management, and error handling.
3. It avoids relying on wagmi's internal provider for the broadcast step.

### Token Setup

Tempo pre-deploys stablecoins at deterministic addresses (all start with `0x20c0...`):

| Token    | Address                                      |
|----------|----------------------------------------------|
| pathUSD  | `0x20c0000000000000000000000000000000000000` |
| AlphaUSD | `0x20c0000000000000000000000000000000000001` |
| BetaUSD  | `0x20c0000000000000000000000000000000000002` |
| ThetaUSD | `0x20c0000000000000000000000000000000000003` |

All use 6 decimals. The demo sends $10 (10_000_000 raw units) of the selected token to the faucet address (`0x5bc1...`).

### Balance Reading

Balances are read via direct `readContract` calls on ERC-20 `balanceOf`, not via wagmi's `useBalance` hook (which checks native token balance). This is mandatory since Tempo has no native token.

```ts
const balance = await tempoClient.readContract({
  address: token.address,
  abi: ERC20_BALANCE_OF_ABI,
  functionName: "balanceOf",
  args: [address],
});
```

A 5-second polling interval refreshes balances automatically.

---

## 4. What Sardis Can Steal From This

### A. The Sign-Then-Broadcast Pattern for Agent Wallets

Sardis currently uses Turnkey MPC for wallet signing. The CDP `useSignEvmTransaction` + `sendRawTransaction` pattern is identical in spirit: sign server-side, broadcast client-side. This validates Sardis's architecture.

**Actionable:** The parallel gas estimation pattern (`Promise.all([nonce, fees, gasLimit])`) with `.catch()` fallbacks is clean and should be adopted for any checkout or agent transaction flow. Sardis's `chain_executor` should use this pattern.

### B. Multi-Token Balance Component

The `Balances.tsx` component -- iterating over a token list, calling `balanceOf` in parallel with `Promise.all`, formatting with `formatUnits` -- is a clean reusable pattern. Sardis's dashboard wallet view could use this for USDC + other stablecoins across chains.

### C. CDP Theme System

The `theme.ts` maps CDP component theme tokens to CSS custom properties. This is a clever bridge pattern: define your app's design system in CSS variables, then map them into CDP's theme interface. Sardis's monokrom grayscale theme could be adapted the same way if CDP components are ever used in the checkout UI.

### D. Minimal Auth Flow

The entire auth flow is one component: `<AuthButton />`. It handles sign-in, sign-out, and wallet creation in a single button. This is dramatically simpler than Sardis's current JWT + better-auth dual path.

### E. Error Message Parsing

The regex pattern for extracting clean error messages from viem errors is a nice touch:
```ts
errorMessage?.match(/Details:\s*(.+?)(?:\s*Version:|$)/s)?.[1]?.trim()
```

---

## 5. Integration Opportunity: CDP Embedded Wallets vs. Turnkey

### Current Sardis Wallet Stack

- **Turnkey MPC** -- server-side key management, API-key authenticated
- **Safe Smart Accounts v1.4.1** -- on-chain account abstraction
- **3-tier signing** -- Tempo access key + Turnkey MPC + EOA

### What CDP Embedded Wallets Offer

| Feature | Turnkey | CDP Embedded Wallets |
|---------|---------|---------------------|
| Key custody | Turnkey servers (MPC) | Coinbase servers |
| Auth model | API key + org/user hierarchy | CDP Project ID + email OTP |
| Smart accounts | Yes (Safe) | Yes (but NOT on Tempo) |
| Chains | Any EVM | Any EVM (including Tempo) |
| Frontend SDK | Custom integration | `@coinbase/cdp-react` + wagmi |
| Sign method | REST API | `useSignEvmTransaction` hook |
| Cost | Per-signature pricing | Free (included in CDP) |
| Compliance | Self-managed | Coinbase KYC/AML infrastructure |
| Recovery | Turnkey recovery flows | Coinbase account recovery |

### Recommendation: Dual Provider, Not Replacement

CDP Embedded Wallets should NOT replace Turnkey for Sardis's core agent infrastructure. Reasons:

1. **Agent wallets need programmatic signing.** CDP's `signEvmTransaction` works great in a browser context via hooks, but Sardis agents sign transactions server-side via Python. Turnkey's REST API is better suited for this.

2. **Smart account compatibility.** Sardis uses Safe accounts for policy enforcement (spending mandates, Zodiac Roles). CDP's EOA-only mode on Tempo means no on-chain policy enforcement there.

3. **Multi-chain control.** Sardis needs to control the same wallet across Base, Ethereum, Arbitrum, etc. with unified policy. Turnkey's organizational model supports this.

**Where CDP Embedded Wallets SHOULD be used:**

1. **Checkout payer wallets.** For the "Pay with Sardis" checkout flow, letting customers use CDP Embedded Wallets (email-based, no seed phrase) as a payment method would dramatically reduce friction. A customer signs in with email, gets a wallet, funds it via Coinbase Onramp, and pays -- all without ever seeing a private key.

2. **Dashboard personal wallets.** Sardis dashboard users who want a personal wallet (not an agent/business wallet) could use CDP Embedded Wallets as a simpler alternative to the full Turnkey + Safe stack.

3. **Tempo-specific flows.** If Sardis adds Tempo as a supported chain (which it should, given the MPP integration), CDP Embedded Wallets are the canonical way to create Tempo wallets.

### Integration Path

```
checkout-ui/
  -> Add @coinbase/cdp-react, @coinbase/cdp-wagmi, @coinbase/cdp-hooks
  -> Add "CDP Wallet" as a payment method alongside "External Wallet" and "Sardis Wallet"
  -> Config: createOnLogin: "eoa", chains: [base, tempoModerato]
  -> Use useSignEvmTransaction for USDC transfers from CDP wallet to merchant
```

The CDP SDK is ~200KB additional and requires only a project ID from the CDP Portal. No backend changes needed for the signing flow -- it all happens client-side via Coinbase's servers.

### Tempo-Specific Takeaways for Sardis

- Chain ID: `tempoModerato` from `viem/chains` (already in viem 2.47+)
- No native token -- gas is near-zero, all value in ERC-20s
- EOA only -- no ERC-4337 smart accounts
- Stablecoin addresses are deterministic (`0x20c0...00` through `0x20c0...03`)
- All stablecoins use 6 decimals (same as USDC)
- Block explorer: accessible via `tempoModerato.blockExplorers.default.url`

---

## File Inventory

| File | Purpose | Lines |
|------|---------|-------|
| `src/config.ts` | CDP + wagmi config, connector setup | 34 |
| `src/tempo.ts` | Viem public client for Tempo, faucet address | 19 |
| `src/tokens.ts` | Token registry (4 stablecoins) | 11 |
| `src/main.tsx` | Provider stack (CDP > Wagmi > ReactQuery) | 22 |
| `src/App.tsx` | Root component, auth state routing | 28 |
| `src/SignInScreen.tsx` | Email auth via AuthButton | 15 |
| `src/SignedInScreen.tsx` | Layout: Header + Balances + Transaction | 28 |
| `src/Balances.tsx` | ERC-20 balance polling via readContract | 126 |
| `src/Transaction.tsx` | Sign-then-broadcast ERC-20 transfer | 178 |
| `src/Header.tsx` | Address display + copy + sign out | 65 |
| `src/theme.ts` | CDP theme -> CSS variable mapping | 20 |
| `src/Icons.tsx` | SVG icon components | 66 |
| `src/Loading.tsx` | Loading spinner | 13 |
| `src/index.css` | Full app styles, dark mode support | 523 |
| `package.json` | Dependencies: cdp-* 0.0.41, wagmi 2.17 | 40 |

**Total:** ~1,200 lines across 15 source files. A minimal but complete reference implementation.
