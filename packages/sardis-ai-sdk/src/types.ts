/**
 * Type definitions for Sardis AI SDK integration.
 */

import { z } from 'zod'

/**
 * Configuration for Sardis AI SDK tools.
 */
export interface SardisToolsConfig {
  /** Sardis API key */
  apiKey: string
  /** Default wallet ID for payments */
  walletId: string
  /** Default agent ID */
  agentId?: string
  /** Base URL for Sardis API (default: https://api.sardis.sh) */
  baseUrl?: string
  /** Enable simulation mode (no real transactions) */
  simulationMode?: boolean
  /** Maximum single payment amount (policy limit) */
  maxPaymentAmount?: number
  /** Blocked merchant categories */
  blockedCategories?: string[]
  /** Allowed merchants only (whitelist mode) */
  allowedMerchants?: string[]
}

/**
 * Payment execution parameters.
 */
export const PaymentParamsSchema = z.object({
  /** Recipient address or merchant identifier */
  to: z.string().describe('Recipient wallet address or merchant ID'),
  /** Amount in USD */
  amount: z.number().positive().describe('Payment amount in USD'),
  /** Token to use (default: USDC) */
  token: z.string().optional().default('USDC').describe('Token to use for payment'),
  /** Chain to execute on */
  chain: z.enum(['base', 'polygon', 'ethereum', 'arbitrum', 'optimism']).optional().default('base').describe('Blockchain network'),
  /** Payment description/memo */
  memo: z.string().optional().describe('Description or memo for the payment'),
  /** Merchant name for policy checks */
  merchant: z.string().optional().describe('Merchant name for policy validation'),
  /** Merchant category code */
  category: z.string().optional().describe('Merchant category code (e.g., "software", "travel")'),
  /** Idempotency key to prevent duplicates */
  idempotencyKey: z.string().optional().describe('Unique key to prevent duplicate payments'),
})

export type PaymentParams = z.infer<typeof PaymentParamsSchema>

/**
 * Hold creation parameters.
 */
export const HoldParamsSchema = z.object({
  /** Amount to hold in USD */
  amount: z.number().positive().describe('Hold amount in USD'),
  /** Merchant name */
  merchant: z.string().describe('Merchant name for the hold'),
  /** Hold expiration in hours (default: 24) */
  expiresInHours: z.number().optional().default(24).describe('Hours until hold expires'),
  /** Description of the hold purpose */
  description: z.string().optional().describe('Description of what the hold is for'),
})

export type HoldParams = z.infer<typeof HoldParamsSchema>

/**
 * Hold capture parameters.
 */
export const CaptureParamsSchema = z.object({
  /** Hold ID to capture */
  holdId: z.string().describe('ID of the hold to capture'),
  /** Amount to capture (defaults to full hold amount) */
  amount: z.number().positive().optional().describe('Amount to capture (partial capture if less than hold)'),
})

export type CaptureParams = z.infer<typeof CaptureParamsSchema>

/**
 * Policy check parameters.
 */
export const PolicyCheckParamsSchema = z.object({
  /** Amount to check */
  amount: z.number().positive().describe('Amount to check against policy'),
  /** Merchant name */
  merchant: z.string().optional().describe('Merchant name for policy check'),
  /** Merchant category */
  category: z.string().optional().describe('Merchant category for policy check'),
})

export type PolicyCheckParams = z.infer<typeof PolicyCheckParamsSchema>

/**
 * Balance check parameters.
 */
export const BalanceParamsSchema = z.object({
  /** Token to check (default: USDC) */
  token: z.string().optional().default('USDC').describe('Token to check balance for'),
  /** Chain to check */
  chain: z.string().optional().describe('Specific chain to check balance on'),
})

export type BalanceParams = z.infer<typeof BalanceParamsSchema>

/**
 * Payment result.
 */
export interface PaymentResult {
  success: boolean
  transactionId?: string
  txHash?: string
  amount: number
  token: string
  chain: string
  status: 'completed' | 'pending' | 'failed'
  error?: string
  blockNumber?: number
  timestamp: string
}

/**
 * Hold result.
 */
export interface HoldResult {
  success: boolean
  holdId?: string
  amount: number
  merchant: string
  expiresAt?: string
  status: 'active' | 'captured' | 'voided' | 'expired' | 'failed'
  error?: string
}

/**
 * Policy check result.
 */
export interface PolicyCheckResult {
  allowed: boolean
  reason?: string
  remainingDailyLimit?: number
  remainingMonthlyLimit?: number
  requiresApproval?: boolean
}

/**
 * Balance result.
 */
export interface BalanceResult {
  available: number
  pending: number
  held: number
  token: string
  chain: string
}
