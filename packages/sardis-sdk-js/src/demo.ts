/**
 * Sardis Demo Mode
 *
 * A fully functional simulation of the Sardis API for:
 * - YC demos
 * - Local development
 * - Integration testing
 * - Hackathons
 *
 * No real transactions, no API key needed.
 *
 * @example
 * ```typescript
 * import { SardisDemoClient } from '@sardis/sdk/demo'
 *
 * const sardis = new SardisDemoClient()
 *
 * // Create a demo wallet
 * const wallet = await sardis.wallets.create({ chain: 'base' })
 *
 * // Make a demo payment
 * const payment = await sardis.payments.execute({
 *   walletId: wallet.id,
 *   to: 'demo_merchant_openai',
 *   amount: '50.00',
 *   token: 'USDC',
 * })
 *
 * console.log(payment.txHash) // 0x1234... (simulated)
 * ```
 */

import { randomBytes } from 'crypto'

// =============================================================================
// Types
// =============================================================================

interface DemoWallet {
  id: string
  address: string
  chain: string
  balance: string
  policy: DemoPolicy
  createdAt: string
}

interface DemoPolicy {
  id: string
  name: string
  dailyLimit: number
  monthlyLimit: number
  singleTxLimit: number
  blockedCategories: string[]
  allowedMerchants: string[] | null
  spent: {
    today: number
    thisMonth: number
  }
}

interface DemoTransaction {
  id: string
  walletId: string
  type: 'payment' | 'hold' | 'capture' | 'refund'
  status: 'pending' | 'confirmed' | 'failed'
  amount: string
  token: string
  chain: string
  from: string
  to: string
  merchant?: string
  category?: string
  txHash: string
  blockNumber: number
  memo?: string
  createdAt: string
  confirmedAt?: string
}

interface DemoHold {
  id: string
  walletId: string
  amount: string
  capturedAmount: string
  merchant: string
  status: 'active' | 'captured' | 'voided' | 'expired'
  expiresAt: string
  createdAt: string
}

interface PolicyCheckResult {
  allowed: boolean
  reason?: string
  remainingDailyLimit: number
  remainingMonthlyLimit: number
  requiresApproval: boolean
}

interface OnRampQuote {
  id: string
  sourceAmount: string
  sourceCurrency: string
  destinationAmount: string
  destinationCurrency: string
  exchangeRate: string
  fee: string
  totalCost: string
  expiresAt: string
  provider: string
}

interface OnRampTransfer {
  id: string
  quoteId: string
  walletId: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  sourceAmount: string
  sourceCurrency: string
  destinationAmount: string
  destinationCurrency: string
  destinationAddress: string
  provider: string
  paymentMethod: string
  kycStatus: 'not_required' | 'pending' | 'approved' | 'rejected'
  createdAt: string
  completedAt?: string
  txHash?: string
}

interface OffRampQuote {
  id: string
  sourceAmount: string
  sourceCurrency: string
  destinationAmount: string
  destinationCurrency: string
  exchangeRate: string
  fee: string
  netAmount: string
  expiresAt: string
  provider: string
}

interface OffRampTransfer {
  id: string
  quoteId: string
  walletId: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  sourceAmount: string
  sourceCurrency: string
  destinationAmount: string
  destinationCurrency: string
  bankAccount?: {
    last4: string
    bankName: string
  }
  provider: string
  createdAt: string
  completedAt?: string
  txHash?: string
}

// =============================================================================
// Demo Data Store
// =============================================================================

class DemoStore {
  wallets: Map<string, DemoWallet> = new Map()
  transactions: Map<string, DemoTransaction> = new Map()
  holds: Map<string, DemoHold> = new Map()
  onRampQuotes: Map<string, OnRampQuote> = new Map()
  onRampTransfers: Map<string, OnRampTransfer> = new Map()
  offRampQuotes: Map<string, OffRampQuote> = new Map()
  offRampTransfers: Map<string, OffRampTransfer> = new Map()
  blockNumber: number = 1000000

  constructor() {
    // Pre-populate with demo data
    this.seedData()
  }

