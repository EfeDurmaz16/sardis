/**
 * Sardis Provider for Vercel AI SDK.
 *
 * Provides a higher-level abstraction for integrating Sardis payments
 * with AI agents, including automatic policy enforcement and transaction logging.
 *
 * @example
 * ```typescript
 * import { SardisProvider } from '@sardis/ai-sdk/provider'
 *
 * const sardis = new SardisProvider({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: 'wallet_abc123',
 *   agentId: 'agent_xyz789',
 * })
 *
 * // Use with Vercel AI SDK
 * const { text } = await generateText({
 *   model: openai('gpt-4o'),
 *   tools: sardis.tools,
 *   system: sardis.systemPrompt,
 *   prompt: 'Purchase $50 worth of API credits',
 * })
 *
 * // Or execute directly
 * const result = await sardis.pay({
 *   to: 'merchant_openai',
 *   amount: 50,
 *   memo: 'API credits',
 * })
 * ```
 */

import { createSardisTools, createMinimalSardisTools, createReadOnlySardisTools } from './tools'
import type { SardisToolsConfig, PaymentResult, HoldResult, PolicyCheckResult, BalanceResult } from './types'
import type { Tool, ToolExecutionOptions } from 'ai'

/**
 * Extended configuration for SardisProvider.
 */
export interface SardisProviderConfig extends SardisToolsConfig {
  /** Log all transactions to console */
  enableLogging?: boolean
  /** Callback for transaction events */
  onTransaction?: (event: TransactionEvent) => void | Promise<void>
  /** Custom system prompt additions */
  customInstructions?: string
  /** Tool set to use: 'full', 'minimal', 'readonly' */
  toolSet?: 'full' | 'minimal' | 'readonly'
}

/**
 * Transaction event for logging/callbacks.
 */
export interface TransactionEvent {
  type: 'payment' | 'hold_create' | 'hold_capture' | 'hold_void' | 'policy_check' | 'balance_check'
  timestamp: string
  params: Record<string, unknown>
  result: PaymentResult | HoldResult | PolicyCheckResult | BalanceResult
  success: boolean
  error?: string
}

/**
 * Sardis Provider for streamlined AI agent integration.
 *
 * Provides:
 * - Pre-configured tools for Vercel AI SDK
 * - System prompt with payment guidelines
 * - Direct payment methods for programmatic access
 * - Transaction logging and callbacks
 */
export class SardisProvider {
  private config: SardisProviderConfig
  private _tools: Record<string, Tool>

  constructor(config: SardisProviderConfig) {
    this.config = config

    // Create appropriate tool set
    switch (config.toolSet) {
      case 'minimal':
        this._tools = createMinimalSardisTools(config)
        break
      case 'readonly':
        this._tools = createReadOnlySardisTools(config)
        break
      default:
        this._tools = createSardisTools(config)
    }

    // Wrap tools with logging if enabled
    if (config.enableLogging || config.onTransaction) {
      this._tools = this.wrapToolsWithLogging(this._tools)
    }
  }

  /**
   * Get the tools for Vercel AI SDK.
   */
  get tools(): Record<string, Tool> {
    return this._tools
  }

  /**
   * Get the recommended system prompt for payment agents.
   */
  get systemPrompt(): string {
    const basePrompt = `You are an AI assistant with access to a Sardis payment wallet.

## Payment Guidelines

1. **Always check policy before large payments** (>$50)
   - Use sardis_check_policy to verify the payment would be allowed
   - Report any policy violations to the user

2. **Use holds for uncertain amounts**
   - Create a hold when the final amount isn't known
   - Capture the hold once the final amount is confirmed
   - Void holds that are no longer needed

3. **Provide transaction details**
   - Always include the transaction ID and status in your response
   - If a payment fails, explain why and suggest alternatives

4. **Respect spending limits**
   - Check remaining limits with sardis_get_spending
   - Don't attempt payments that would exceed limits

5. **Security practices**
   - Never expose wallet IDs or API keys
   - Verify merchant names before large payments
   - Double-check amounts with the user for payments >$100

## Available Actions

- **sardis_pay**: Execute a payment
- **sardis_create_hold**: Reserve funds for later
- **sardis_capture_hold**: Complete a held payment
- **sardis_void_hold**: Cancel a hold
- **sardis_check_policy**: Check if payment is allowed
- **sardis_get_balance**: Check wallet balance
- **sardis_get_spending**: View spending summary`

    if (this.config.customInstructions) {
      return `${basePrompt}\n\n## Additional Instructions\n\n${this.config.customInstructions}`
    }

    return basePrompt
  }

