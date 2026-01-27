/**
 * Sardis Onramper Integration
 *
 * Onramper is a fiat on-ramp aggregator that provides access to
 * 100+ payment providers (Moonpay, Transak, Ramp, Simplex, etc.)
 * through a single API/widget integration.
 *
 * @see https://docs.onramper.com
 */

import { RampError } from './errors'

// =============================================================================
// Types
// =============================================================================

export interface OnramperConfig {
  /** Onramper API key */
  apiKey: string
  /** Sardis API key for wallet operations */
  sardisKey: string
  /** Environment mode */
  mode?: 'sandbox' | 'production'
  /** Custom Sardis API URL */
  sardisUrl?: string
  /** Default fiat currency */
  defaultFiat?: string
  /** Default crypto */
  defaultCrypto?: string
}

export interface OnramperQuote {
  id: string
  provider: string
  providerLogo?: string
  sourceAmount: number
  sourceCurrency: string
  destinationAmount: number
  destinationCurrency: string
  rate: number
  fees: {
    network: number
    provider: number
    total: number
  }
  paymentMethod: string
  estimatedTime: string // e.g., "5-10 minutes"
  kycRequired: boolean
  expiresAt: string
}

export interface OnramperTransaction {
  id: string
  externalId?: string
  provider: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'expired'
  sourceAmount: number
  sourceCurrency: string
  destinationAmount: number
  destinationCurrency: string
  destinationAddress: string
  paymentMethod: string
  txHash?: string
  createdAt: string
  updatedAt: string
  completedAt?: string
  failureReason?: string
}

export interface OnramperWidgetOptions {
  /** Wallet address to receive crypto */
  walletAddress: string
  /** Network/chain */
  network?: string
  /** Fiat currency (default: USD) */
  fiatCurrency?: string
  /** Crypto currency (default: USDC) */
  cryptoCurrency?: string
  /** Fiat amount */
  fiatAmount?: number
  /** Crypto amount */
  cryptoAmount?: number
  /** Payment method filter */
  paymentMethod?: 'creditCard' | 'debitCard' | 'bankTransfer' | 'applePay' | 'googlePay'
  /** Color theme */
  color?: string
  /** Dark mode */
  darkMode?: boolean
  /** Supported providers filter */
  onlyProviders?: string[]
  /** Excluded providers */
  excludeProviders?: string[]
  /** Country filter (ISO 3166-1 alpha-2) */
  country?: string
  /** Language */
  language?: string
  /** Skip KYC intro */
  skipIntro?: boolean
  /** Redirect URL after completion */
  redirectUrl?: string
  /** Partner context for tracking */
  partnerContext?: string
}

export interface SupportedAsset {
  code: string
  name: string
  network: string
  symbol: string
  decimals: number
  minAmount: number
  maxAmount: number
}

export interface SupportedFiat {
  code: string
  name: string
  symbol: string
  minAmount: number
  maxAmount: number
}

// =============================================================================
// Onramper Client
// =============================================================================

const ONRAMPER_API_URL = 'https://api.onramper.com'
const ONRAMPER_WIDGET_URL = 'https://buy.onramper.com'
const DEFAULT_SARDIS_API_URL = 'https://api.sardis.sh/v2'

export class SardisOnramper {
  private readonly apiKey: string
  private readonly sardisKey: string
  private readonly sardisUrl: string
  private readonly mode: 'sandbox' | 'production'
  private readonly defaultFiat: string
  private readonly defaultCrypto: string

  constructor(config: OnramperConfig) {
    if (!config.apiKey || config.apiKey.trim() === '') {
      throw new RampError('Onramper API key is required', 'INVALID_CONFIG')
    }
    if (!config.sardisKey || config.sardisKey.trim() === '') {
      throw new RampError('Sardis API key is required', 'INVALID_CONFIG')
    }

    this.apiKey = config.apiKey
    this.sardisKey = config.sardisKey
    this.sardisUrl = config.sardisUrl ?? DEFAULT_SARDIS_API_URL
    this.mode = config.mode ?? 'sandbox'
    this.defaultFiat = config.defaultFiat ?? 'USD'
    this.defaultCrypto = config.defaultCrypto ?? 'USDC'
  }

  // ===========================================================================
  // API Requests
  // ===========================================================================

