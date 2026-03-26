# CDP Production Readiness Checklist

Last updated: 2026-03-26

## Requirements from CDP Support (March 11 conversation)

### 1. Session Token Endpoint — AUTHENTICATED
- [x] **Status: PASS**
- Endpoint: `POST /wallets/{wallet_id}/onramp` (wallets.py:2143)
  - Protected by `require_principal` (bearer token auth)
  - Calls `_get_cdp_onramp_session_token()` which hits `POST api.developer.coinbase.com/onramp/v1/token`
  - Uses CDP Ed25519 JWT (`CDP_API_KEY_ID` + `CDP_API_KEY_SECRET`)
  - Returns `sessionToken` in the onramp URL
- Checkout flow: `POST /sessions/client/{client_secret}/onramp-token` (merchant_checkout.py:1056)
  - Session-scoped auth via `client_secret` + wallet address match
  - Same CDP JWT generation and `/onramp/v1/token` call

### 2. Direct Wallet Connection via SIGN Method
- [x] **Status: PASS**
- Checkout UI uses wagmi + EIP-712 typed data signing (ExternalWalletConnect.tsx)
- Flow: Connect wallet (Coinbase Wallet / WalletConnect) -> `signTypedDataAsync` -> verify on backend
- Backend: `POST /sessions/client/{client_secret}/connect-external` (merchant_checkout.py:619)
- No manual address paste — direct wallet connection + signature verification

### 3. Three Wallet Types Supported
- [x] **Status: PASS**
- **External wallets**: WalletConnect (MetaMask, Rainbow, 300+ wallets) + Coinbase Wallet / Smart Wallet
  - Configured in `wallet-config.ts` with `coinbaseWallet` and `walletConnect` connectors
  - `coinbaseWallet` preference `"all"` includes both browser extension AND passkey-based Smart Wallet
- **Embedded wallets**: Turnkey MPC wallets created server-side (`sardis_wallet/manager.py:427`)
  - Non-custodial — Turnkey holds encrypted key shares, Sardis never has raw keys
- **Managed wallets**: Agent wallets created via `POST /agents/{id}/wallet` → Turnkey MPC backing
  - Programmatic access with spending mandates and policy controls

### 4. Production/Staging Links for Testing
- [x] **Status: PASS**
- Landing: `sardis.sh`
- Dashboard: `app.sardis.sh` (Next.js 14)
- Checkout: `checkout.sardis.sh` (Vite React)
- API: `api.sardis.sh` (Cloud Run, `sardis-api-staging`)
- Guard dashboard: `guard-dashboard.sardis.sh`

### 5. Non-Custodial Model
- [x] **Status: PASS**
- Turnkey MPC custody: `sardis_wallet/turnkey_client.py` ("non-custodial wallet operations")
- `sardis_wallet/manager.py:427`: "Create a non-custodial MPC wallet via Turnkey"
- Architecture: Turnkey holds encrypted key shares using secure enclaves; Sardis API has signing authority but never possesses raw private keys
- Users can export keys from Turnkey at any time

### 6. Funds Flow: Fiat -> Wallet -> Purchases (Not Direct)
- [x] **Status: PASS**
- Onramp flow: User initiates onramp → Coinbase widget → USDC lands in user's wallet → user spends from wallet
- Checkout flow: FundAndPay component → onramp token → fund wallet → then `confirm-external-payment` for merchant payment
- USDC always goes to the user's wallet address first, not directly to a merchant

## Additional Requirements

### CDP API Configuration
- [x] `CDP_API_KEY_ID` env var configured on Cloud Run
- [x] `CDP_API_KEY_SECRET` env var configured on Cloud Run
- [ ] **Share API Key ID with CDP Support** — required for their allowlisting

### Mainnet Readiness
- [x] USDC contract address for Base mainnet: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- [x] Testnet (Base Sepolia) USDC: `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
- [x] Chain switching via `VITE_CHAIN` env var (checkout) and `SARDIS_CHECKOUT_CHAIN` (API)
- [ ] **Request mainnet onramp approval from CDP Support**

### Error Handling
- [x] CDP token generation failure returns HTTP 502 with descriptive error
- [x] Empty session token from CDP returns HTTP 502
- [x] Wallet address mismatch returns HTTP 400
- [x] Missing CDP credentials returns HTTP 500

## Code References

| Requirement | File | Line |
|---|---|---|
| CDP JWT generation (wallets) | `packages/sardis-api/src/sardis_api/routers/wallets.py` | 2040-2093 |
| CDP session token fetch | `packages/sardis-api/src/sardis_api/routers/wallets.py` | 2096-2140 |
| Onramp URL generation | `packages/sardis-api/src/sardis_api/routers/wallets.py` | 2143-2228 |
| Checkout onramp token | `packages/sardis-api/src/sardis_api/routers/merchant_checkout.py` | 1015-1129 |
| Wallet connection (frontend) | `packages/sardis-checkout-ui/src/components/ExternalWalletConnect.tsx` | Full file |
| Wagmi config | `packages/sardis-checkout-ui/src/lib/wallet-config.ts` | Full file |
| Turnkey MPC client | `packages/sardis-wallet/src/sardis_wallet/turnkey_client.py` | Full file |
| Non-custodial wallet creation | `packages/sardis-wallet/src/sardis_wallet/manager.py` | 427-475 |
