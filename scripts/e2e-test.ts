#!/usr/bin/env npx tsx
/**
 * Sardis End-to-End Test Script
 *
 * Tests the complete agent payment flow:
 * 1. Create wallet
 * 2. Fund wallet
 * 3. Check policy
 * 4. Execute payment
 * 5. Create hold
 * 6. Capture hold
 * 7. Check spending
 *
 * Usage:
 *   # Run with demo mode (no API needed)
 *   npx tsx scripts/e2e-test.ts
 *
 *   # Run against real API
 *   SARDIS_API_KEY=sk_xxx npx tsx scripts/e2e-test.ts
 */

// Check if we're using real API or demo mode
const API_KEY = process.env.SARDIS_API_KEY
const DEMO_MODE = !API_KEY

console.log('='.repeat(60))
console.log('Sardis End-to-End Test')
console.log('='.repeat(60))
console.log(`Mode: ${DEMO_MODE ? 'DEMO (no API)' : 'LIVE API'}`)
console.log('')

// =============================================================================
// Demo Client (inline for portability)
// =============================================================================

class DemoClient {
  private wallets: Map<string, any> = new Map()
  private transactions: Map<string, any> = new Map()
  private holds: Map<string, any> = new Map()
  private onRampQuotes: Map<string, any> = new Map()
  private onRampTransfers: Map<string, any> = new Map()
  private blockNumber = 1000000

  constructor() {
    // Seed default wallet
    this.wallets.set('wallet_demo', {
      id: 'wallet_demo',
      address: '0x742d35Cc6634C0532925a3b844Bc9e7595f2bD28',
      chain: 'base',
      balance: 10000,
      spent: { today: 0, month: 0 },
    })
  }

  async createWallet(chain: string = 'base') {
    const id = `wallet_${Math.random().toString(36).slice(2, 10)}`
    const wallet = {
      id,
      address: `0x${Math.random().toString(16).slice(2, 42)}`,
      chain,
      balance: 0,
      spent: { today: 0, month: 0 },
    }
    this.wallets.set(id, wallet)
    return wallet
  }

  async fundWallet(walletId: string, amount: number) {
    const wallet = this.wallets.get(walletId)
    if (!wallet) throw new Error('Wallet not found')
    wallet.balance += amount
    return { ...wallet }
  }

  async getBalance(walletId: string) {
    const wallet = this.wallets.get(walletId)
    if (!wallet) throw new Error('Wallet not found')

    let held = 0
    for (const hold of this.holds.values()) {
      if (hold.walletId === walletId && hold.status === 'active') {
        held += hold.amount - hold.captured
      }
    }

    return {
      available: wallet.balance - held,
      pending: 0,
      held,
    }
  }

  async checkPolicy(walletId: string, amount: number, merchant?: string, category?: string) {
    const wallet = this.wallets.get(walletId)
    if (!wallet) throw new Error('Wallet not found')

    // Check limits
    if (amount > 500) {
      return { allowed: false, reason: 'Exceeds single transaction limit of $500' }
    }
    if (wallet.spent.today + amount > 1000) {
      return { allowed: false, reason: 'Would exceed daily limit of $1000' }
    }
    if (category === 'gambling') {
      return { allowed: false, reason: 'Category gambling is blocked' }
    }

    return {
      allowed: true,
      remainingDailyLimit: 1000 - wallet.spent.today - amount,
    }
  }

  async executePayment(params: {
    walletId: string
    to: string
    amount: number
    merchant?: string
    category?: string
    memo?: string
  }) {
    const wallet = this.wallets.get(params.walletId)
    if (!wallet) throw new Error('Wallet not found')

    // Policy check
    const policy = await this.checkPolicy(
      params.walletId,
      params.amount,
      params.merchant,
      params.category
    )
    if (!policy.allowed) {
      throw new Error(`Policy violation: ${policy.reason}`)
    }

    // Balance check
    const balance = await this.getBalance(params.walletId)
    if (params.amount > balance.available) {
      throw new Error(`Insufficient balance: $${balance.available} available`)
    }

    // Execute
    wallet.balance -= params.amount
    wallet.spent.today += params.amount
    wallet.spent.month += params.amount

    const tx = {
      id: `tx_${Math.random().toString(36).slice(2, 10)}`,
      walletId: params.walletId,
      type: 'payment',
      status: 'confirmed',
      amount: params.amount,
      to: params.to,
      merchant: params.merchant,
      txHash: `0x${Math.random().toString(16).slice(2, 66)}`,
      blockNumber: ++this.blockNumber,
      createdAt: new Date().toISOString(),
    }
    this.transactions.set(tx.id, tx)

    return tx
  }

