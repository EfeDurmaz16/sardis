/**
 * Sardis payment tools for Vercel AI SDK.
 *
 * These tools enable AI agents to make payments with policy guardrails.
 *
 * @example
 * ```typescript
 * import { generateText } from 'ai'
 * import { openai } from '@ai-sdk/openai'
 * import { createSardisTools } from '@sardis/ai-sdk'
 *
 * const sardisTools = createSardisTools({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: 'wallet_abc123',
 * })
 *
 * const result = await generateText({
 *   model: openai('gpt-4o'),
 *   tools: sardisTools,
 *   prompt: 'Pay $50 to merchant_xyz for API credits',
 * })
 * ```
 */

import { tool } from 'ai'
import { z } from 'zod'
import type { CoreTool } from 'ai'
import type {
  SardisToolsConfig,
  PaymentResult,
  HoldResult,
  PolicyCheckResult,
  BalanceResult,
} from './types'
import {
  PaymentParamsSchema,
  HoldParamsSchema,
  CaptureParamsSchema,
  PolicyCheckParamsSchema,
  BalanceParamsSchema,
} from './types'

/**
 * Internal Sardis API client for tool execution.
 */
class SardisToolClient {
  private apiKey: string
  private walletId: string
  private agentId?: string
  private baseUrl: string
  private simulationMode: boolean
  private maxPaymentAmount?: number
  private blockedCategories: string[]
  private allowedMerchants?: string[]

