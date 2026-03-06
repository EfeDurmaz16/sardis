import type { SessionDetails, ConnectResult, BalanceInfo, PaymentResult } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v2/merchant-checkout";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getSessionDetails(sessionId: string) {
  return request<SessionDetails>(`/sessions/${sessionId}/details`);
}

export function connectWallet(sessionId: string, walletId: string) {
  return request<ConnectResult>(
    `/sessions/${sessionId}/connect`,
    { method: "POST", body: JSON.stringify({ wallet_id: walletId }) },
  );
}

export function paySession(sessionId: string, walletId: string) {
  return request<PaymentResult>(`/sessions/${sessionId}/pay`, {
    method: "POST",
    body: JSON.stringify({ wallet_id: walletId }),
  });
}

export function getBalance(sessionId: string) {
  return request<BalanceInfo>(`/sessions/${sessionId}/balance`);
}

export function getOnrampToken(sessionId: string, walletAddress: string) {
  return request<{ session_token: string; onramp_url: string }>(
    `/sessions/${sessionId}/onramp-token`,
    { method: "POST", body: JSON.stringify({ wallet_address: walletAddress }) },
  );
}