  /**
   * Execute a payment directly (without AI).
   */
  async pay(params: {
    to: string
    amount: number
    token?: string
    chain?: 'base' | 'polygon' | 'ethereum' | 'arbitrum' | 'optimism'
    memo?: string
    merchant?: string
    category?: string
  }): Promise<PaymentResult> {
    const tool = this._tools.sardis_pay
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Payment tool not available')
    }
    return tool.execute(params, { toolCallId: 'direct', messages: [] }) as Promise<PaymentResult>
  }

  /**
   * Create a hold directly (without AI).
   */
  async createHold(params: {
    amount: number
    merchant: string
    expiresInHours?: number
    description?: string
  }): Promise<HoldResult> {
    const tool = this._tools.sardis_create_hold
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Hold tool not available')
    }
    return tool.execute(params, { toolCallId: 'direct', messages: [] }) as Promise<HoldResult>
  }

  /**
   * Capture a hold directly (without AI).
   */
  async captureHold(holdId: string, amount?: number): Promise<HoldResult> {
    const tool = this._tools.sardis_capture_hold
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Capture tool not available')
    }
    return tool.execute({ holdId, amount }, { toolCallId: 'direct', messages: [] }) as Promise<HoldResult>
  }

  /**
   * Void a hold directly (without AI).
   */
  async voidHold(holdId: string): Promise<HoldResult> {
    const tool = this._tools.sardis_void_hold
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Void tool not available')
    }
    return tool.execute({ holdId }, { toolCallId: 'direct', messages: [] }) as Promise<HoldResult>
  }

  /**
   * Check policy directly (without AI).
   */
  async checkPolicy(params: {
    amount: number
    merchant?: string
    category?: string
  }): Promise<PolicyCheckResult> {
    const tool = this._tools.sardis_check_policy
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Policy check tool not available')
    }
    return tool.execute(params, { toolCallId: 'direct', messages: [] }) as Promise<PolicyCheckResult>
  }

  /**
   * Get balance directly (without AI).
   */
  async getBalance(token?: string, chain?: string): Promise<BalanceResult> {
    const tool = this._tools.sardis_get_balance
    if (!tool || typeof tool.execute !== 'function') {
      throw new Error('Balance tool not available')
    }
    return tool.execute({ token, chain }, { toolCallId: 'direct', messages: [] }) as Promise<BalanceResult>
  }

  /**
   * Wrap tools with logging functionality.
   */
  private wrapToolsWithLogging(tools: Record<string, Tool>): Record<string, Tool> {
    const wrapped: Record<string, Tool> = {}

    for (const [name, tool] of Object.entries(tools)) {
      if (tool && typeof tool.execute === 'function') {
        const originalExecute = tool.execute.bind(tool)

        wrapped[name] = {
          ...tool,
          execute: async (params: unknown, options: ToolExecutionOptions) => {
            const startTime = Date.now()
            let result: unknown
            let success = true
            let error: string | undefined

            try {
              result = await originalExecute(params, options)

              // Check if result indicates failure
              if (result && typeof result === 'object' && 'success' in result) {
                success = (result as { success: boolean }).success
                if (!success && 'error' in result) {
                  error = (result as { error?: string }).error
                }
              }
            } catch (e) {
              success = false
              error = e instanceof Error ? e.message : 'Unknown error'
              throw e
            } finally {
              const event: TransactionEvent = {
                type: this.getEventType(name),
                timestamp: new Date().toISOString(),
                params: params as Record<string, unknown>,
                result: result as TransactionEvent['result'],
                success,
                error,
              }

              // Log to console if enabled
              if (this.config.enableLogging) {
                const duration = Date.now() - startTime
                console.log(`[Sardis] ${name} ${success ? '✓' : '✗'} (${duration}ms)`, event)
              }

              // Call transaction callback if provided
              if (this.config.onTransaction) {
                try {
                  await this.config.onTransaction(event)
                } catch (callbackError) {
                  console.error('[Sardis] Transaction callback error:', callbackError)
                }
              }
            }

            return result
          },
        } as Tool
      } else {
        wrapped[name] = tool
      }
    }

    return wrapped
  }

  /**
   * Map tool name to event type.
   */
  private getEventType(toolName: string): TransactionEvent['type'] {
    const mapping: Record<string, TransactionEvent['type']> = {
      sardis_pay: 'payment',
      sardis_create_hold: 'hold_create',
      sardis_capture_hold: 'hold_capture',
      sardis_void_hold: 'hold_void',
      sardis_check_policy: 'policy_check',
      sardis_get_balance: 'balance_check',
      sardis_get_spending: 'balance_check',
    }
    return mapping[toolName] || 'payment'
  }
}

/**
 * Create a SardisProvider instance.
 *
 * Convenience function for creating a provider.
 */
export function createSardisProvider(config: SardisProviderConfig): SardisProvider {
  return new SardisProvider(config)
}