  constructor(config: SardisToolsConfig) {
    this.apiKey = config.apiKey
    this.walletId = config.walletId
    this.agentId = config.agentId
    this.baseUrl = config.baseUrl || 'https://api.sardis.sh/v2'
    this.simulationMode = config.simulationMode || false
    this.maxPaymentAmount = config.maxPaymentAmount
    this.blockedCategories = config.blockedCategories || []
    this.allowedMerchants = config.allowedMerchants
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-Wallet-Id': this.walletId,
        ...(this.agentId && { 'X-Agent-Id': this.agentId }),
        ...(this.simulationMode && { 'X-Simulation-Mode': 'true' }),
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || `API error: ${response.status}`)
    }

    return response.json()
  }

  /**
   * Local policy pre-check before API call.
   */
  private preCheckPolicy(
    amount: number,
    merchant?: string,
    category?: string
  ): { allowed: boolean; reason?: string } {
    // Check max payment amount
    if (this.maxPaymentAmount && amount > this.maxPaymentAmount) {
      return {
        allowed: false,
        reason: `Amount $${amount} exceeds maximum allowed payment of $${this.maxPaymentAmount}`,
      }
    }

    // Check blocked categories
    if (category && this.blockedCategories.includes(category.toLowerCase())) {
      return {
        allowed: false,
        reason: `Category "${category}" is blocked by policy`,
      }
    }

    // Check allowed merchants (whitelist mode)
    if (this.allowedMerchants && merchant) {
      if (!this.allowedMerchants.includes(merchant.toLowerCase())) {
        return {
          allowed: false,
          reason: `Merchant "${merchant}" is not in the allowed list`,
        }
      }
    }

    return { allowed: true }
  }

  async executePayment(params: z.infer<typeof PaymentParamsSchema>): Promise<PaymentResult> {
    // Local pre-check
    const preCheck = this.preCheckPolicy(params.amount, params.merchant, params.category)
    if (!preCheck.allowed) {
      return {
        success: false,
        amount: params.amount,
        token: params.token || 'USDC',
        chain: params.chain || 'base',
        status: 'failed',
        error: preCheck.reason,
        timestamp: new Date().toISOString(),
      }
    }

    try {
      const result = await this.request<{
        transaction_id: string
        tx_hash: string
        status: string
        block_number?: number
      }>('POST', '/payments/execute', {
        wallet_id: this.walletId,
        to: params.to,
        amount: params.amount.toString(),
        token: params.token || 'USDC',
        chain: params.chain || 'base',
        memo: params.memo,
        merchant: params.merchant,
        category: params.category,
        idempotency_key: params.idempotencyKey,
      })

      return {
        success: true,
        transactionId: result.transaction_id,
        txHash: result.tx_hash,
        amount: params.amount,
        token: params.token || 'USDC',
        chain: params.chain || 'base',
        status: result.status as PaymentResult['status'],
        blockNumber: result.block_number,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return {
        success: false,
        amount: params.amount,
        token: params.token || 'USDC',
        chain: params.chain || 'base',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      }
    }
  }

  async createHold(params: z.infer<typeof HoldParamsSchema>): Promise<HoldResult> {
    try {
      const result = await this.request<{
        hold_id: string
        expires_at: string
        status: string
      }>('POST', '/holds', {
        wallet_id: this.walletId,
        amount: params.amount.toString(),
        merchant: params.merchant,
        expires_in_hours: params.expiresInHours || 24,
        description: params.description,
      })

      return {
        success: true,
        holdId: result.hold_id,
        amount: params.amount,
        merchant: params.merchant,
        expiresAt: result.expires_at,
        status: result.status as HoldResult['status'],
      }
    } catch (error) {
      return {
        success: false,
        amount: params.amount,
        merchant: params.merchant,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async captureHold(params: z.infer<typeof CaptureParamsSchema>): Promise<HoldResult> {
    try {
      const result = await this.request<{
        hold_id: string
        amount: number
        merchant: string
        status: string
      }>('POST', `/holds/${params.holdId}/capture`, {
        amount: params.amount?.toString(),
      })

      return {
        success: true,
        holdId: result.hold_id,
        amount: result.amount,
        merchant: result.merchant,
        status: 'captured',
      }
    } catch (error) {
      return {
        success: false,
        holdId: params.holdId,
        amount: params.amount || 0,
        merchant: '',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async voidHold(holdId: string): Promise<HoldResult> {
    try {
      const result = await this.request<{
        hold_id: string
        amount: number
        merchant: string
      }>('POST', `/holds/${holdId}/void`, {})

      return {
        success: true,
        holdId: result.hold_id,
        amount: result.amount,
        merchant: result.merchant,
        status: 'voided',
      }
    } catch (error) {
      return {
        success: false,
        holdId: holdId,
        amount: 0,
        merchant: '',
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async checkPolicy(params: z.infer<typeof PolicyCheckParamsSchema>): Promise<PolicyCheckResult> {
    // Local pre-check first
    const preCheck = this.preCheckPolicy(params.amount, params.merchant, params.category)
    if (!preCheck.allowed) {
      return {
        allowed: false,
        reason: preCheck.reason,
      }
    }

    try {
      const result = await this.request<{
        allowed: boolean
        reason?: string
        remaining_daily_limit?: number
        remaining_monthly_limit?: number
        requires_approval?: boolean
      }>('POST', `/wallets/${this.walletId}/check-policy`, {
        amount: params.amount.toString(),
        merchant: params.merchant,
        category: params.category,
      })

      return {
        allowed: result.allowed,
        reason: result.reason,
        remainingDailyLimit: result.remaining_daily_limit,
        remainingMonthlyLimit: result.remaining_monthly_limit,
        requiresApproval: result.requires_approval,
      }
    } catch (error) {
      return {
        allowed: false,
        reason: error instanceof Error ? error.message : 'Policy check failed',
      }
    }
  }

  async getBalance(params: z.infer<typeof BalanceParamsSchema>): Promise<BalanceResult> {
    try {
      const result = await this.request<{
        available: string
        pending: string
        held: string
        token: string
        chain: string
      }>('GET', `/wallets/${this.walletId}/balance?token=${params.token || 'USDC'}${params.chain ? `&chain=${params.chain}` : ''}`)

      return {
        available: parseFloat(result.available),
        pending: parseFloat(result.pending),
        held: parseFloat(result.held),
        token: result.token,
        chain: result.chain,
      }
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get balance')
    }
  }

  async getSpendingSummary(): Promise<{
    today: number
    thisWeek: number
    thisMonth: number
    byCategory: Record<string, number>
    byMerchant: Record<string, number>
  }> {
    try {
      return await this.request('GET', `/wallets/${this.walletId}/spending/summary`)
    } catch (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to get spending summary')
    }
  }
}

/**
 * Create Sardis payment tools for Vercel AI SDK.
 *
 * Returns a set of tools that can be passed to `generateText` or `streamText`.
 *
 * @example
 * ```typescript
 * const tools = createSardisTools({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: 'wallet_abc123',
 *   maxPaymentAmount: 100, // Optional: limit single payments
 *   blockedCategories: ['gambling', 'adult'], // Optional: block categories
 * })
 *
 * const { text, toolResults } = await generateText({
 *   model: openai('gpt-4o'),
 *   tools,
 *   prompt: 'Check my balance and pay $25 to OpenAI for API credits',
 * })
 * ```
 */
export function createSardisTools(config: SardisToolsConfig): Record<string, CoreTool> {
  const client = new SardisToolClient(config)

  return {
    /**
     * Execute a payment from the wallet.
     */
    sardis_pay: tool({
      description: `Execute a payment from the Sardis wallet. Use this to send money to merchants or addresses.
Always check the policy first for large amounts. The payment is executed on-chain and returns a transaction hash.
Supported chains: base, polygon, ethereum, arbitrum, optimism.
Default token is USDC.`,
      parameters: PaymentParamsSchema,
      execute: async (params) => client.executePayment(params),
    }),

    /**
     * Create a hold (pre-authorization) for a future payment.
     */
    sardis_create_hold: tool({
      description: `Create a hold (pre-authorization) on funds for a future payment.
Use this when the final amount is not yet known, like hotel reservations or variable-price services.
The hold reserves funds without transferring them. Capture the hold later to complete the payment.`,
      parameters: HoldParamsSchema,
      execute: async (params) => client.createHold(params),
    }),

    /**
     * Capture a previously created hold.
     */
    sardis_capture_hold: tool({
      description: `Capture a previously created hold to complete the payment.
You can capture the full amount or a partial amount (for tips, adjustments, etc.).
If no amount is specified, the full hold amount is captured.`,
      parameters: CaptureParamsSchema,
      execute: async (params) => client.captureHold(params),
    }),

    /**
     * Void/cancel a hold.
     */
    sardis_void_hold: tool({
      description: `Void (cancel) a hold to release the reserved funds back to the wallet.
Use this when a transaction is cancelled or no longer needed.`,
      parameters: z.object({
        holdId: z.string().describe('ID of the hold to void'),
      }),
      execute: async ({ holdId }) => client.voidHold(holdId),
    }),

    /**
     * Check if a payment is allowed by policy.
     */
    sardis_check_policy: tool({
      description: `Check if a payment would be allowed by the wallet's policy before attempting it.
Use this to verify spending limits, merchant restrictions, and category rules.
Always use this before large payments to avoid failed transactions.`,
      parameters: PolicyCheckParamsSchema,
      execute: async (params) => client.checkPolicy(params),
    }),

    /**
     * Get wallet balance.
     */
    sardis_get_balance: tool({
      description: `Get the current balance of the wallet.
Returns available balance, pending transactions, and held amounts.
Default token is USDC. Can check specific chains if needed.`,
      parameters: BalanceParamsSchema,
      execute: async (params) => client.getBalance(params),
    }),

    /**
     * Get spending summary.
     */
    sardis_get_spending: tool({
      description: `Get a summary of spending from the wallet.
Shows spending by day, week, month, and breakdowns by category and merchant.
Useful for budget tracking and reporting.`,
      parameters: z.object({}),
      execute: async () => client.getSpendingSummary(),
    }),
  }
}

/**
 * Create a minimal set of Sardis tools (pay + balance only).
 *
 * Use this for simpler use cases that don't need holds or detailed policy checks.
 */
export function createMinimalSardisTools(config: SardisToolsConfig): Record<string, CoreTool> {
  const allTools = createSardisTools(config)

  return {
    sardis_pay: allTools.sardis_pay!,
    sardis_get_balance: allTools.sardis_get_balance!,
  }
}

/**
 * Create Sardis tools with only read operations (no payments).
 *
 * Use this for analytics, reporting, or view-only access.
 */
export function createReadOnlySardisTools(config: SardisToolsConfig): Record<string, CoreTool> {
  const allTools = createSardisTools(config)

  return {
    sardis_check_policy: allTools.sardis_check_policy!,
    sardis_get_balance: allTools.sardis_get_balance!,
    sardis_get_spending: allTools.sardis_get_spending!,
  }
}
