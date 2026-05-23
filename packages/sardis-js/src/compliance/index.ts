/**
 * `sardis/compliance` — KYC + sanctions + audit-log surface.
 *
 * Provides the evidence resource (tamper-evident receipts) and the
 * shared types used by compliance providers (Persona for KYC, Elliptic
 * for sanctions screening, Sardis-native audit ledger).
 */

export { EvidenceResource } from '../resources/evidence.js';
export type { LedgerEntry } from '../types.js';

export type KYCStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'requires_review';
export type SanctionsHit = 'clear' | 'match' | 'review' | 'pending';

export interface ComplianceCheckSummary {
  kyc: KYCStatus;
  sanctions: SanctionsHit;
  /** ISO 8601 timestamp of the most recent provider response. */
  asOf: string;
}
