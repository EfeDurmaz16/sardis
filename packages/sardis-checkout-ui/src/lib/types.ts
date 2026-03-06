export interface SessionDetails {
  session_id: string;
  merchant_name: string;
  merchant_logo_url: string | null;
  amount: string;
  currency: string;
  description: string | null;
  status: string;
  expires_at: string | null;
}

export interface ConnectResult {
  status: string;
  session_id: string;
  wallet_id: string;
  wallet_address: string;
}

export interface BalanceInfo {
  wallet_id: string;
  wallet_address: string;
  balance: string;
  currency: string;
  chain: string;
}

export interface PaymentResult {
  session_id: string;
  status: string;
  tx_hash: string | null;
  amount: string;
  currency: string;
  merchant_id: string;
}

export type CheckoutStep =
  | "loading"
  | "pay"
  | "fund"
  | "processing"
  | "success"
  | "error"
  | "expired";