  private seedData() {
    // Create default demo wallet
    const defaultWallet: DemoWallet = {
      id: 'wallet_demo_default',
      address: '0x742d35Cc6634C0532925a3b844Bc9e7595f2bD28',
      chain: 'base',
      balance: '10000.00',
      policy: {
        id: 'policy_demo_default',
        name: 'Demo Policy',
        dailyLimit: 1000,
        monthlyLimit: 10000,
        singleTxLimit: 500,
        blockedCategories: ['gambling', 'adult'],
        allowedMerchants: null,
        spent: { today: 0, thisMonth: 0 },
      },
      createdAt: new Date().toISOString(),
    }
    this.wallets.set(defaultWallet.id, defaultWallet)
  }

  generateId(prefix: string): string {
    return `${prefix}_${randomBytes(8).toString('hex')}`
  }

  generateTxHash(): string {
    return `0x${randomBytes(32).toString('hex')}`
  }

  generateAddress(): string {
    return `0x${randomBytes(20).toString('hex')}`
  }

  nextBlock(): number {
    return ++this.blockNumber
  }
}

// =============================================================================
// Demo Client
// =============================================================================

export class SardisDemoClient {
  private store: DemoStore
  private simulatedDelay: number

  wallets: DemoWalletsResource
  payments: DemoPaymentsResource
  holds: DemoHoldsResource
  policy: DemoPolicyResource
  ramp: DemoRampResource

  constructor(options?: { simulatedDelay?: number }) {
    this.store = new DemoStore()
    this.simulatedDelay = options?.simulatedDelay ?? 500

    this.wallets = new DemoWalletsResource(this.store, this.simulatedDelay)
    this.payments = new DemoPaymentsResource(this.store, this.simulatedDelay)
    this.holds = new DemoHoldsResource(this.store, this.simulatedDelay)
    this.policy = new DemoPolicyResource(this.store, this.simulatedDelay)
    this.ramp = new DemoRampResource(this.store, this.simulatedDelay)
  }

  /**
   * Get the default demo wallet ID.
   */
  get defaultWalletId(): string {
    return 'wallet_demo_default'
  }

  /**
   * Reset all demo data to initial state.
   */
  reset(): void {
    this.store = new DemoStore()
    this.wallets = new DemoWalletsResource(this.store, this.simulatedDelay)
    this.payments = new DemoPaymentsResource(this.store, this.simulatedDelay)
    this.holds = new DemoHoldsResource(this.store, this.simulatedDelay)
    this.policy = new DemoPolicyResource(this.store, this.simulatedDelay)
    this.ramp = new DemoRampResource(this.store, this.simulatedDelay)
  }
}

// =============================================================================
// Resources
// =============================================================================

class DemoWalletsResource {
  constructor(
    private store: DemoStore,
    private delay: number
  ) {}

  private async simulate<T>(result: T): Promise<T> {
    await new Promise((r) => setTimeout(r, this.delay))
    return result
  }

  async create(params: { chain?: string; policyId?: string }): Promise<DemoWallet> {
    const wallet: DemoWallet = {
      id: this.store.generateId('wallet'),
      address: this.store.generateAddress(),
      chain: params.chain || 'base',
      balance: '0.00',
      policy: {
        id: params.policyId || 'policy_demo_default',
        name: 'Demo Policy',
        dailyLimit: 1000,
        monthlyLimit: 10000,
        singleTxLimit: 500,
        blockedCategories: ['gambling', 'adult'],
        allowedMerchants: null,
        spent: { today: 0, thisMonth: 0 },
      },
      createdAt: new Date().toISOString(),
    }

    this.store.wallets.set(wallet.id, wallet)
    return this.simulate(wallet)
  }