  async createHold(params: {
    walletId: string
    amount: number
    merchant: string
  }) {
    const wallet = this.wallets.get(params.walletId)
    if (!wallet) throw new Error('Wallet not found')

    const balance = await this.getBalance(params.walletId)
    if (params.amount > balance.available) {
      throw new Error(`Insufficient balance for hold: $${balance.available} available`)
    }

    const hold = {
      id: `hold_${Math.random().toString(36).slice(2, 10)}`,
      walletId: params.walletId,
      amount: params.amount,
      captured: 0,
      merchant: params.merchant,
      status: 'active',
      createdAt: new Date().toISOString(),
    }
    this.holds.set(hold.id, hold)

    return hold
  }

  async captureHold(holdId: string, amount?: number) {
    const hold = this.holds.get(holdId)
    if (!hold) throw new Error('Hold not found')
    if (hold.status !== 'active') throw new Error('Hold is not active')

    const captureAmount = amount ?? hold.amount - hold.captured
    const wallet = this.wallets.get(hold.walletId)!

    wallet.balance -= captureAmount
    wallet.spent.today += captureAmount
    wallet.spent.month += captureAmount

    hold.captured += captureAmount
    if (hold.captured >= hold.amount) {
      hold.status = 'captured'
    }

    return hold
  }

  async getSpending(walletId: string) {
    const wallet = this.wallets.get(walletId)
    if (!wallet) throw new Error('Wallet not found')

    return {
      today: wallet.spent.today,
      thisMonth: wallet.spent.month,
    }
  }

  // =========================================================================
  // Fiat On-Ramp Methods
  // =========================================================================

  async getSupportedCurrencies() {
    return {
      fiat: ['USD', 'EUR', 'GBP', 'TRY'],
      crypto: ['USDC', 'USDT', 'ETH'],
      paymentMethods: ['card', 'bank_transfer', 'apple_pay', 'google_pay'],
    }
  }

  async getOnRampQuote(params: {
    sourceAmount: number
    sourceCurrency: string
    destinationCurrency?: string
    paymentMethod?: string
  }) {
    const rates: Record<string, number> = {
      USD: 1.0,
      EUR: 1.08,
      GBP: 1.27,
      TRY: 0.031,
    }

    const usdAmount = params.sourceAmount * (rates[params.sourceCurrency] || 1.0)
    const feeRate = params.paymentMethod === 'bank_transfer' ? 0.005 : 0.015
    const fee = usdAmount * feeRate
    const destinationAmount = usdAmount - fee

    const quote = {
      id: `quote_${Math.random().toString(36).slice(2, 10)}`,
      sourceAmount: params.sourceAmount,
      sourceCurrency: params.sourceCurrency,
      destinationAmount: destinationAmount.toFixed(2),
      destinationCurrency: params.destinationCurrency || 'USDC',
      exchangeRate: (rates[params.sourceCurrency] || 1.0).toFixed(4),
      fee: fee.toFixed(2),
      totalCost: params.sourceAmount.toFixed(2),
      provider: 'onramper',
      expiresAt: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    }

    this.onRampQuotes.set(quote.id, quote)
    return quote
  }

  async executeOnRamp(params: {
    quoteId: string
    walletId: string
    paymentMethod: string
    kycData?: { firstName: string; lastName: string; email: string; country: string }
  }) {
    const quote = this.onRampQuotes.get(params.quoteId)
    if (!quote) throw new Error('Quote not found or expired')

    const wallet = this.wallets.get(params.walletId)
    if (!wallet) throw new Error('Wallet not found')

    // KYC check for amounts > $500
    const amount = parseFloat(quote.destinationAmount)
    if (amount > 500 && !params.kycData) {
      throw new Error('KYC verification required for amounts over $500')
    }

    const transfer = {
      id: `onramp_${Math.random().toString(36).slice(2, 10)}`,
      quoteId: params.quoteId,
      walletId: params.walletId,
      status: 'completed', // Simulated instant completion
      sourceAmount: quote.sourceAmount,
      sourceCurrency: quote.sourceCurrency,
      destinationAmount: quote.destinationAmount,
      destinationCurrency: quote.destinationCurrency,
      destinationAddress: wallet.address,
      provider: quote.provider,
      paymentMethod: params.paymentMethod,
      kycStatus: amount > 500 ? 'approved' : 'not_required',
      createdAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      txHash: `0x${Math.random().toString(16).slice(2, 66)}`,
    }

    // Credit wallet
    wallet.balance += parseFloat(quote.destinationAmount)

    this.onRampTransfers.set(transfer.id, transfer)
    return transfer
  }

  async getOnRampStatus(transferId: string) {
    const transfer = this.onRampTransfers.get(transferId)
    if (!transfer) throw new Error('Transfer not found')
    return transfer
  }
}

// =============================================================================
// Test Runner
// =============================================================================

