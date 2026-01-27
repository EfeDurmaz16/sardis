/**
 * Type definitions for Sardis Fiat Ramp.
 */

export type FundingMethod = 'bank' | 'card' | 'crypto'

export interface BankAccount {
  accountHolderName: string
  accountNumber: string
  routingNumber: string
  accountType?: 'checking' | 'savings'
  bankName?: string
  // For international wires
  swiftCode?: string
  iban?: string
  bankAddress?: string
}

export interface MerchantAccount {
  name: string
  bankAccount: BankAccount
  merchantId?: string
  category?: string
}

export interface ACHDetails {
  accountNumber: string
  routingNumber: string
  bankName: string
  accountHolder: string
  reference: string
}

export interface WireDetails {
  accountNumber: string
  routingNumber: string
  swiftCode: string
  bankName: string
  bankAddress: string
  accountHolder: string
  reference: string
}

export interface FundingResult {
  type: 'crypto' | 'fiat'
  // For crypto deposits
  depositAddress?: string
  chain?: string
  token?: string
  // For fiat deposits
  paymentLink?: string
  achInstructions?: ACHDetails
  wireInstructions?: WireDetails
  estimatedArrival?: Date
  feePercent?: number
  transferId?: string
}

export interface WithdrawalResult {
  txHash: string
  payoutId: string
  estimatedArrival: Date
  fee: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
}

export interface PaymentResult {
  status: 'completed' | 'pending_approval' | 'failed'
  // For completed payments
  paymentId?: string
  merchantReceived?: number
  fee?: number
  txHash?: string
  // For pending approval
  approvalRequest?: Record<string, unknown>
  // For failed payments
  error?: string
}

export interface RampConfig {
  /** Sardis API key (required) */
  sardisKey: string
  /** Bridge API key (required) */
  bridgeKey: string
  /** Environment - sandbox for testing, production for live (default: sandbox) */
  environment?: 'sandbox' | 'production'
  /** Default chain for new wallets */
  defaultChain?: string
  /** Custom Sardis API URL (optional, for enterprise deployments) */
  sardisUrl?: string
  /** Custom Bridge API URL (optional, for testing) */
  bridgeUrl?: string
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number
}

export interface Wallet {
  id: string
  address: string
  chain: string
  balance?: string
  policy?: string
}