  async get(walletId: string): Promise<DemoWallet> {
    const wallet = this.store.wallets.get(walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${walletId}`)
    }
    return this.simulate(wallet)
  }

  async getBalance(
    walletId: string
  ): Promise<{ available: string; pending: string; held: string }> {
    const wallet = await this.get(walletId)

    // Calculate held amount from active holds
    let held = 0
    for (const hold of this.store.holds.values()) {
      if (hold.walletId === walletId && hold.status === 'active') {
        held += parseFloat(hold.amount) - parseFloat(hold.capturedAmount)
      }
    }

    return this.simulate({
      available: (parseFloat(wallet.balance) - held).toFixed(2),
      pending: '0.00',
      held: held.toFixed(2),
    })
  }

  async list(): Promise<DemoWallet[]> {
    return this.simulate(Array.from(this.store.wallets.values()))
  }

  async fund(walletId: string, amount: string): Promise<DemoWallet> {
    const wallet = await this.get(walletId)
    wallet.balance = (parseFloat(wallet.balance) + parseFloat(amount)).toFixed(2)
    return this.simulate(wallet)
  }
}

class DemoPaymentsResource {
  constructor(
    private store: DemoStore,
    private delay: number
  ) {}

  private async simulate<T>(result: T): Promise<T> {
    await new Promise((r) => setTimeout(r, this.delay))
    return result
  }

  async execute(params: {
    walletId: string
    to: string
    amount: string
    token?: string
    chain?: string
    memo?: string
    merchant?: string
    category?: string
  }): Promise<DemoTransaction> {
    const wallet = this.store.wallets.get(params.walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${params.walletId}`)
    }

    const amount = parseFloat(params.amount)

    // Policy check
    const policy = wallet.policy
    if (amount > policy.singleTxLimit) {
      throw new Error(
        `Payment of $${amount} exceeds single transaction limit of $${policy.singleTxLimit}`
      )
    }
    if (policy.spent.today + amount > policy.dailyLimit) {
      throw new Error(
        `Payment would exceed daily limit. Remaining: $${policy.dailyLimit - policy.spent.today}`
      )
    }
    if (params.category && policy.blockedCategories.includes(params.category.toLowerCase())) {
      throw new Error(`Category '${params.category}' is blocked by policy`)
    }

    // Balance check
    if (amount > parseFloat(wallet.balance)) {
      throw new Error(
        `Insufficient balance. Available: $${wallet.balance}, Required: $${amount}`
      )
    }

    // Create transaction
    const tx: DemoTransaction = {
      id: this.store.generateId('tx'),
      walletId: params.walletId,
      type: 'payment',
      status: 'confirmed',
      amount: params.amount,
      token: params.token || 'USDC',
      chain: params.chain || wallet.chain,
      from: wallet.address,
      to: params.to,
      merchant: params.merchant,
      category: params.category,
      txHash: this.store.generateTxHash(),
      blockNumber: this.store.nextBlock(),
      memo: params.memo,
      createdAt: new Date().toISOString(),
      confirmedAt: new Date().toISOString(),
    }

    // Update wallet balance
    wallet.balance = (parseFloat(wallet.balance) - amount).toFixed(2)

    // Update spending
    policy.spent.today += amount
    policy.spent.thisMonth += amount

    this.store.transactions.set(tx.id, tx)
    return this.simulate(tx)
  }

  async get(transactionId: string): Promise<DemoTransaction> {
    const tx = this.store.transactions.get(transactionId)
    if (!tx) {
      throw new Error(`Transaction not found: ${transactionId}`)
    }
    return this.simulate(tx)
  }

  async list(walletId: string): Promise<DemoTransaction[]> {
    const transactions = Array.from(this.store.transactions.values()).filter(
      (tx) => tx.walletId === walletId
    )
    return this.simulate(transactions)
  }
}

class DemoHoldsResource {
  constructor(
    private store: DemoStore,
    private delay: number
  ) {}

  private async simulate<T>(result: T): Promise<T> {
    await new Promise((r) => setTimeout(r, this.delay))
    return result
  }

