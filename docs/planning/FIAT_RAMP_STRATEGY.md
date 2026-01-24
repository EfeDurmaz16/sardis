# Sardis Fiat On/Off Ramp Strategy

## Problem

Sardis currently supports 5 chains (Base, Polygon, ETH, Arbitrum, Optimism) but all are crypto-only. For mainstream user and enterprise adoption:

- Users cannot fund directly from bank accounts
- When agents make payments, merchants should receive USD
- Withdrawals should go to bank accounts

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 SARDIS + Fiat Rails                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                      END USER                               │
│                         │                                   │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│   │   Bank    │  │   Card    │  │  Crypto   │              │
│   │  (ACH)    │  │ (Stripe)  │  │  (USDC)   │              │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘              │
│         │              │              │                     │
│         └──────────────┼──────────────┘                     │
│                        ▼                                    │
│              ┌─────────────────┐                            │
│              │     BRIDGE      │  ← Fiat ↔ Crypto           │
│              │   (by Stripe)   │    Settlement layer        │
│              └────────┬────────┘                            │
│                       │                                     │
│                       ▼                                     │
│              ┌─────────────────┐                            │
│              │     SARDIS      │  ← Policy enforcement      │
│              │     WALLET      │    MPC custody             │
│              │     (USDC)      │    Natural language rules  │
│              └────────┬────────┘                            │
│                       │                                     │
│         ┌─────────────┼─────────────┐                       │
│         ▼             ▼             ▼                       │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐                │
│   │  Crypto   │ │  Virtual  │ │   Fiat    │                │
│   │  Payout   │ │   Card    │ │  Payout   │                │
│   │  (USDC)   │ │ (Lithic)  │ │ (Bridge)  │                │
│   └───────────┘ └───────────┘ └───────────┘                │
│        │             │              │                       │
│        ▼             ▼              ▼                       │
│   On-chain       Anywhere       Merchant                    │
│   merchants      cards work     bank acct                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Ramp Provider Comparison

| Provider | On-Ramp | Off-Ramp | Fee | Settlement | API Quality |
|----------|---------|----------|-----|------------|-------------|
| Bridge (Stripe) | ✅ | ✅ | 0.5-1% | Instant | ⭐⭐⭐⭐⭐ |
| Circle Mint | ✅ | ✅ | 0.1% | 1-2 day | ⭐⭐⭐⭐ |
| MoonPay | ✅ | ✅ | 1-4.5% | Instant | ⭐⭐⭐ |
| Coinbase Prime | ✅ | ✅ | 0.5% | Same day | ⭐⭐⭐⭐ |
| Zero Hash | ✅ | ✅ | Custom | Instant | ⭐⭐⭐⭐ |

### Recommendation: Bridge (by Stripe)

- Lowest friction (Stripe trust)
- Instant settlement
- Enterprise-grade compliance
- Excellent API

## Implementation

### Python SDK

