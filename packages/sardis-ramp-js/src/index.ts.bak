/**
 * Sardis Fiat Ramp - Bridge crypto wallets to traditional banking.
 *
 * @example
 * ```typescript
 * import { SardisFiatRamp } from '@sardis/fiat-ramp'
 *
 * const ramp = new SardisFiatRamp({
 *   sardisKey: 'sk_...',
 *   bridgeKey: 'bridge_...'
 * })
 *
 * // Fund wallet from bank
 * const result = await ramp.fundWallet({
 *   walletId: 'wallet_123',
 *   amountUsd: 100,
 *   method: 'bank'
 * })
 * ```
 */

export { SardisFiatRamp } from './ramp'
export type {
  FundingResult,
  WithdrawalResult,
  PaymentResult,
  BankAccount,
  MerchantAccount,
  FundingMethod,
  RampConfig,
  ACHDetails,
  WireDetails,
} from './types'
export { PolicyViolation } from './errors'