  async create(params: {
    walletId: string
    amount: string
    merchant: string
    expiresInHours?: number
    description?: string
  }): Promise<DemoHold> {
    const wallet = this.store.wallets.get(params.walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${params.walletId}`)
    }

    const amount = parseFloat(params.amount)

    // Balance check (including existing holds)
    let totalHeld = 0
    for (const hold of this.store.holds.values()) {
      if (hold.walletId === params.walletId && hold.status === 'active') {
        totalHeld += parseFloat(hold.amount) - parseFloat(hold.capturedAmount)
      }
    }

    const available = parseFloat(wallet.balance) - totalHeld
    if (amount > available) {
      throw new Error(
        `Insufficient available balance for hold. Available: $${available.toFixed(2)}`
      )
    }

    const expiresAt = new Date()
    expiresAt.setHours(expiresAt.getHours() + (params.expiresInHours || 24))

    const hold: DemoHold = {
      id: this.store.generateId('hold'),
      walletId: params.walletId,
      amount: params.amount,
      capturedAmount: '0.00',
      merchant: params.merchant,
      status: 'active',
      expiresAt: expiresAt.toISOString(),
      createdAt: new Date().toISOString(),
    }

    this.store.holds.set(hold.id, hold)
    return this.simulate(hold)
  }

  async capture(holdId: string, amount?: string): Promise<DemoHold> {
    const hold = this.store.holds.get(holdId)
    if (!hold) {
      throw new Error(`Hold not found: ${holdId}`)
    }
    if (hold.status !== 'active') {
      throw new Error(`Hold is not active: ${hold.status}`)
    }

    const captureAmount = amount ? parseFloat(amount) : parseFloat(hold.amount)
    const maxCapture = parseFloat(hold.amount) - parseFloat(hold.capturedAmount)

    if (captureAmount > maxCapture) {
      throw new Error(`Capture amount $${captureAmount} exceeds remaining hold $${maxCapture}`)
    }

    // Update wallet balance
    const wallet = this.store.wallets.get(hold.walletId)!
    wallet.balance = (parseFloat(wallet.balance) - captureAmount).toFixed(2)

    // Update hold
    hold.capturedAmount = (parseFloat(hold.capturedAmount) + captureAmount).toFixed(2)
    if (parseFloat(hold.capturedAmount) >= parseFloat(hold.amount)) {
      hold.status = 'captured'
    }

    // Create transaction
    const tx: DemoTransaction = {
      id: this.store.generateId('tx'),
      walletId: hold.walletId,
      type: 'capture',
      status: 'confirmed',
      amount: captureAmount.toFixed(2),
      token: 'USDC',
      chain: wallet.chain,
      from: wallet.address,
      to: hold.merchant,
      merchant: hold.merchant,
      txHash: this.store.generateTxHash(),
      blockNumber: this.store.nextBlock(),
      createdAt: new Date().toISOString(),
      confirmedAt: new Date().toISOString(),
    }
    this.store.transactions.set(tx.id, tx)

    return this.simulate(hold)
  }

  async void(holdId: string): Promise<DemoHold> {
    const hold = this.store.holds.get(holdId)
    if (!hold) {
      throw new Error(`Hold not found: ${holdId}`)
    }
    if (hold.status !== 'active') {
      throw new Error(`Hold is not active: ${hold.status}`)
    }

    hold.status = 'voided'
    return this.simulate(hold)
  }

  async get(holdId: string): Promise<DemoHold> {
    const hold = this.store.holds.get(holdId)
    if (!hold) {
      throw new Error(`Hold not found: ${holdId}`)
    }
    return this.simulate(hold)
  }

  async list(walletId: string): Promise<DemoHold[]> {
    const holds = Array.from(this.store.holds.values()).filter(
      (h) => h.walletId === walletId
    )
    return this.simulate(holds)
  }
}

class DemoPolicyResource {
  constructor(
    private store: DemoStore,
    private delay: number
  ) {}

  private async simulate<T>(result: T): Promise<T> {
    await new Promise((r) => setTimeout(r, this.delay))
    return result
  }

  async check(params: {
    walletId: string
    amount: string
    merchant?: string
    category?: string
  }): Promise<PolicyCheckResult> {
    const wallet = this.store.wallets.get(params.walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${params.walletId}`)
    }

    const amount = parseFloat(params.amount)
    const policy = wallet.policy

    // Check single transaction limit
    if (amount > policy.singleTxLimit) {
      return this.simulate({
        allowed: false,
        reason: `Amount $${amount} exceeds single transaction limit of $${policy.singleTxLimit}`,
        remainingDailyLimit: policy.dailyLimit - policy.spent.today,
        remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth,
        requiresApproval: false,
      })
    }

    // Check daily limit
    if (policy.spent.today + amount > policy.dailyLimit) {
      return this.simulate({
        allowed: false,
        reason: `Would exceed daily limit. Remaining: $${policy.dailyLimit - policy.spent.today}`,
        remainingDailyLimit: policy.dailyLimit - policy.spent.today,
        remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth,
        requiresApproval: false,
      })
    }