  private async onramperRequest<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const response = await fetch(`${ONRAMPER_API_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new RampError(
        error.message || 'Onramper API error',
        error.code || 'ONRAMPER_ERROR',
        error
      )
    }

    return response.json()
  }

  private async sardisRequest<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const response = await fetch(`${this.sardisUrl}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${this.sardisKey}`,
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new RampError(
        error.message || 'Sardis API error',
        error.code || 'SARDIS_ERROR',
        error
      )
    }

    return response.json()
  }

  // ===========================================================================
  // Supported Assets
  // ===========================================================================

  /**
   * Get supported fiat currencies
   */
  async getSupportedFiats(): Promise<SupportedFiat[]> {
    const response = await this.onramperRequest<{
      fiats: Array<{
        code: string
        name: string
        symbol: string
        limits: { min: number; max: number }
      }>
    }>('GET', '/supported/fiats')

    return response.fiats.map((f) => ({
      code: f.code,
      name: f.name,
      symbol: f.symbol,
      minAmount: f.limits.min,
      maxAmount: f.limits.max,
    }))
  }

  /**
   * Get supported crypto assets
   */
  async getSupportedCryptos(network?: string): Promise<SupportedAsset[]> {
    const path = network
      ? `/supported/crypto?network=${encodeURIComponent(network)}`
      : '/supported/crypto'

    const response = await this.onramperRequest<{
      crypto: Array<{
        code: string
        name: string
        network: string
        symbol: string
        decimals: number
        limits: { min: number; max: number }
      }>
    }>('GET', path)

    return response.crypto.map((c) => ({
      code: c.code,
      name: c.name,
      network: c.network,
      symbol: c.symbol,
      decimals: c.decimals,
      minAmount: c.limits.min,
      maxAmount: c.limits.max,
    }))
  }

  /**
   * Get supported payment methods for a country
   */
  async getSupportedPaymentMethods(country: string): Promise<string[]> {
    const response = await this.onramperRequest<{
      paymentMethods: string[]
    }>('GET', `/supported/payment-methods?country=${encodeURIComponent(country)}`)

    return response.paymentMethods
  }

  // ===========================================================================
  // Quotes
  // ===========================================================================

  /**
   * Get quotes from all available providers
   */
  async getQuotes(params: {
    sourceCurrency: string
    destinationCurrency: string
    amount: number
    type?: 'fiat' | 'crypto' // Amount type: fiat amount or crypto amount
    paymentMethod?: string
    country?: string
    network?: string
  }): Promise<OnramperQuote[]> {
    const queryParams = new URLSearchParams({
      source: params.sourceCurrency,
      destination: params.destinationCurrency,
      amount: params.amount.toString(),
      type: params.type || 'fiat',
    })

    if (params.paymentMethod) {
      queryParams.set('paymentMethod', params.paymentMethod)
    }
    if (params.country) {
      queryParams.set('country', params.country)
    }
    if (params.network) {
      queryParams.set('network', params.network)
    }

    const response = await this.onramperRequest<{
      quotes: Array<{
        id: string
        provider: string
        providerLogo?: string
        sourceAmount: number
        sourceCurrency: string
        destinationAmount: number
        destinationCurrency: string
        rate: number
        fees: {
          network: number
          provider: number
          total: number
        }
        paymentMethod: string
        estimatedTime: string
        kycRequired: boolean
        expiresAt: string
      }>
    }>('GET', `/quotes?${queryParams.toString()}`)

    return response.quotes
  }

  /**
   * Get the best quote (lowest total cost)
   */
  async getBestQuote(params: {
    sourceCurrency: string
    destinationCurrency: string
    amount: number
    type?: 'fiat' | 'crypto'
    paymentMethod?: string
    country?: string
    network?: string
  }): Promise<OnramperQuote | null> {
    const quotes = await this.getQuotes(params)

    if (quotes.length === 0) {
      return null
    }

    // Sort by destination amount (highest = best value)
    return quotes.sort((a, b) => b.destinationAmount - a.destinationAmount)[0]
  }

  // ===========================================================================
  // Widget Integration
  // ===========================================================================

  /**
   * Generate widget URL for embedding or redirect
   *
   * @example
   * ```typescript
   * const url = onramper.getWidgetUrl({
   *   walletAddress: '0x...',
   *   fiatCurrency: 'USD',
   *   cryptoCurrency: 'USDC',
   *   fiatAmount: 100,
   *   network: 'base',
   * })
   * window.open(url, '_blank')
   * ```
   */
  getWidgetUrl(options: OnramperWidgetOptions): string {
    const params = new URLSearchParams()

    // Required
    params.set('apiKey', this.apiKey)
    params.set('walletAddress', options.walletAddress)

    // Defaults
    params.set('defaultFiat', options.fiatCurrency || this.defaultFiat)
    params.set('defaultCrypto', options.cryptoCurrency || this.defaultCrypto)

    // Optional amount
    if (options.fiatAmount) {
      params.set('fiatAmount', options.fiatAmount.toString())
    }
    if (options.cryptoAmount) {
      params.set('cryptoAmount', options.cryptoAmount.toString())
    }

    // Network mapping for Onramper
    if (options.network) {
      params.set('network', this.mapNetwork(options.network))
    }

    // Payment method
    if (options.paymentMethod) {
      params.set('paymentMethod', options.paymentMethod)
    }

    // Theming
    if (options.color) {
      params.set('color', options.color.replace('#', ''))
    }
    if (options.darkMode) {
      params.set('darkMode', 'true')
    }

    // Filters
    if (options.onlyProviders?.length) {
      params.set('onlyProviders', options.onlyProviders.join(','))
    }
    if (options.excludeProviders?.length) {
      params.set('excludeProviders', options.excludeProviders.join(','))
    }

    // Locale
    if (options.country) {
      params.set('country', options.country)
    }
    if (options.language) {
      params.set('language', options.language)
    }

    // Flow
    if (options.skipIntro) {
      params.set('skipIntro', 'true')
    }
    if (options.redirectUrl) {
      params.set('redirectUrl', options.redirectUrl)
    }
    if (options.partnerContext) {
      params.set('partnerContext', options.partnerContext)
    }

    // Mode
    if (this.mode === 'sandbox') {
      params.set('isTestMode', 'true')
    }

    return `${ONRAMPER_WIDGET_URL}?${params.toString()}`
  }

  /**
   * Generate widget HTML for iframe embedding
   */
  getWidgetIframe(options: OnramperWidgetOptions & { width?: string; height?: string }): string {
    const url = this.getWidgetUrl(options)
    const width = options.width || '400px'
    const height = options.height || '600px'

    return `<iframe
  src="${url}"
  width="${width}"
  height="${height}"
  frameborder="0"
  allow="accelerometer; autoplay; camera; gyroscope; payment"
  style="border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
></iframe>`
  }

  // ===========================================================================
  // Transaction Management
  // ===========================================================================

  /**
   * Get transaction status by Onramper transaction ID
   */
  async getTransaction(transactionId: string): Promise<OnramperTransaction> {
    return this.onramperRequest<OnramperTransaction>(
      'GET',
      `/transactions/${transactionId}`
    )
  }

  /**
   * List transactions for a wallet address
   */
  async listTransactions(
    walletAddress: string,
    options?: {
      limit?: number
      offset?: number
      status?: OnramperTransaction['status']
    }
  ): Promise<OnramperTransaction[]> {
    const params = new URLSearchParams({
      walletAddress,
    })

    if (options?.limit) {
      params.set('limit', options.limit.toString())
    }
    if (options?.offset) {
      params.set('offset', options.offset.toString())
    }
    if (options?.status) {
      params.set('status', options.status)
    }

    const response = await this.onramperRequest<{
      transactions: OnramperTransaction[]
    }>('GET', `/transactions?${params.toString()}`)

    return response.transactions
  }

  // ===========================================================================
  // Sardis Integration
  // ===========================================================================

  /**
   * Fund a Sardis wallet via Onramper widget
   *
   * Returns a widget URL that, when used, will deposit crypto
   * directly to the Sardis wallet.
   */
  async fundWallet(params: {
    walletId: string
    fiatAmount?: number
    fiatCurrency?: string
    cryptoCurrency?: string
    paymentMethod?: string
    redirectUrl?: string
  }): Promise<{
    widgetUrl: string
    walletAddress: string
    network: string
  }> {
    // Get wallet details from Sardis
    const wallet = await this.sardisRequest<{
      id: string
      address: string
      chain: string
    }>('GET', `/wallets/${params.walletId}`)

    const widgetUrl = this.getWidgetUrl({
      walletAddress: wallet.address,
      network: wallet.chain,
      fiatAmount: params.fiatAmount,
      fiatCurrency: params.fiatCurrency,
      cryptoCurrency: params.cryptoCurrency || 'USDC',
      paymentMethod: params.paymentMethod as OnramperWidgetOptions['paymentMethod'],
      redirectUrl: params.redirectUrl,
      partnerContext: `sardis:${wallet.id}`,
      darkMode: true,
      color: 'FF6B35', // Sardis orange
    })

    return {
      widgetUrl,
      walletAddress: wallet.address,
      network: wallet.chain,
    }
  }

  /**
   * Get best quote for funding a Sardis wallet
   */
  async getWalletFundingQuote(params: {
    walletId: string
    fiatAmount: number
    fiatCurrency?: string
    paymentMethod?: string
  }): Promise<OnramperQuote | null> {
    const wallet = await this.sardisRequest<{
      chain: string
    }>('GET', `/wallets/${params.walletId}`)

    return this.getBestQuote({
      sourceCurrency: params.fiatCurrency || this.defaultFiat,
      destinationCurrency: 'USDC',
      amount: params.fiatAmount,
      type: 'fiat',
      paymentMethod: params.paymentMethod,
      network: wallet.chain,
    })
  }

  // ===========================================================================
  // Webhooks
  // ===========================================================================

  /**
   * Verify webhook signature from Onramper
   */
  verifyWebhookSignature(payload: string, signature: string, secret: string): boolean {
    // Onramper uses HMAC-SHA256 for webhook signatures
    const crypto = require('crypto')
    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex')

    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    )
  }

  /**
   * Parse webhook payload
   */
  parseWebhookPayload(payload: string): {
    event: 'transaction.created' | 'transaction.completed' | 'transaction.failed'
    transaction: OnramperTransaction
  } {
    return JSON.parse(payload)
  }

  // ===========================================================================
  // Helpers
  // ===========================================================================

  private mapNetwork(chain: string): string {
    const mapping: Record<string, string> = {
      base: 'base',
      polygon: 'polygon',
      ethereum: 'ethereum',
      arbitrum: 'arbitrum',
      optimism: 'optimism',
      avalanche: 'avalanche',
      bsc: 'bsc',
      solana: 'solana',
    }
    return mapping[chain.toLowerCase()] || chain
  }
}

// =============================================================================
// Factory Function
// =============================================================================

export function createOnramper(config: OnramperConfig): SardisOnramper {
  return new SardisOnramper(config)
}
