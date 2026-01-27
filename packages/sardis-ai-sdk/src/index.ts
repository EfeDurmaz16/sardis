/**
 * @sardis/ai-sdk - Sardis payment tools for Vercel AI SDK
 *
 * Enable AI agents to make payments with policy guardrails.
 *
 * @example Basic usage with generateText
 * ```typescript
 * import { generateText } from 'ai'
 * import { openai } from '@ai-sdk/openai'
 * import { createSardisTools } from '@sardis/ai-sdk'
 *
 * const tools = createSardisTools({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: 'wallet_abc123',
 * })
 *
 * const { text, toolResults } = await generateText({
 *   model: openai('gpt-4o'),
 *   tools,
 *   prompt: 'Pay $50 to merchant_xyz for API credits',
 * })
 * ```
 *
 * @example Using SardisProvider for more control
 * ```typescript
 * import { generateText } from 'ai'
 * import { openai } from '@ai-sdk/openai'
 * import { SardisProvider } from '@sardis/ai-sdk'
 *
 * const sardis = new SardisProvider({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: 'wallet_abc123',
 *   enableLogging: true,
 *   onTransaction: async (event) => {
 *     await logToDatabase(event)
 *   },
 * })
 *
 * const { text } = await generateText({
 *   model: openai('gpt-4o'),
 *   tools: sardis.tools,
 *   system: sardis.systemPrompt,
 *   prompt: 'Check my balance and pay $25 for API credits',
 * })
 *
 * // Or use directly without AI
 * const balance = await sardis.getBalance()
 * const result = await sardis.pay({ to: 'merchant', amount: 25 })
 * ```
 *
 * @packageDocumentation
 */

// Main tool creation functions
export {
  createSardisTools,
  createMinimalSardisTools,
  createReadOnlySardisTools,
} from './tools'

// Provider class and factory
export {
  SardisProvider,
  createSardisProvider,
  type SardisProviderConfig,
  type TransactionEvent,
} from './provider'

// Types
export type {
  SardisToolsConfig,
  PaymentParams,
  HoldParams,
  CaptureParams,
  PolicyCheckParams,
  BalanceParams,
  PaymentResult,
  HoldResult,
  PolicyCheckResult,
  BalanceResult,
} from './types'

// Zod schemas for validation
export {
  PaymentParamsSchema,
  HoldParamsSchema,
  CaptureParamsSchema,
  PolicyCheckParamsSchema,
  BalanceParamsSchema,
} from './types'