    // Check monthly limit
    if (policy.spent.thisMonth + amount > policy.monthlyLimit) {
      return this.simulate({
        allowed: false,
        reason: `Would exceed monthly limit. Remaining: $${policy.monthlyLimit - policy.spent.thisMonth}`,
        remainingDailyLimit: policy.dailyLimit - policy.spent.today,
        remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth,
        requiresApproval: false,
      })
    }

    // Check blocked categories
    if (params.category && policy.blockedCategories.includes(params.category.toLowerCase())) {
      return this.simulate({
        allowed: false,
        reason: `Category '${params.category}' is blocked by policy`,
        remainingDailyLimit: policy.dailyLimit - policy.spent.today,
        remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth,
        requiresApproval: false,
      })
    }

    // Check allowed merchants (if whitelist mode)
    if (policy.allowedMerchants && params.merchant) {
      if (!policy.allowedMerchants.includes(params.merchant.toLowerCase())) {
        return this.simulate({
          allowed: false,
          reason: `Merchant '${params.merchant}' is not in allowed list`,
          remainingDailyLimit: policy.dailyLimit - policy.spent.today,
          remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth,
          requiresApproval: false,
        })
      }
    }

    // All checks passed
    return this.simulate({
      allowed: true,
      remainingDailyLimit: policy.dailyLimit - policy.spent.today - amount,
      remainingMonthlyLimit: policy.monthlyLimit - policy.spent.thisMonth - amount,
      requiresApproval: amount > 250, // Require approval for >$250
    })
  }

  async getSpending(walletId: string): Promise<{
    today: number
    thisWeek: number
    thisMonth: number
    byCategory: Record<string, number>
    byMerchant: Record<string, number>
  }> {
    const wallet = this.store.wallets.get(walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${walletId}`)
    }

    const transactions = Array.from(this.store.transactions.values()).filter(
      (tx) => tx.walletId === walletId && tx.type === 'payment'
    )

    const byCategory: Record<string, number> = {}
    const byMerchant: Record<string, number> = {}

    for (const tx of transactions) {
      const amount = parseFloat(tx.amount)
      if (tx.category) {
        byCategory[tx.category] = (byCategory[tx.category] || 0) + amount
      }
      if (tx.merchant) {
        byMerchant[tx.merchant] = (byMerchant[tx.merchant] || 0) + amount
      }
    }

    return this.simulate({
      today: wallet.policy.spent.today,
      thisWeek: wallet.policy.spent.today * 3, // Simulated
      thisMonth: wallet.policy.spent.thisMonth,
      byCategory,
      byMerchant,
    })
  }
}

// =============================================================================
// Ramp Resource (Fiat On/Off Ramp)
// =============================================================================

class DemoRampResource {
  constructor(
    private store: DemoStore,
    private delay: number
  ) {}

  private async simulate<T>(result: T): Promise<T> {
    await new Promise((r) => setTimeout(r, this.delay))
    return result
  }

  /**
   * Get supported currencies for on-ramp
   */
  async getSupportedCurrencies(): Promise<{
    fiat: string[]
    crypto: string[]
    paymentMethods: string[]
  }> {
    return this.simulate({
      fiat: ['USD', 'EUR', 'GBP', 'TRY'],
      crypto: ['USDC', 'USDT', 'ETH'],
      paymentMethods: ['card', 'bank_transfer', 'apple_pay', 'google_pay'],
    })
  }

  /**
   * Get a quote for fiat -> crypto conversion
   */
  async getOnRampQuote(params: {
    sourceAmount: string
    sourceCurrency: string
    destinationCurrency?: string
    paymentMethod?: string
  }): Promise<OnRampQuote> {
    const sourceAmount = parseFloat(params.sourceAmount)
    const sourceCurrency = params.sourceCurrency.toUpperCase()
    const destCurrency = params.destinationCurrency?.toUpperCase() || 'USDC'

    // Simulated exchange rates (as of demo)
    const rates: Record<string, number> = {
      USD: 1.0,
      EUR: 1.08,
      GBP: 1.27,
      TRY: 0.031,
    }

    const usdAmount = sourceAmount * (rates[sourceCurrency] || 1.0)

    // Fee: 1.5% for cards, 0.5% for bank transfers
    const feeRate = params.paymentMethod === 'bank_transfer' ? 0.005 : 0.015
    const fee = usdAmount * feeRate
    const destinationAmount = (usdAmount - fee).toFixed(2)

    const expiresAt = new Date()
    expiresAt.setMinutes(expiresAt.getMinutes() + 5)

    const quote: OnRampQuote = {
      id: this.store.generateId('quote_on'),
      sourceAmount: params.sourceAmount,
      sourceCurrency,
      destinationAmount,
      destinationCurrency: destCurrency,
      exchangeRate: (rates[sourceCurrency] || 1.0).toFixed(4),
      fee: fee.toFixed(2),
      totalCost: sourceAmount.toFixed(2),
      expiresAt: expiresAt.toISOString(),
      provider: 'onramper', // Simulated provider
    }

    this.store.onRampQuotes.set(quote.id, quote)
    return this.simulate(quote)
  }

  /**
   * Execute on-ramp: fiat -> crypto to wallet
   */
  async executeOnRamp(params: {
    quoteId: string
    walletId: string
    paymentMethod: string
    kycData?: {
      firstName: string
      lastName: string
      email: string
      country: string
    }
  }): Promise<OnRampTransfer> {
    const quote = this.store.onRampQuotes.get(params.quoteId)
    if (!quote) {
      throw new Error(`Quote not found or expired: ${params.quoteId}`)
    }

    const wallet = this.store.wallets.get(params.walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${params.walletId}`)
    }

    // Check if quote expired
    if (new Date(quote.expiresAt) < new Date()) {
      throw new Error('Quote has expired. Please get a new quote.')
    }

    // Simulate KYC check for amounts > $500
    const amount = parseFloat(quote.destinationAmount)
    const kycRequired = amount > 500
    const kycStatus = kycRequired
      ? params.kycData
        ? 'approved'
        : 'pending'
      : 'not_required'

    if (kycRequired && !params.kycData) {
      throw new Error('KYC verification required for amounts over $500')
    }

    const transfer: OnRampTransfer = {
      id: this.store.generateId('onramp'),
      quoteId: params.quoteId,
      walletId: params.walletId,
      status: 'processing',
      sourceAmount: quote.sourceAmount,
      sourceCurrency: quote.sourceCurrency,
      destinationAmount: quote.destinationAmount,
      destinationCurrency: quote.destinationCurrency,
      destinationAddress: wallet.address,
      provider: quote.provider,
      paymentMethod: params.paymentMethod,
      kycStatus,
      createdAt: new Date().toISOString(),
    }

    this.store.onRampTransfers.set(transfer.id, transfer)

    // Simulate async completion (in real scenario, webhook would update)
    setTimeout(() => {
      const t = this.store.onRampTransfers.get(transfer.id)
      if (t && t.status === 'processing') {
        t.status = 'completed'
        t.completedAt = new Date().toISOString()
        t.txHash = this.store.generateTxHash()

        // Credit the wallet
        const w = this.store.wallets.get(params.walletId)
        if (w) {
          w.balance = (parseFloat(w.balance) + parseFloat(quote.destinationAmount)).toFixed(2)
        }
      }
    }, this.delay * 4) // Complete after 4x delay

    return this.simulate(transfer)
  }

  /**
   * Get on-ramp transfer status
   */
  async getOnRampStatus(transferId: string): Promise<OnRampTransfer> {
    const transfer = this.store.onRampTransfers.get(transferId)
    if (!transfer) {
      throw new Error(`Transfer not found: ${transferId}`)
    }
    return this.simulate(transfer)
  }

  /**
   * Get a quote for crypto -> fiat conversion (off-ramp)
   */
  async getOffRampQuote(params: {
    sourceAmount: string
    sourceCurrency?: string
    destinationCurrency: string
  }): Promise<OffRampQuote> {
    const sourceAmount = parseFloat(params.sourceAmount)
    const destCurrency = params.destinationCurrency.toUpperCase()

    // Simulated exchange rates
    const rates: Record<string, number> = {
      USD: 1.0,
      EUR: 0.92,
      GBP: 0.79,
      TRY: 32.5,
    }

    const destAmount = sourceAmount * (rates[destCurrency] || 1.0)

    // Fee: 1% for off-ramp
    const fee = sourceAmount * 0.01
    const netAmount = (destAmount - fee * (rates[destCurrency] || 1.0)).toFixed(2)

    const expiresAt = new Date()
    expiresAt.setMinutes(expiresAt.getMinutes() + 5)

    const quote: OffRampQuote = {
      id: this.store.generateId('quote_off'),
      sourceAmount: params.sourceAmount,
      sourceCurrency: params.sourceCurrency?.toUpperCase() || 'USDC',
      destinationAmount: destAmount.toFixed(2),
      destinationCurrency: destCurrency,
      exchangeRate: (rates[destCurrency] || 1.0).toFixed(4),
      fee: fee.toFixed(2),
      netAmount,
      expiresAt: expiresAt.toISOString(),
      provider: 'onramper',
    }

    this.store.offRampQuotes.set(quote.id, quote)
    return this.simulate(quote)
  }

  /**
   * Execute off-ramp: crypto -> fiat to bank account
   */
  async executeOffRamp(params: {
    quoteId: string
    walletId: string
    bankAccount: {
      accountNumber: string
      routingNumber?: string
      iban?: string
      bankName: string
    }
  }): Promise<OffRampTransfer> {
    const quote = this.store.offRampQuotes.get(params.quoteId)
    if (!quote) {
      throw new Error(`Quote not found or expired: ${params.quoteId}`)
    }

    const wallet = this.store.wallets.get(params.walletId)
    if (!wallet) {
      throw new Error(`Wallet not found: ${params.walletId}`)
    }

    // Check if quote expired
    if (new Date(quote.expiresAt) < new Date()) {
      throw new Error('Quote has expired. Please get a new quote.')
    }

    // Check balance
    const sourceAmount = parseFloat(quote.sourceAmount)
    if (sourceAmount > parseFloat(wallet.balance)) {
      throw new Error(
        `Insufficient balance. Available: $${wallet.balance}, Required: $${sourceAmount}`
      )
    }

    // Deduct from wallet immediately
    wallet.balance = (parseFloat(wallet.balance) - sourceAmount).toFixed(2)

    const transfer: OffRampTransfer = {
      id: this.store.generateId('offramp'),
      quoteId: params.quoteId,
      walletId: params.walletId,
      status: 'processing',
      sourceAmount: quote.sourceAmount,
      sourceCurrency: quote.sourceCurrency,
      destinationAmount: quote.netAmount,
      destinationCurrency: quote.destinationCurrency,
      bankAccount: {
        last4: params.bankAccount.accountNumber.slice(-4),
        bankName: params.bankAccount.bankName,
      },
      provider: quote.provider,
      createdAt: new Date().toISOString(),
      txHash: this.store.generateTxHash(),
    }

    this.store.offRampTransfers.set(transfer.id, transfer)

    // Simulate async completion
    setTimeout(() => {
      const t = this.store.offRampTransfers.get(transfer.id)
      if (t && t.status === 'processing') {
        t.status = 'completed'
        t.completedAt = new Date().toISOString()
      }
    }, this.delay * 6) // Bank transfers take longer

    return this.simulate(transfer)
  }

  /**
   * Get off-ramp transfer status
   */
  async getOffRampStatus(transferId: string): Promise<OffRampTransfer> {
    const transfer = this.store.offRampTransfers.get(transferId)
    if (!transfer) {
      throw new Error(`Transfer not found: ${transferId}`)
    }
    return this.simulate(transfer)
  }

  /**
   * List all ramp transfers for a wallet
   */
  async listTransfers(walletId: string): Promise<{
    onRamp: OnRampTransfer[]
    offRamp: OffRampTransfer[]
  }> {
    const onRamp = Array.from(this.store.onRampTransfers.values()).filter(
      (t) => t.walletId === walletId
    )
    const offRamp = Array.from(this.store.offRampTransfers.values()).filter(
      (t) => t.walletId === walletId
    )

    return this.simulate({ onRamp, offRamp })
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a demo client for testing without API.
 */
export function createDemoClient(options?: { simulatedDelay?: number }): SardisDemoClient {
  return new SardisDemoClient(options)
}
