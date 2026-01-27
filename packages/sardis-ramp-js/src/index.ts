/**
 * Sardis Fiat Ramp
 *
 * Fiat on/off ramp integrations for Sardis wallets.
 * Supports multiple providers:
 * - Onramper (aggregator with 100+ providers)
 * - Bridge.xyz (direct integration)
 *
 * @packageDocumentation
 */

// Bridge integration (direct)
export { SardisFiatRamp } from './ramp'

// Onramper integration (aggregator)
export {
  SardisOnramper,
  createOnramper,
  type OnramperConfig,
  type OnramperQuote,
  type OnramperTransaction,
  type OnramperWidgetOptions,
  type SupportedAsset,
  type SupportedFiat,
} from './onramper'

// Types
export type {
  RampConfig,
  FundingMethod,
  FundingResult,
  WithdrawalResult,
  PaymentResult,
  BankAccount,
  MerchantAccount,
  ACHDetails,
  WireDetails,
  Wallet,
} from './types'

// Errors
export { RampError, PolicyViolation } from './errors'