```python
# sardis/ramp/bridge.py
from bridge_sdk import Bridge
from sardis import Sardis

class SardisFiatRamp:
    def __init__(self):
        self.bridge = Bridge(api_key=os.environ["BRIDGE_API_KEY"])
        self.sardis = Sardis(api_key=os.environ["SARDIS_API_KEY"])

    async def fund_wallet(
        self,
        wallet_id: str,
        amount_usd: float,
        source: Literal["bank", "card", "crypto"]
    ) -> FundingResult:
        """Fiat → Sardis Wallet"""

        wallet = await self.sardis.wallets.get(wallet_id)

        if source == "crypto":
            # Direct USDC deposit
            return FundingResult(
                deposit_address=wallet.address,
                chain=wallet.chain,
                token="USDC"
            )

        # Fiat → USDC via Bridge
        transfer = await self.bridge.transfers.create(
            amount=amount_usd,
            source_currency="USD",
            destination_currency="USDC",
            destination_address=wallet.address,
            destination_chain=wallet.chain,
            payment_method=source  # "bank" or "card"
        )

        return FundingResult(
            payment_link=transfer.hosted_url,
            ach_instructions=transfer.ach_details,
            wire_instructions=transfer.wire_details,
            estimated_arrival=transfer.eta,
            fee_percent=transfer.fee_percent
        )

    async def withdraw_to_bank(
        self,
        wallet_id: str,
        amount_usd: float,
        bank_account: BankAccount
    ) -> WithdrawalResult:
        """Sardis Wallet → Bank Account"""

        wallet = await self.sardis.wallets.get(wallet_id)

        # 1. Policy check
        check = await wallet.check_policy(
            amount=str(amount_usd),
            action="withdrawal"
        )
        if not check.allowed:
            raise PolicyViolation(check.reason)

        # 2. Get Bridge deposit address
        bridge_address = await self.bridge.get_deposit_address(
            chain=wallet.chain,
            currency="USDC"
        )

        # 3. Send USDC to Bridge
        tx = await wallet.pay(
            to=bridge_address,
            amount=str(amount_usd),
            token="USDC",
            memo="Withdrawal to bank"
        )

        # 4. Bridge sends USD to bank
        payout = await self.bridge.payouts.create(
            amount=amount_usd,
            currency="USD",
            destination=bank_account,
            source_tx=tx.tx_hash
        )

        return WithdrawalResult(
            tx_hash=tx.tx_hash,
            payout_id=payout.id,
            estimated_arrival=payout.eta,
            fee=payout.fee
        )

    async def pay_merchant_fiat(
        self,
        wallet_id: str,
        amount_usd: float,
        merchant: MerchantAccount
    ) -> PaymentResult:
        """Agent pays, merchant receives USD"""

        wallet = await self.sardis.wallets.get(wallet_id)

        # Policy check
        check = await wallet.check_policy(
            amount=str(amount_usd),
            merchant=merchant.name
        )
        if not check.allowed:
            raise PolicyViolation(check.reason)

        if check.requires_approval:
            return PaymentResult(
                status="pending_approval",
                approval_request=await wallet.request_approval(
                    amount=str(amount_usd),
                    reason=f"Payment to {merchant.name}"
                )
            )

        # Pay via Bridge (instant USD to merchant)
        payment = await self.bridge.payments.create(
            amount=amount_usd,
            source_wallet=wallet.address,
            source_chain=wallet.chain,
            destination=merchant.bank_account,
            destination_currency="USD"
        )

        return PaymentResult(
            status="completed",
            payment_id=payment.id,
            merchant_received=amount_usd,
            fee=payment.fee
        )
```

### TypeScript SDK

```typescript
// @sardis/fiat-ramp
import { Bridge } from '@bridge-xyz/sdk'
import { Sardis, Wallet } from '@sardis/sdk'

export class SardisFiatRamp {
  private bridge: Bridge
  private sardis: Sardis

  constructor(config: { sardisKey: string; bridgeKey: string }) {
    this.sardis = new Sardis({ apiKey: config.sardisKey })
    this.bridge = new Bridge({ apiKey: config.bridgeKey })
  }

  async fundWallet(params: {
    walletId: string
    amountUsd: number
    method: 'bank' | 'card' | 'crypto'
  }): Promise<FundingResult> {
    const wallet = await this.sardis.wallets.get(params.walletId)

    if (params.method === 'crypto') {
      return {
        type: 'crypto',
        depositAddress: wallet.address,
        chain: wallet.chain,
        token: 'USDC'
      }
    }

    const transfer = await this.bridge.transfers.create({
      amount: params.amountUsd,
      sourceCurrency: 'USD',
      destinationCurrency: 'USDC',
      destinationAddress: wallet.address,
      destinationChain: wallet.chain
    })

    return {
      type: 'fiat',
      paymentLink: transfer.hostedUrl,
      achInstructions: transfer.achDetails,
      eta: transfer.eta
    }
  }

  async withdrawToBank(params: {
    walletId: string
    amountUsd: number
    bankAccount: BankAccount
  }): Promise<WithdrawalResult> {
    const wallet = await this.sardis.wallets.get(params.walletId)

    // Policy check
    const check = await wallet.checkPolicy({
      amount: params.amountUsd.toString(),
      action: 'withdrawal'
    })

    if (!check.allowed) {
      throw new PolicyViolation(check.reason)
    }

    // Get Bridge deposit address
    const bridgeAddress = await this.bridge.getDepositAddress({
      chain: wallet.chain,
      currency: 'USDC'
    })

    // Send USDC to Bridge
    const tx = await wallet.pay({
      to: bridgeAddress,
      amount: params.amountUsd.toString(),
      token: 'USDC',
      memo: 'Withdrawal to bank'
    })

    // Bridge sends USD to bank
    const payout = await this.bridge.payouts.create({
      amount: params.amountUsd,
      currency: 'USD',
      destination: params.bankAccount,
      sourceTx: tx.txHash
    })

    return {
      txHash: tx.txHash,
      payoutId: payout.id,
      eta: payout.eta,
      fee: payout.fee
    }
  }
}
```

---

## Business Model

### Current Revenue Streams

