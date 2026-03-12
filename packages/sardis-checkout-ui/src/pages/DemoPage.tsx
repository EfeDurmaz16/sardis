import { useState, useCallback, useEffect } from "react";
import type { CheckoutStep, PaymentResult, SessionDetails } from "@/lib/types";
import { getSessionDetails } from "@/lib/api";
import {
  buildDemoUrlWithClientSecret,
  DEMO_CLIENT_SECRET_STORAGE_KEY,
  getPreferredCheckoutTab,
  resolvePersistedDemoClientSecret,
  stripDemoClientSecret,
} from "@/lib/checkout-session";
import MerchantHeader from "@/components/MerchantHeader";
import SuccessView from "@/components/SuccessView";
import FundAndPay from "@/components/FundAndPay";
import PayFromWallet from "@/components/PayFromWallet";
import TabSwitcher from "@/components/TabSwitcher";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v2/merchant-checkout";

const MOCK_SESSION = {
  session_id: "mcs_demo_preview",
  merchant_name: "Sardis Demo Store",
  merchant_logo_url: null,
  amount: "49.99",
  currency: "USDC",
  description: "Premium Plan — Monthly",
  status: "pending",
  payment_method: null,
  payer_wallet_address: null,
  expires_at: null,
  embed_origin: null,
  settlement_address: null,
};

function getStepForStatus(status: string): CheckoutStep {
  if (status === "paid" || status === "settled") return "success";
  if (status === "expired") return "expired";
  return "pay";
}

function getPersistedDemoClientSecret() {
  if (typeof window === "undefined") return null;
  return resolvePersistedDemoClientSecret(
    window.location.search,
    window.sessionStorage.getItem(DEMO_CLIENT_SECRET_STORAGE_KEY),
  );
}

function persistDemoClientSecret(clientSecret: string) {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(DEMO_CLIENT_SECRET_STORAGE_KEY, clientSecret);
  window.history.replaceState(
    {},
    "",
    buildDemoUrlWithClientSecret(
      window.location.pathname,
      window.location.search,
      clientSecret,
    ),
  );
}

function clearPersistedDemoClientSecret() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(DEMO_CLIENT_SECRET_STORAGE_KEY);
  window.history.replaceState(
    {},
    "",
    stripDemoClientSecret(window.location.pathname, window.location.search),
  );
}

export default function DemoPage() {
  const [step, setStep] = useState<CheckoutStep>("pay");
  const [tab, setTab] = useState<"wallet" | "fund">("fund");
  const [result, setResult] = useState<PaymentResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [liveSecret, setLiveSecret] = useState<string | null>(null);
  const [liveSession, setLiveSession] = useState<SessionDetails | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const applySession = (clientSecret: string, session: SessionDetails) => {
      if (cancelled) return;
      setLiveSecret(clientSecret);
      setLiveSession(session);
      setTab(getPreferredCheckoutTab(session));
      setStep(getStepForStatus(session.status));
    };

    const loadExistingSession = async (clientSecret: string) => {
      const session = await getSessionDetails(clientSecret);
      if (["expired", "paid", "settled", "failed"].includes(session.status)) {
        return false;
      }
      applySession(clientSecret, session);
      return true;
    };

    const createFreshSession = async () => {
      const response = await fetch(`${API_BASE}/create-test-session`, {
        method: "POST",
      });
      if (!response.ok) return;

      const data = await response.json().catch(() => null);
      if (!data?.client_secret) return;

      persistDemoClientSecret(data.client_secret);
      await loadExistingSession(data.client_secret);
    };

    const bootstrap = async () => {
      setLoadingSession(true);
      try {
        const persistedClientSecret = getPersistedDemoClientSecret();
        if (persistedClientSecret) {
          try {
            const restored = await loadExistingSession(persistedClientSecret);
            if (restored) return;
            clearPersistedDemoClientSecret();
          } catch {
            clearPersistedDemoClientSecret();
          }
        }

        await createFreshSession();
      } catch {
        clearPersistedDemoClientSecret();
      } finally {
        if (!cancelled) setLoadingSession(false);
      }
    };

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleSuccess = useCallback((r: PaymentResult) => {
    setResult(r);
    setStep("success");
  }, []);

  const handleError = useCallback((msg: string) => {
    setError(msg);
  }, []);

  const handleProcessing = useCallback(() => {
    setStep("processing");
  }, []);

  const handleExternalWalletConnected = useCallback((address: string) => {
    setLiveSession((current) => {
      if (!current) return current;
      return {
        ...current,
        payment_method: "external_wallet",
        payer_wallet_address: address,
      };
    });
  }, []);

  const sessionData = liveSession ?? MOCK_SESSION;

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6">
        <div className="mb-4 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-center">
          <span className="text-xs font-medium text-amber-700">
            {liveSecret ? "Staging Mode — Testnet transactions" : "Demo Mode — Session unavailable"}
          </span>
        </div>

        <MerchantHeader
          merchantName={sessionData.merchant_name}
          logoUrl={sessionData.merchant_logo_url ?? null}
          amount={sessionData.amount}
          currency={sessionData.currency}
          description={sessionData.description}
        />

        {step === "pay" && (
          <>
            <TabSwitcher active={tab} onChange={setTab} />

            {error && (
              <div className="mb-4 px-3 py-2 rounded-lg bg-red-50 border border-red-200">
                <p className="text-xs text-red-700">{error}</p>
              </div>
            )}

            {loadingSession ? (
              <div className="flex items-center justify-center py-6">
                <div className="w-5 h-5 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin" />
              </div>
            ) : !liveSecret || !liveSession ? (
              <div className="px-3 py-4 rounded-lg bg-blue-50 border border-blue-200 text-center">
                <p className="text-xs text-blue-700">
                  Staging checkout is temporarily unavailable. Please reload the
                  page to create a new test session.
                </p>
              </div>
            ) : tab === "wallet" ? (
              <div className="mt-4">
                <PayFromWallet
                  clientSecret={liveSecret}
                  amount={liveSession.amount}
                  currency={liveSession.currency}
                  settlementAddress={liveSession.settlement_address}
                  verifiedExternalAddress={liveSession.payer_wallet_address}
                  onExternalWalletConnected={handleExternalWalletConnected}
                  onSuccess={handleSuccess}
                  onError={handleError}
                  onProcessing={handleProcessing}
                />
              </div>
            ) : (
              <div className="mt-4">
                <FundAndPay
                  clientSecret={liveSecret}
                  amount={liveSession.amount}
                  currency={liveSession.currency}
                  settlementAddress={liveSession.settlement_address}
                  verifiedExternalAddress={liveSession.payer_wallet_address}
                  onExternalWalletConnected={handleExternalWalletConnected}
                  onSuccess={handleSuccess}
                  onError={handleError}
                  onProcessing={handleProcessing}
                />
              </div>
            )}
          </>
        )}

        {step === "processing" && (
          <div className="flex flex-col items-center py-10">
            <div className="w-10 h-10 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin mb-4" />
            <p className="text-sm font-medium">Processing payment...</p>
          </div>
        )}

        {step === "success" && result && <SuccessView result={result} />}

        <div className="mt-8 pt-4 border-t border-[var(--checkout-border)] flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <svg
              className="w-3.5 h-3.5 text-[var(--checkout-muted)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
            <span className="text-xs text-[var(--checkout-muted)]">
              Secured by Sardis
            </span>
          </div>
          <span className="text-xs text-[var(--checkout-muted)]">Base Network</span>
        </div>
      </div>
    </div>
  );
}
