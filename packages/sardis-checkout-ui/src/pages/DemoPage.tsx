import { useState, useCallback, useEffect } from "react";
import type { CheckoutStep, PaymentResult } from "@/lib/types";
import MerchantHeader from "@/components/MerchantHeader";
import SuccessView from "@/components/SuccessView";
import FundAndPay from "@/components/FundAndPay";
import PayFromWallet from "@/components/PayFromWallet";
import TabSwitcher from "@/components/TabSwitcher";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v2/merchant-checkout";

const MOCK_SESSION = {
  session_id: "mcs_demo_preview",
  merchant_name: "Sardis Demo Store",
  amount: "49.99",
  currency: "USDC",
  description: "Premium Plan — Monthly",
};

export default function DemoPage() {
  const [step, setStep] = useState<CheckoutStep>("pay");
  const [tab, setTab] = useState<"wallet" | "fund">("fund");
  const [result, setResult] = useState<PaymentResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Try to create a staging test session for real wallet flows
  const [liveSecret, setLiveSecret] = useState<string | null>(null);
  const [liveSettlement, setLiveSettlement] = useState<string | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/create-test-session`, { method: "POST" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.client_secret) {
          setLiveSecret(data.client_secret);
          setLiveSettlement(data.settlement_address ?? null);
        }
      })
      .catch(() => {})
      .finally(() => setLoadingSession(false));
  }, []);

  const clientSecret = liveSecret ?? "demo_preview";

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

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6">
        {/* Demo banner */}
        <div className="mb-4 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-center">
          <span className="text-xs font-medium text-amber-700">
            {liveSecret ? "Staging Mode — Testnet transactions" : "Demo Mode — No real transactions"}
          </span>
        </div>

        <MerchantHeader
          merchantName={MOCK_SESSION.merchant_name}
          logoUrl={null}
          amount={MOCK_SESSION.amount}
          currency={MOCK_SESSION.currency}
          description={MOCK_SESSION.description}
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
            ) : tab === "wallet" ? (
              <div className="mt-4">
                {liveSecret ? (
                  <PayFromWallet
                    clientSecret={clientSecret}
                    amount={MOCK_SESSION.amount}
                    currency={MOCK_SESSION.currency}
                    settlementAddress={liveSettlement}
                    onSuccess={handleSuccess}
                    onError={handleError}
                    onProcessing={handleProcessing}
                  />
                ) : (
                  <div className="px-3 py-4 rounded-lg bg-blue-50 border border-blue-200 text-center">
                    <p className="text-xs text-blue-700">
                      Wallet connection requires a live session. Switch to the
                      staging environment or use the Fund &amp; Pay tab.
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-4">
                <FundAndPay
                  clientSecret={clientSecret}
                  amount={MOCK_SESSION.amount}
                  currency={MOCK_SESSION.currency}
                  settlementAddress={liveSettlement}
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

        {/* Footer */}
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