| Stream | Rate | Notes |
|--------|------|-------|
| Transaction fee | 0.5-1.5% | Per payment |
| Virtual card fee | $2-5/card | Monthly per active card |
| Enterprise tier | $500+/mo | Custom policies, SLA |
| Float income | ~4-5% APY | On wallet balances |
| Card interchange | 0.5-1% | Revenue share w/ Lithic |

### New Revenue with Fiat Ramp

| Stream | Rate | Notes |
|--------|------|-------|
| On-ramp fee | 1-2% | Fiat → Wallet (margin over Bridge's 0.5%) |
| Off-ramp fee | 1% | Wallet → Bank |
| Instant settlement | +0.5% | Premium for instant |
| FX conversion | 1-2% | USD → EUR, etc. |
| Wire transfer | $15 flat | International wires |

### Unit Economics Projection

```
Scenario: 10,000 wallets, $500 avg monthly volume

                          Without Fiat    With Fiat Ramp
                          ────────────    ──────────────
Active wallets            10,000          25,000
                                          (mainstream users)

Avg monthly volume        $500            $750
                                          (lower friction)

Transaction fees          $37,500/mo      $140,625/mo
(0.75% avg)

On-ramp fees (1.5%)       $0              $56,250/mo

Off-ramp fees (1%)        $0              $18,750/mo

Virtual cards             $30,000/mo      $75,000/mo
($3/active card)

Float income              $16,667/mo      $41,667/mo
(4% APY)
                          ────────────    ──────────────
GROSS REVENUE             $84,167/mo      $332,292/mo
                                          (+295% increase)

Bridge/infra costs        -$10,000/mo     -$50,000/mo
                          ────────────    ──────────────
NET REVENUE               $74,167/mo      $282,292/mo
```

### Pricing Tiers

```
┌────────────────────────────────────────────────────────────┐
│                      SARDIS PRICING                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   Starter          Growth            Enterprise           │
│   Free             $49/mo            Custom               │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   ✓ 1 wallet       ✓ 10 wallets      ✓ Unlimited          │
│   ✓ $1K/mo volume  ✓ $50K/mo volume  ✓ Unlimited volume   │
│   ✓ 1.5% tx fee    ✓ 1% tx fee       ✓ 0.5% tx fee       │
│   ✓ Crypto only    ✓ Fiat on-ramp    ✓ Fiat on/off-ramp  │
│   ✗ Virtual cards  ✓ 5 cards         ✓ Unlimited cards   │
│   ✗ API access     ✓ Full API        ✓ Dedicated support │
│   Community        Email support     ✓ SLA guarantee     │
│   support                            ✓ Custom policies   │
│                                      ✓ SSO/SAML          │
│                                      ✓ Webhook callbacks │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Market Sizing

### TAM/SAM/SOM

```
TAM (Total Addressable Market)
AI Agent Economy by 2028                    $50B

SAM (Serviceable Addressable Market)
AI agents needing payment capabilities      $15B

SOM (Serviceable Obtainable Market)
Developer-focused, US/EU, 2026-2027        $500M

Sardis Target (5% of SOM)
                                           $25M ARR by 2027
```

### Competitive Positioning

```
                     Fiat Native ──────────────────► Crypto Native
                          │                              │
             ┌────────────┼──────────────────────────────┼─────┐
             │            │                              │     │
     Agent   │   Stripe   │                              │     │
     Focus   │   Connect  │         SARDIS              │     │
       │     │  (future?) │        ┌─────┐              │     │
       │     │            │        │█████│              │     │
       │     │            │        └─────┘              │     │
       │     │            │     + Fiat Ramp             │     │
       ▼     │            │                              │     │
             │  PayPal    │                        Coinbase│   │
    Generic  │  Plaid     │                        Commerce│   │
             │            │                              │     │
             └────────────┼──────────────────────────────┼─────┘
                          │                              │

Sardis + Fiat Ramp = Best of both worlds
- Crypto-native flexibility (programmable, global, instant)
- Fiat accessibility (mainstream users, enterprise)
```

---

## Go-to-Market with Fiat Ramp

### Phase 1: Developer Adoption (Q1-Q2)
- Free tier generous
- Excellent docs (llms.txt, llms-full.txt)
- MCP server for Claude/Cursor

### Phase 2: Fiat Ramp Launch (Q2-Q3)
- Bridge integration live
- Bank funding available
- Press release: "AI agents can now spend real dollars"

### Phase 3: Enterprise Push (Q3-Q4)
- SOC2 certification
- Enterprise tier with SLAs
- Dedicated account managers

### Phase 4: Platform Network Effects (2027)
- Agent-to-agent payments
- Marketplace for agent services
- Float-based yield products

---

*Last updated: January 2026*
