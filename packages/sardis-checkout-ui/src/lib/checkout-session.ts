export const DEMO_CLIENT_SECRET_STORAGE_KEY = "sardis-demo-client-secret";
export const DEMO_CLIENT_SECRET_PARAM = "client_secret";

export function resolvePersistedDemoClientSecret(
  search: string,
  storedSecret: string | null,
): string | null {
  const params = new URLSearchParams(search);
  return params.get(DEMO_CLIENT_SECRET_PARAM) || storedSecret;
}

export function buildDemoUrlWithClientSecret(
  pathname: string,
  search: string,
  clientSecret: string,
): string {
  const params = new URLSearchParams(search);
  params.set(DEMO_CLIENT_SECRET_PARAM, clientSecret);
  const nextSearch = params.toString();
  return nextSearch ? `${pathname}?${nextSearch}` : pathname;
}

export function stripDemoClientSecret(pathname: string, search: string): string {
  const params = new URLSearchParams(search);
  params.delete(DEMO_CLIENT_SECRET_PARAM);
  const nextSearch = params.toString();
  return nextSearch ? `${pathname}?${nextSearch}` : pathname;
}

export function isInternalSardisWalletEnabled(flag: string | undefined): boolean {
  return flag === "true";
}

export function getPreferredCheckoutTab(session: {
  payment_method?: string | null;
  payer_wallet_address?: string | null;
}): "wallet" | "fund" {
  if (session.payment_method === "external_wallet" || session.payer_wallet_address) {
    return "fund";
  }
  return "wallet";
}
