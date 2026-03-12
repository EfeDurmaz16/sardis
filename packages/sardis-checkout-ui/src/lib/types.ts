export interface SessionDetails {
  session_id: string;
  merchant_name: string;
  merchant_logo_url: string | null;
  amount: string;
  currency: string;
  description: string | null;
  status: string;
  payment_method: string | null;
  payer_wallet_address: string | null;
  expires_at: string | null;
  embed_origin: string | null;
  settlement_address: string | null;
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
  platform_fee: string | null;
  net_amount: string | null;
}

export interface ExternalWalletConnectParams {
  typed_data: {
    domain: Record<string, unknown>;
    message: Record<string, unknown>;
    primaryType: string;
    types: Record<string, Array<{ name: string; type: string }>>;
  };
  chain_id: number;
  nonce: string;
  session_id: string;
}

export type CheckoutStep =
  | "loading"
  | "pay"
  | "fund"
  | "processing"
  | "success"
  | "error"
  | "expired";
