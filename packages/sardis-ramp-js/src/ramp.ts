/**
 * Sardis Fiat Ramp - Bridge integration for fiat on/off ramp.
 */

import { PolicyViolation, RampError } from './errors'
import type {
  BankAccount,
  FundingMethod,
  FundingResult,
  MerchantAccount,
  PaymentResult,
  RampConfig,
  WithdrawalResult,
  Wallet,
  ACHDetails,
  WireDetails,
} from './types'

// Default API URLs - can be overridden via config for testing/custom deployments
const DEFAULT_BRIDGE_API_URL = 'https://api.bridge.xyz/v0'
const DEFAULT_BRIDGE_SANDBOX_URL = 'https://api.sandbox.bridge.xyz/v0'
const DEFAULT_SARDIS_API_URL = 'https://api.sardis.sh/v2'

export class SardisFiatRamp {
  private readonly sardisKey: string
  private readonly bridgeKey: string
  private readonly bridgeUrl: string
  private readonly sardisUrl: string

  constructor(config: RampConfig) {
    // Validate required keys
    if (!config.sardisKey || config.sardisKey.trim() === '') {
      throw new RampError('Sardis API key is required', 'INVALID_CONFIG')
    }
    if (!config.bridgeKey || config.bridgeKey.trim() === '') {
      throw new RampError('Bridge API key is required', 'INVALID_CONFIG')
    }

    this.sardisKey = config.sardisKey
    this.bridgeKey = config.bridgeKey

    // Allow custom URLs for testing/enterprise deployments
    this.bridgeUrl = config.bridgeUrl ?? (
      config.environment === 'production'
        ? DEFAULT_BRIDGE_API_URL
        : DEFAULT_BRIDGE_SANDBOX_URL
    )
    this.sardisUrl = config.sardisUrl ?? DEFAULT_SARDIS_API_URL
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

  private async bridgeRequest<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const response = await fetch(`${this.bridgeUrl}${path}`, {
      method,
      headers: {
        'Api-Key': this.bridgeKey,
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new RampError(
        error.message || 'Bridge API error',
        error.code || 'BRIDGE_ERROR',
        error
      )
    }

    return response.json()
  }

  async getWallet(walletId: string): Promise<Wallet> {
    return this.sardisRequest<Wallet>('GET', `/wallets/${walletId}`)
  }

  /**
   * Fund a Sardis wallet from fiat sources.
   *
   * @example
   * ```typescript
   * const result = await ramp.fundWallet({
   *   walletId: 'wallet_123',
   *   amountUsd: 100,
   *   method: 'bank'
   * })
   * console.log(result.achInstructions?.routingNumber)
   * ```
   */
  async fundWallet(params: {
    walletId: string
    amountUsd: number
    method: FundingMethod
  }): Promise<FundingResult> {
    const wallet = await this.getWallet(params.walletId)

    if (params.method === 'crypto') {
      return {
        type: 'crypto',
        depositAddress: wallet.address,
        chain: wallet.chain,
        token: 'USDC',
      }
    }

    const transfer = await this.bridgeRequest<{
      id: string
      hosted_url?: string
      source_deposit_instructions?: {
        payment_rail: string
        account_number: string
        routing_number: string
        bank_name: string
        account_holder: string
        reference: string
        swift_code?: string
        bank_address?: string
      }
      estimated_completion_at?: string
      fee?: { percent: string }
    }>('POST', '/transfers', {
      amount: params.amountUsd.toString(),
      on_behalf_of: params.walletId,
      source: {
        payment_rail: params.method === 'bank' ? 'ach' : 'card',
        currency: 'usd',
      },
      destination: {
        payment_rail: 'ethereum',
        currency: 'usdc',
        to_address: wallet.address,
        chain: this.chainToBridge(wallet.chain),
      },
    })

    let achInstructions: ACHDetails | undefined
    let wireInstructions: WireDetails | undefined

    const instr = transfer.source_deposit_instructions
    if (instr?.payment_rail === 'ach') {
      achInstructions = {
        accountNumber: instr.account_number,
        routingNumber: instr.routing_number,
        bankName: instr.bank_name,
        accountHolder: instr.account_holder,
        reference: instr.reference,
      }
    } else if (instr?.payment_rail === 'wire') {
      wireInstructions = {
        accountNumber: instr.account_number,
        routingNumber: instr.routing_number,
        swiftCode: instr.swift_code || '',
        bankName: instr.bank_name,
        bankAddress: instr.bank_address || '',
        accountHolder: instr.account_holder,
        reference: instr.reference,
      }
    }

    return {
      type: 'fiat',
      paymentLink: transfer.hosted_url,
      achInstructions,
      wireInstructions,
      estimatedArrival: transfer.estimated_completion_at
        ? new Date(transfer.estimated_completion_at)
        : undefined,
      feePercent: transfer.fee ? parseFloat(transfer.fee.percent) : undefined,
      transferId: transfer.id,
    }
  }

  /**
   * Withdraw from Sardis wallet to bank account.
   *
   * @example
   * ```typescript
   * const result = await ramp.withdrawToBank({
   *   walletId: 'wallet_123',
   *   amountUsd: 50,
   *   bankAccount: {
   *     accountHolderName: 'John Doe',
   *     accountNumber: '1234567890',
   *     routingNumber: '021000021'
   *   }
   * })
   * ```
   */
  async withdrawToBank(params: {
    walletId: string
    amountUsd: number
    bankAccount: BankAccount
  }): Promise<WithdrawalResult> {
    const wallet = await this.getWallet(params.walletId)

    // Policy check
    const policyCheck = await this.sardisRequest<{
      allowed: boolean
      reason?: string
    }>('POST', `/wallets/${params.walletId}/check-policy`, {
      amount: params.amountUsd.toString(),
      action: 'withdrawal',
    })

    if (!policyCheck.allowed) {
      throw new PolicyViolation(policyCheck.reason || 'Policy violation')
    }

    // Get Bridge deposit address
    const bridgeDeposit = await this.bridgeRequest<{ address: string }>(
      'POST',
      '/deposit-addresses',
      {
        chain: this.chainToBridge(wallet.chain),
        currency: 'usdc',
      }
    )

    // Send USDC to Bridge
    const tx = await this.sardisRequest<{ tx_hash: string }>(
      'POST',
      '/transactions',
      {
        wallet_id: params.walletId,
        to: bridgeDeposit.address,
        amount: params.amountUsd.toString(),
        token: 'USDC',
        memo: 'Withdrawal to bank',
      }
    )

    // Create payout to bank
    const payout = await this.bridgeRequest<{
      id: string
      estimated_completion_at: string
      fee?: { amount: string }
    }>('POST', '/payouts', {
      amount: params.amountUsd.toString(),
      currency: 'usd',
      source: {
        tx_hash: tx.tx_hash,
        chain: this.chainToBridge(wallet.chain),
      },
      destination: {
        payment_rail: 'ach',
        account_holder_name: params.bankAccount.accountHolderName,
        account_number: params.bankAccount.accountNumber,
        routing_number: params.bankAccount.routingNumber,
        account_type: params.bankAccount.accountType || 'checking',
      },
    })

    return {
      txHash: tx.tx_hash,
      payoutId: payout.id,
      estimatedArrival: new Date(payout.estimated_completion_at),
      fee: payout.fee ? parseFloat(payout.fee.amount) : 0,
      status: 'pending',
    }
  }

  /**
   * Pay merchant in USD from crypto wallet.
   *
   * @example
   * ```typescript
   * const result = await ramp.payMerchantFiat({
   *   walletId: 'wallet_123',
   *   amountUsd: 99.99,
   *   merchant: {
   *     name: 'ACME Corp',
   *     bankAccount: { ... }
   *   }
   * })
   * ```
   */
  async payMerchantFiat(params: {
    walletId: string
    amountUsd: number
    merchant: MerchantAccount
  }): Promise<PaymentResult> {
    const wallet = await this.getWallet(params.walletId)

    // Policy check
    const policyCheck = await this.sardisRequest<{
      allowed: boolean
      reason?: string
      requires_approval?: boolean
    }>('POST', `/wallets/${params.walletId}/check-policy`, {
      amount: params.amountUsd.toString(),
      merchant: params.merchant.name,
      category: params.merchant.category,
    })

    if (!policyCheck.allowed) {
      throw new PolicyViolation(policyCheck.reason || 'Policy violation')
    }

    if (policyCheck.requires_approval) {
      const approval = await this.sardisRequest<Record<string, unknown>>(
        'POST',
        `/wallets/${params.walletId}/request-approval`,
        {
          amount: params.amountUsd.toString(),
          reason: `Payment to ${params.merchant.name}`,
        }
      )
      return {
        status: 'pending_approval',
        approvalRequest: approval,
      }
    }

    // Create payment via Bridge
    const payment = await this.bridgeRequest<{
      id: string
      source_tx_hash?: string
      fee?: { amount: string }
    }>('POST', '/payments', {
      amount: params.amountUsd.toString(),
      source: {
        wallet_address: wallet.address,
        chain: this.chainToBridge(wallet.chain),
        currency: 'usdc',
      },
      destination: {
        payment_rail: 'ach',
        currency: 'usd',
        account_holder_name: params.merchant.bankAccount.accountHolderName,
        account_number: params.merchant.bankAccount.accountNumber,
        routing_number: params.merchant.bankAccount.routingNumber,
      },
    })

    return {
      status: 'completed',
      paymentId: payment.id,
      merchantReceived: params.amountUsd,
      fee: payment.fee ? parseFloat(payment.fee.amount) : 0,
      txHash: payment.source_tx_hash,
    }
  }

  /**
   * Get status of a funding transfer.
   */
  async getFundingStatus(transferId: string): Promise<unknown> {
    return this.bridgeRequest('GET', `/transfers/${transferId}`)
  }

  /**
   * Get status of a bank withdrawal.
   */
  async getWithdrawalStatus(payoutId: string): Promise<unknown> {
    return this.bridgeRequest('GET', `/payouts/${payoutId}`)
  }

  private chainToBridge(chain: string): string {
    const mapping: Record<string, string> = {
      base: 'base',
      polygon: 'polygon',
      ethereum: 'ethereum',
      arbitrum: 'arbitrum',
      optimism: 'optimism',
    }
    return mapping[chain.toLowerCase()] || chain
  }
}
