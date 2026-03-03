/**
 * CLI Types and Zod Schemas
 */

import { z } from 'zod';

// Wallet
export interface Wallet {
  wallet_id: string;
  agent_id: string;
  balance: string;
  currency: string;
  is_active: boolean;
  address?: string;
  chain?: string;
}

export const WalletSchema = z.object({
  wallet_id: z.string(),
  agent_id: z.string(),
  balance: z.string(),
  currency: z.string(),
  is_active: z.boolean(),
  address: z.string().optional(),
  chain: z.string().optional(),
});

// Agent
export interface Agent {
  external_id: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
}

export const AgentSchema = z.object({
  external_id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  is_active: z.boolean(),
  created_at: z.string(),
});

// Payment
export interface PaymentResult {
  payment_id: string;
  status: string;
  ledger_tx_id?: string;
  chain_tx_hash?: string;
  chain: string;
  amount: string;
  token: string;
}

// Hold
export interface Hold {
  hold_id: string;
  wallet_id: string;
  amount: string;
  token: string;
  status: 'active' | 'captured' | 'voided' | 'expired';
  merchant_id?: string;
  purpose?: string;
  expires_at: string;
  captured_amount?: string;
  created_at: string;
}

// Card
export interface Card {
  card_id: string;
  agent_id: string;
  last4: string;
  spending_limit: string;
  spent: string;
  status: 'active' | 'frozen' | 'cancelled';
  provider: string;
  currency: string;
}

// Policy
export interface Policy {
  policy_id: string;
  agent_id: string;
  max_per_tx?: number;
  max_total?: number;
  allowed_destinations?: string[];
  status: string;
}

export interface PolicyCheckResult {
  allowed: boolean;
  reason?: string;
  checks_passed?: string[];
  checks_failed?: string[];
}

// Spending
export interface SpendingSummary {
  period: string;
  total_spent: string;
  total_transactions: number;
  top_merchants: string[];
  by_agent: Array<{
    agent_id: string;
    spent: string;
    transactions: number;
  }>;
}
