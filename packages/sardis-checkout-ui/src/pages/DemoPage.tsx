import { useState } from "react";
import type { CheckoutStep, PaymentResult } from "@/lib/types";
import MerchantHeader from "@/components/MerchantHeader";
import TabSwitcher from "@/components/TabSwitcher";
import SuccessView from "@/components/SuccessView";

const MOCK_SESSION = {
  session_id: "mcs_demo_preview",
  merchant_name: "Sardis Demo Store",
  amount: "49.99",
  currency: "USDC",
  description: "Premium Plan — Monthly",
};

export default function DemoPage() {
  const [step, setStep] = useState<CheckoutStep>("pay");
  const [tab, setTab] = useState<"wallet" | "fund">("wallet");
  const [walletId, setWalletId] = useState("");
  const [result, setResult] = useState<PaymentResult | null>(null);

  const handleDemoPay = () => {
    if (!walletId.trim()) return;
    setStep("processing");
    setTimeout(() => {
      const r: PaymentResult = {
        session_id: MOCK_SESSION.session_id,
        status: "paid",
        tx_hash: "0xdemo...preview",
        amount: MOCK_SESSION.amount,
        currency: MOCK_SESSION.currency,
        merchant_id: "merch_demo",
      };
      setResult(r);
      setStep("success");
    }, 2000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6">
        {/* Demo banner */}
        <div className="mb-4 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-center">
          <span className="text-xs font-medium text-amber-700">Demo Mode — No real transactions</span>
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
            {tab === "wallet" ? (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="block text-xs font-medium text-[var(--checkout-muted)] mb-1.5">
                    Wallet ID
                  </label>
                  <input
                    type="text"
                    value={walletId}
                    onChange={(e) => setWalletId(e.target.value)}
                    placeholder="wal_..."
                    className="w-full px-3 py-2.5 text-sm rounded-lg border border-[var(--checkout-border)] bg-[var(--checkout-bg)] outline-none focus:border-[var(--checkout-blue)] transition-colors"
                  />
                </div>
                <button
                  onClick={handleDemoPay}
                  disabled={!walletId.trim()}
                  className="w-full py-3 rounded-lg text-sm font-semibold text-white transition-colors disabled:opacity-40"
                  style={{ background: walletId.trim() ? "var(--checkout-blue)" : "var(--checkout-border)" }}
                >
                  Pay {MOCK_SESSION.amount} {MOCK_SESSION.currency}
                </button>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="border border-[var(--checkout-border)] rounded-lg p-5 text-center">
                  <div className="w-10 h-10 mx-auto mb-3 bg-[#0052FF] rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 15.5c-3.03 0-5.5-2.47-5.5-5.5S8.97 6.5 12 6.5s5.5 2.47 5.5 5.5-2.47 5.5-5.5 5.5z"/>
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-[var(--checkout-primary)] mb-1">
                    Buy USDC with Coinbase
                  </p>
                  <p className="text-xs text-[var(--checkout-muted)] mb-3">
                    Purchase USDC with card or bank transfer — 0% fee
                  </p>
                  <span className="inline-block px-5 py-2.5 text-sm font-medium text-white bg-[#0052FF] rounded-lg opacity-60 cursor-not-allowed">
                    Buy {MOCK_SESSION.amount} USDC
                  </span>
                  <p className="mt-2 text-xs text-[var(--checkout-muted)]">
                    Onramp opens in a new tab during live sessions
                  </p>
                </div>
                <div className="flex items-center justify-between px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--checkout-blue)] animate-pulse" />
                    <span className="text-xs text-[var(--checkout-secondary)]">
                      Watching for funds...
                    </span>
                  </div>
                  <span className="text-sm font-medium" style={{ fontFamily: "var(--font-mono, monospace)" }}>
                    <span className="text-[var(--checkout-usdc)]">0.00</span>{" "}
                    <span className="text-[var(--checkout-muted)]">USDC</span>
                  </span>
                </div>
                <p className="text-xs text-center text-[var(--checkout-muted)]">
                  Payment triggers automatically once {MOCK_SESSION.amount} USDC arrives
                </p>
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
            <svg className="w-3.5 h-3.5 text-[var(--checkout-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="text-xs text-[var(--checkout-muted)]">Secured by Sardis</span>
          </div>
          <span className="text-xs text-[var(--checkout-muted)]">Base Network</span>
        </div>
      </div>
    </div>
  );
}
