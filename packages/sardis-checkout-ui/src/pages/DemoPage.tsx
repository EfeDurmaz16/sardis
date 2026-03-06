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

const DEMO_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68";
const CDP_APP_ID = "fad58dd4-baf9-48e5-90e5-68a87498872f";

function buildDemoOnrampUrl(): string {
  const params = new URLSearchParams({
    appId: CDP_APP_ID,
    destinationWallets: JSON.stringify([
      { address: DEMO_ADDRESS, assets: ["USDC"], supportedNetworks: ["base"] },
    ]),
    defaultAsset: "USDC",
    defaultNetwork: "base",
    presetFiatAmount: "50",
  });
  return `https://pay.coinbase.com/buy/select-asset?${params.toString()}`;
}

export default function DemoPage() {
  const [step, setStep] = useState<CheckoutStep>("pay");
  const [tab, setTab] = useState<"wallet" | "fund">("wallet");
  const [walletId, setWalletId] = useState("");
  const [connected, setConnected] = useState(false);
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

  const handleDemoConnect = () => {
    if (!walletId.trim()) return;
    setConnected(true);
  };

  const handleOpenOnramp = () => {
    const url = buildDemoOnrampUrl();
    const w = 460;
    const h = 700;
    const left = window.screenX + (window.outerWidth - w) / 2;
    const top = window.screenY + (window.outerHeight - h) / 2;
    window.open(
      url,
      "coinbase-onramp",
      `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no,location=no,status=no`,
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6">
        {/* Demo banner */}
        <div className="mb-4 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-center">
          <span className="text-xs font-medium text-amber-700">
            Demo Mode — No real transactions
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
                  style={{
                    background: walletId.trim()
                      ? "var(--checkout-blue)"
                      : "var(--checkout-border)",
                  }}
                >
                  Pay {MOCK_SESSION.amount} {MOCK_SESSION.currency}
                </button>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                {!connected ? (
                  <>
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
                      onClick={handleDemoConnect}
                      disabled={!walletId.trim()}
                      className="w-full py-3 rounded-lg text-sm font-semibold text-white transition-colors disabled:opacity-40 bg-[var(--checkout-blue)]"
                    >
                      Connect Wallet
                    </button>
                  </>
                ) : (
                  <>
                    {/* Coinbase Onramp */}
                    <div className="rounded-lg border border-[var(--checkout-border)] overflow-hidden">
                      <div className="px-5 py-5 text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                            <rect width="20" height="20" rx="5" fill="#0052FF" />
                            <path
                              d="M10 4a6 6 0 100 12 6 6 0 000-12zm-1.4 3.6a2.4 2.4 0 013.8 1.9h-1.5a.9.9 0 10-.9-.9v-.02h-1.5a2.38 2.38 0 01.1-1z"
                              fill="white"
                            />
                          </svg>
                          <span className="text-sm font-semibold text-[var(--checkout-primary)]">
                            Coinbase Onramp
                          </span>
                        </div>
                        <p className="text-xs text-[var(--checkout-muted)] mb-4">
                          Buy USDC with card or bank transfer
                        </p>
                        <button
                          onClick={handleOpenOnramp}
                          className="w-full py-3 px-4 text-sm font-semibold text-white rounded-lg transition-colors"
                          style={{ background: "#0052FF" }}
                          onMouseOver={(e) =>
                            (e.currentTarget.style.background = "#0040D6")
                          }
                          onMouseOut={(e) =>
                            (e.currentTarget.style.background = "#0052FF")
                          }
                        >
                          Buy {MOCK_SESSION.amount} USDC
                        </button>
                      </div>
                    </div>

                    {/* Balance polling */}
                    <div className="flex items-center justify-between px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-[var(--checkout-secondary)]">
                          Waiting for USDC...
                        </span>
                      </div>
                      <span
                        className="text-sm font-medium"
                        style={{ fontFamily: "var(--font-mono, monospace)" }}
                      >
                        <span className="text-[var(--checkout-usdc)]">0.00</span>{" "}
                        <span className="text-[var(--checkout-muted)]">USDC</span>
                      </span>
                    </div>

                    <p className="text-xs text-center text-[var(--checkout-muted)]">
                      Payment triggers automatically once{" "}
                      {MOCK_SESSION.amount} USDC arrives
                    </p>

                    <div className="text-center">
                      <p className="text-[10px] text-[var(--checkout-muted)] font-mono truncate">
                        {DEMO_ADDRESS}
                      </p>
                    </div>
                  </>
                )}
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