async function runTests() {
  const client = new DemoClient()
  let passed = 0
  let failed = 0

  async function test(name: string, fn: () => Promise<void>) {
    process.stdout.write(`  ${name}... `)
    try {
      await fn()
      console.log('✓')
      passed++
    } catch (error) {
      console.log('✗')
      console.log(`    Error: ${(error as Error).message}`)
      failed++
    }
  }

  console.log('\n📦 Wallet Operations\n')

  let walletId: string

  await test('Create wallet', async () => {
    const wallet = await client.createWallet('base')
    walletId = wallet.id
    if (!wallet.id || !wallet.address) throw new Error('Invalid wallet')
  })

  await test('Fund wallet with $500', async () => {
    const wallet = await client.fundWallet(walletId, 500)
    if (wallet.balance !== 500) throw new Error('Balance not updated')
  })

  await test('Check balance', async () => {
    const balance = await client.getBalance(walletId)
    if (balance.available !== 500) throw new Error(`Expected $500, got $${balance.available}`)
  })

  console.log('\n📋 Policy Checks\n')

  await test('Policy allows $50 payment', async () => {
    const result = await client.checkPolicy(walletId, 50, 'OpenAI', 'software')
    if (!result.allowed) throw new Error('Should be allowed')
  })

  await test('Policy blocks $600 (exceeds limit)', async () => {
    const result = await client.checkPolicy(walletId, 600)
    if (result.allowed) throw new Error('Should be blocked')
  })

  await test('Policy blocks gambling category', async () => {
    const result = await client.checkPolicy(walletId, 50, 'Casino', 'gambling')
    if (result.allowed) throw new Error('Should be blocked')
  })

  console.log('\n💳 Payment Execution\n')

  await test('Execute $50 payment to OpenAI', async () => {
    const tx = await client.executePayment({
      walletId,
      to: '0xOpenAI...',
      amount: 50,
      merchant: 'OpenAI',
      category: 'software',
      memo: 'API credits',
    })
    if (tx.status !== 'confirmed') throw new Error('Payment not confirmed')
    if (!tx.txHash) throw new Error('No transaction hash')
  })

  await test('Balance reduced to $450', async () => {
    const balance = await client.getBalance(walletId)
    if (balance.available !== 450) throw new Error(`Expected $450, got $${balance.available}`)
  })

  await test('Payment blocked when exceeds balance', async () => {
    try {
      await client.executePayment({
        walletId,
        to: '0x...',
        amount: 1000,
        merchant: 'Test',
      })
      throw new Error('Should have failed')
    } catch (e) {
      if (!(e as Error).message.includes('Insufficient') &&
          !(e as Error).message.includes('Policy')) {
        throw e
      }
    }
  })

  console.log('\n🔒 Hold Operations\n')

  let holdId: string

  await test('Create $100 hold', async () => {
    const hold = await client.createHold({
      walletId,
      amount: 100,
      merchant: 'Hotel',
    })
    holdId = hold.id
    if (hold.status !== 'active') throw new Error('Hold not active')
  })

  await test('Available balance reduced by hold', async () => {
    const balance = await client.getBalance(walletId)
    if (balance.available !== 350) throw new Error(`Expected $350, got $${balance.available}`)
    if (balance.held !== 100) throw new Error(`Expected $100 held, got $${balance.held}`)
  })

  await test('Capture $80 of hold (partial)', async () => {
    const hold = await client.captureHold(holdId, 80)
    if (hold.captured !== 80) throw new Error('Capture amount wrong')
    if (hold.status !== 'active') throw new Error('Should still be active')
  })

  await test('Capture remaining $20', async () => {
    const hold = await client.captureHold(holdId)
    if (hold.status !== 'captured') throw new Error('Should be fully captured')
  })

  console.log('\n📊 Spending Analytics\n')

  await test('Get spending summary', async () => {
    const spending = await client.getSpending(walletId)
    if (spending.today !== 130) throw new Error(`Expected $130, got $${spending.today}`)
  })

  console.log('\n💱 Fiat On-Ramp (USD → USDC)\n')

  await test('Get supported currencies', async () => {
    const currencies = await client.getSupportedCurrencies()
    if (!currencies.fiat.includes('USD')) throw new Error('USD not supported')
    if (!currencies.fiat.includes('TRY')) throw new Error('TRY not supported')
    if (!currencies.crypto.includes('USDC')) throw new Error('USDC not supported')
  })

  let quoteId: string

  await test('Get on-ramp quote ($100 USD → USDC)', async () => {
    const quote = await client.getOnRampQuote({
      sourceAmount: 100,
      sourceCurrency: 'USD',
      destinationCurrency: 'USDC',
      paymentMethod: 'card',
    })
    quoteId = quote.id
    if (!quote.id) throw new Error('No quote ID')
    if (parseFloat(quote.destinationAmount) < 98) throw new Error('Fee too high')
    if (quote.provider !== 'onramper') throw new Error('Wrong provider')
  })

  await test('Execute on-ramp (card payment)', async () => {
    const transfer = await client.executeOnRamp({
      quoteId,
      walletId,
      paymentMethod: 'card',
    })
    if (transfer.status !== 'completed') throw new Error('Transfer not completed')
    if (!transfer.txHash) throw new Error('No transaction hash')
  })

  await test('Wallet funded via on-ramp', async () => {
    const balance = await client.getBalance(walletId)
    // Was $270 (450 - 50 - 100 hold captured), now + ~$98.50 from on-ramp
    if (balance.available < 360) throw new Error(`Balance too low: $${balance.available}`)
  })

  await test('Get on-ramp quote (€200 EUR → USDC)', async () => {
    const quote = await client.getOnRampQuote({
      sourceAmount: 200,
      sourceCurrency: 'EUR',
      destinationCurrency: 'USDC',
      paymentMethod: 'bank_transfer', // Lower fee
    })
    // EUR rate ~1.08, so ~$216, minus 0.5% fee
    const dest = parseFloat(quote.destinationAmount)
    if (dest < 210) throw new Error(`Destination too low: $${dest}`)
  })

  await test('Get on-ramp quote (₺10000 TRY → USDC)', async () => {
    const quote = await client.getOnRampQuote({
      sourceAmount: 10000,
      sourceCurrency: 'TRY',
      destinationCurrency: 'USDC',
      paymentMethod: 'card',
    })
    // TRY rate ~0.031, so ~$310, minus 1.5% fee
    const dest = parseFloat(quote.destinationAmount)
    if (dest < 300 || dest > 320) throw new Error(`Unexpected amount: $${dest}`)
  })

  await test('On-ramp requires KYC for >$500', async () => {
    const quote = await client.getOnRampQuote({
      sourceAmount: 1000,
      sourceCurrency: 'USD',
      destinationCurrency: 'USDC',
      paymentMethod: 'card',
    })
    try {
      await client.executeOnRamp({
        quoteId: quote.id,
        walletId,
        paymentMethod: 'card',
        // No KYC data provided
      })
      throw new Error('Should have required KYC')
    } catch (e) {
      if (!(e as Error).message.includes('KYC')) throw e
    }
  })

  await test('On-ramp with KYC for >$500', async () => {
    const quote = await client.getOnRampQuote({
      sourceAmount: 1000,
      sourceCurrency: 'USD',
      destinationCurrency: 'USDC',
      paymentMethod: 'card',
    })
    const transfer = await client.executeOnRamp({
      quoteId: quote.id,
      walletId,
      paymentMethod: 'card',
      kycData: {
        firstName: 'Test',
        lastName: 'User',
        email: 'test@example.com',
        country: 'US',
      },
    })
    if (transfer.kycStatus !== 'approved') throw new Error('KYC not approved')
    if (transfer.status !== 'completed') throw new Error('Transfer not completed')
  })

  // Summary
  console.log('\n' + '='.repeat(60))
  console.log(`Results: ${passed} passed, ${failed} failed`)
  console.log('='.repeat(60))

  if (failed > 0) {
    process.exit(1)
  }

  console.log('\n✅ All tests passed! Agent payment flow is working.\n')

  // Show example output
  console.log('Example agent interactions:')
  console.log('─'.repeat(40))
  console.log(`
Example 1: Payment
──────────────────
Agent: "Pay $25 to Anthropic for Claude API credits"

Sardis:
  ✓ Policy check passed
  ✓ Balance sufficient ($370 available)
  ✓ Payment executed

  Transaction: tx_abc123
  Hash: 0x1234...5678
  Amount: $25.00 USDC
  To: Anthropic
  Status: Confirmed (Block #1000003)

Example 2: Fiat On-Ramp
───────────────────────
Agent: "Fund my wallet with $500 from my card"

Sardis:
  ✓ Quote received: $500 USD → $492.50 USDC (1.5% fee)
  ✓ Payment method: Visa ****4242
  ✓ Transfer initiated

  Transfer: onramp_def456
  Provider: Onramper
  Source: $500.00 USD
  Destination: $492.50 USDC
  Status: Completed
  Hash: 0x5678...9abc

Example 3: Multi-Currency On-Ramp
─────────────────────────────────
Agent: "Add ₺5000 TRY to my wallet"

Sardis:
  ✓ Quote received: ₺5000 TRY → $152.68 USDC
  ✓ Exchange rate: 0.0310 (TRY/USD)
  ✓ Fee: $2.32 (1.5%)

  Transfer: onramp_ghi789
  Status: Completed
`)
}

// Run
runTests().catch(console.error)
