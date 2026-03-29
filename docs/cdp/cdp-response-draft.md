# CDP Support Response Draft

**Date:** 2026-03-26
**Re:** Sardis — Coinbase Onramp Production Approval Request
**Last conversation:** March 11, 2026

---

Hi CDP Team,

Following up on our March 11 conversation. We have addressed all the requirements discussed and are requesting mainnet onramp approval.

## What Changed Since March 11

**1. Authenticated Session Token Endpoint**
Our onramp session token endpoint is fully authenticated. The `POST /wallets/{wallet_id}/onramp` endpoint requires bearer token authentication (`require_principal`). It generates a CDP Ed25519 JWT and calls `POST api.developer.coinbase.com/onramp/v1/token` server-side, then returns the `sessionToken` in the onramp URL. No raw API keys are exposed to the client.

**2. Direct Wallet Connection (Sign Method)**
We use wagmi with EIP-712 typed data signing for wallet verification. Users connect their wallet (Coinbase Wallet, WalletConnect, or Smart Wallet), sign a typed message, and the backend verifies the signature. No manual address paste.

**3. Three Wallet Types**
- **External wallets:** Coinbase Wallet (including passkey-based Smart Wallet) + WalletConnect (MetaMask, Rainbow, 300+ wallets)
- **Embedded wallets:** Turnkey MPC wallets — non-custodial, created server-side with encrypted key shares
- **Managed wallets:** Programmatic agent wallets with spending mandates and policy controls, also backed by Turnkey MPC

**4. Non-Custodial Architecture**
All wallets are backed by Turnkey MPC infrastructure. Sardis never possesses raw private keys. Users can export their keys from Turnkey at any time.

**5. Funds Flow**
Fiat onramp deposits go to the user's wallet first. Users then spend from their wallet balance. No direct-to-merchant flows bypass the wallet.

## Production URLs

- **Landing:** https://sardis.sh
- **Dashboard:** https://app.sardis.sh
- **API:** https://api.sardis.sh
- **Checkout:** https://checkout.sardis.sh

All environments are live and available for testing.

## Demo & Testing

- **Checkout demo:** https://checkout.sardis.sh/demo (creates test sessions, shows full onramp flow)
- **API Health:** https://api.sardis.sh/health (7/7 checks passing, v2.0.0)
- **API Docs:** https://api.sardis.sh/api/v2/docs (Swagger UI)
- **CDP API Key ID:** a4031ceb-814b-45e7-aee3-3c737b191c95

## CDP Embedded Wallets + Tempo

We noticed CDP Embedded Wallets now supports Tempo natively. We are very interested in integrating CDP Embedded Wallets alongside our existing Turnkey MPC infrastructure for a fully Coinbase-native experience on Tempo. This would give our users seamless fiat onramp directly to Tempo without bridging.

## Request

1. Please approve our application for **mainnet Coinbase Onramp** on Base (and Tempo if supported).
2. Our CDP API Key ID for allowlisting: `a4031ceb-814b-45e7-aee3-3c737b191c95`
3. We would also love to discuss CDP Embedded Wallets integration for Tempo-native wallets.
4. Happy to schedule a review call if needed.

Best regards,
Efe Baran Durmaz
Founder & CEO, Sardis Labs, Inc.
efe@sardis.sh | sardis.sh
