import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { getSessionDetails } from "@/lib/api";
import type { CheckoutStep, SessionDetails, PaymentResult } from "@/lib/types";
import MerchantHeader from "@/components/MerchantHeader";
import TabSwitcher from "@/components/TabSwitcher";
import PayFromWallet from "@/components/PayFromWallet";
import FundAndPay from "@/components/FundAndPay";
import ProcessingView from "@/components/ProcessingView";
import SuccessView from "@/components/SuccessView";
import ErrorView from "@/components/ErrorView";

export default function CheckoutPage() {
  const { clientSecret } = useParams<{ clientSecret: string }>();
  const [searchParams] = useSearchParams();
  const urlEmbedOrigin = useMemo(() => searchParams.get("embed_origin"), [searchParams]);
  const [session, setSession] = useState<SessionDetails | null>(null);
  const [step, setStep] = useState<CheckoutStep>("loading");
  const [tab, setTab] = useState<"wallet" | "fund">("wallet");
  const [error, setError] = useState("");
  const [result, setResult] = useState<PaymentResult | null>(null);

  useEffect(() => {
    if (!clientSecret) return;
    getSessionDetails(clientSecret)
      .then((data) => {
        setSession(data);
        if (data.status === "paid" || data.status === "settled") {
          setStep("success");
        } else if (data.status === "expired") {
          setStep("expired");
        } else {
          setStep("pay");
        }
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load session");
        setStep("error");
      });
  }, [clientSecret]);

  // Notify parent iframe of events (use embed_origin for security, fall back to "*")
  const postToParent = (event: string, data?: Record<string, unknown>) => {
    if (window.parent !== window) {
      // Prefer session-level embed_origin (set at session creation), then URL param (set by embed SDK)
      const targetOrigin = session?.embed_origin || urlEmbedOrigin || "*";
      window.parent.postMessage({ source: "sardis-checkout", event, ...data }, targetOrigin);
    }
  };

  const handleSuccess = (r: PaymentResult) => {
    setResult(r);
    setStep("success");
    postToParent("success", { session_id: r.session_id, tx_hash: r.tx_hash });
  };

  const handleError = (msg: string) => {
    setError(msg);
    setStep("error");
    postToParent("error", { message: msg });
  };

  const handleRetry = () => {
    setError("");
    setStep("pay");
  };

  if (step === "loading") {
    return (
      <Shell>
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin" />
        </div>
      </Shell>
    );
  }

  if (step === "expired") {
    return (
      <Shell>
        <div className="flex flex-col items-center py-10 text-center">
          <div className="w-14 h-14 rounded-full bg-[var(--checkout-bg)] flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-[var(--checkout-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold mb-1" style={{ fontFamily: "var(--font-display)" }}>
            Session Expired
          </h2>
          <p className="text-sm text-[var(--checkout-muted)]">
            This checkout session has expired. Please request a new one.
          </p>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      {session && (
        <MerchantHeader
          merchantName={session.merchant_name}
          logoUrl={session.merchant_logo_url}
          amount={session.amount}
          currency={session.currency}
          description={session.description}
        />
      )}

      {step === "pay" && session && clientSecret && (
        <>
          <TabSwitcher active={tab} onChange={setTab} />
          {tab === "wallet" ? (
            <PayFromWallet
              clientSecret={clientSecret}
              amount={session.amount}
              currency={session.currency}
              settlementAddress={session.settlement_address}
              onSuccess={handleSuccess}
              onError={handleError}
              onProcessing={() => setStep("processing")}
            />
          ) : (
            <FundAndPay
              clientSecret={clientSecret}
              amount={session.amount}
              currency={session.currency}
              settlementAddress={session.settlement_address}
              onSuccess={handleSuccess}
              onError={handleError}
              onProcessing={() => setStep("processing")}
            />
          )}
        </>
      )}

      {step === "processing" && <ProcessingView />}

      {step === "success" && result && (
        <SuccessView result={result} />
      )}

      {step === "error" && (
        <ErrorView message={error} onRetry={handleRetry} />
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t border-[var(--checkout-border)] flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-[var(--checkout-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <span className="text-xs text-[var(--checkout-muted)]">
            Secured by Sardis
          </span>
        </div>
        <span className="text-xs text-[var(--checkout-muted)]">
          Base Network
        </span>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6">
        {children}
      </div>
    </div>
  );
}
