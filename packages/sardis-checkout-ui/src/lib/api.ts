import type {
  SessionDetails,
  ConnectResult,
  BalanceInfo,
  PaymentResult,
  ExternalWalletConnectParams,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v2/merchant-checkout";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Merge headers explicitly so caller-provided headers (e.g. Authorization)
  // don't clobber Content-Type via the options spread.
  const mergedHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: mergedHeaders,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getSessionDetails(clientSecret: string) {
  return request<SessionDetails>(`/sessions/client/${clientSecret}/details`);
}

export function connectWallet(clientSecret: string, walletId: string) {
  return request<ConnectResult>(
    `/sessions/client/${clientSecret}/connect`,
    { method: "POST", body: JSON.stringify({ wallet_id: walletId }) },
  );
}

export function paySession(clientSecret: string, walletId: string) {
  return request<PaymentResult>(`/sessions/client/${clientSecret}/pay`, {
    method: "POST",
    body: JSON.stringify({ wallet_id: walletId }),
  });
}

export function getBalance(clientSecret: string) {
  return request<BalanceInfo>(`/sessions/client/${clientSecret}/balance`);
}

export function getOnrampToken(clientSecret: string, walletAddress: string) {
  // Bearer auth: the client_secret is a session-scoped cryptographic
  // bearer token (same pattern as Stripe client_secret). The backend
  // requires it in the Authorization header on this endpoint to
  // prevent unauthenticated session-token minting (Coinbase CDP
  // review requirement, 2026-04-08).
  return request<{ session_token: string; onramp_url: string }>(
    `/sessions/client/${clientSecret}/onramp-token`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${clientSecret}` },
      body: JSON.stringify({ wallet_address: walletAddress }),
    },
  );
}

export function getExternalWalletConnectParams(clientSecret: string, walletAddress: string) {
  const params = new URLSearchParams({ address: walletAddress });
  return request<ExternalWalletConnectParams>(
    `/sessions/client/${clientSecret}/connect-params?${params.toString()}`,
  );
}

export function connectExternalWallet(
  clientSecret: string,
  body: {
    address: string;
    signature: string;
    message?: string;
    session_id?: string;
    chain_id?: number;
    nonce?: string;
  },
) {
  return request<{ status: string; address: string; session_id: string }>(
    `/sessions/client/${clientSecret}/connect-external`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function confirmExternalPayment(
  clientSecret: string,
  body: { tx_hash: string; address: string },
) {
  return request<PaymentResult>(
    `/sessions/client/${clientSecret}/confirm-external-payment`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

/**
 * Create an EventSource for SSE streaming of session updates.
 * Falls back to null if SSE is not supported.
 */
export function createSessionStream(clientSecret: string): EventSource | null {
  if (typeof EventSource === "undefined") return null;
  return new EventSource(`${API_BASE}/sessions/client/${clientSecret}/stream`);
}
