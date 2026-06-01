/**
 * AP2 mandate types — the Intent → Cart → Payment mandate chain.
 *
 * Mirrors the fields of `core/mandates.py` that the verifier reads. Amounts are
 * minor units (integer) as in the Python (`*_minor` fields), so we use `number`
 * for the integer minor units the AP2 payload carries (these are AP2 wire-shape
 * integers, distinct from the policy engine's `Money` bigint).
 */

export interface VCProof {
  type?: 'DataIntegrityProof';
  verificationMethod: string;
  created?: string;
  proofPurpose?: string;
  proofValue: string;
}

export interface IntentMandate {
  mandateId: string;
  mandateType: string; // expected "intent"
  issuer?: string;
  subject: string;
  /** epoch seconds */
  expiresAt: number;
  nonce?: string;
  domain?: string;
  purpose: string; // expected "intent"
  scope?: string[];
  /** minor units, or null/undefined if unbounded */
  requestedAmount?: number | null;
  naturalLanguageDescription?: string;
  /** SHA-256 hex of naturalLanguageDescription */
  actionDescriptionHash?: string;
  originHash?: string;
  proof?: VCProof;
}

export interface CartMandate {
  mandateId: string;
  mandateType: string; // expected "cart"
  issuer?: string;
  subject: string;
  expiresAt: number;
  nonce?: string;
  domain?: string;
  purpose: string; // expected "cart"
  lineItems?: Array<Record<string, unknown>>;
  merchantDomain: string;
  currency?: string;
  subtotalMinor: number;
  taxesMinor: number;
  cartHash?: string;
  proof?: VCProof;
}

export interface PaymentMandate {
  mandateId: string;
  mandateType: string; // expected "payment"
  issuer?: string;
  subject: string;
  expiresAt: number;
  nonce?: string;
  domain?: string;
  purpose: string; // expected "checkout"
  chain?: string;
  token?: string;
  amountMinor: number;
  destination?: string;
  auditHash?: string;
  aiAgentPresence?: boolean;
  transactionModality?: 'human_present' | 'human_not_present';
  merchantDomain?: string | null;
  cartMandateHash?: string;
  approvalContextHash?: string;
  proof?: VCProof;
}

export interface MandateBundle {
  intent: IntentMandate;
  cart: CartMandate;
  payment: PaymentMandate;
}

export interface MandateChainVerification {
  accepted: boolean;
  reason?: string;
  driftScore: number;
  driftReasons?: string[];
}
