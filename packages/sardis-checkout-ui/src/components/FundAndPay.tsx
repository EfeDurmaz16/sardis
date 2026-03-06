import { useState, useEffect } from "react";
import { connectWallet, paySession } from "@/lib/api";
import { useBalancePoll } from "@/hooks/useBalancePoll";
import type { PaymentResult } from "@/lib/types";

interface FundAndPayProps {
  sessionId: string;
  amount: string;
  currency: string;
  onSuccess: (result: PaymentResult) => void;
  onError: (message: string) => void;
  onProcessing: () => void;
}

export default function FundAndPay({
  sessionId,
  amount,
  currency,
  onSuccess,
  onError,
  onProcessing,
}: FundAndPayProps) {
  const [walletId, setWalletId] = useState("");
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [autoPaying, setAutoPaying] = useState(false);

  const { balance } = useBalancePoll(sessionId, connected, 5000);
  const hasEnough = parseFloat(balance) >= parseFloat(amount);

  // Auto-trigger payment when balance is sufficient
  useEffect(() => {
    if (connected && hasEnough && !autoPaying) {
      setAutoPaying(true);
      onProcessing();
      paySession(sessionId, walletId)
        .then(onSuccess)
        .catch((e) => {
          setAutoPaying(false);
          onError(e instanceof Error ? e.message : "Payment failed");
        });
    }
  }, [connected, hasEnough, autoPaying, sessionId, walletId, amount, onSuccess, onError, onProcessing]);

  const handleConnect = async () => {
    if (!walletId.trim()) return;
    setConnecting(true);
    try {
      await connectWallet(sessionId, walletId);
      setConnected(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  };

  if (!connected) {
    return (
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-[var(--checkout-secondary)] mb-1.5 uppercase tracking-wider">
            Wallet ID
          </label>
          <input
            type="text"
            placeholder="wal_..."
            value={walletId}
            onChange={(e) => setWalletId(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border border-[var(--checkout-border)] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[var(--checkout-blue)] focus:border-transparent"
            style={{ fontFamily: "var(--font-mono)" }}
          />
        </div>
        <button
          onClick={handleConnect}
          disabled={connecting || !walletId.trim()}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {connecting ? "Connecting..." : "Connect Wallet"}
        </button>
      </div>
    );
  }

  const CDP_APP_ID = import.meta.env.VITE_COINBASE_APP_ID || "fad58dd4-baf9-48e5-90e5-68a87498872f";

  const onrampParams = new URLSearchParams({
    appId: CDP_APP_ID,
    destinationWallets: JSON.stringify([
      { address: walletId, assets: ["USDC"], supportedNetworks: ["base"] },
    ]),
    defaultAsset: "USDC",
    defaultNetwork: "base",
    presetFiatAmount: String(Math.ceil(parseFloat(amount))),
  });

  const onrampUrl = `https://pay.coinbase.com/buy/select-asset?${onrampParams.toString()}`;

  return (
    <div className="space-y-4">
      {/* Coinbase Onramp */}
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
        <a
          href={onrampUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block px-5 py-2.5 text-sm font-medium text-white bg-[#0052FF] hover:bg-[#003ECB] rounded-lg transition-colors"
        >
          Buy {amount} USDC
        </a>
      </div>

      {/* Balance polling indicator */}
      <div className="flex items-center justify-between px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--checkout-blue)] animate-pulse-dot" />
          <span className="text-xs text-[var(--checkout-secondary)]">
            Watching for funds...
          </span>
        </div>
        <span className="text-sm font-medium" style={{ fontFamily: "var(--font-mono)" }}>
          <span className="text-[var(--checkout-usdc)]">{parseFloat(balance).toFixed(2)}</span>{" "}
          <span className="text-[var(--checkout-muted)]">{currency}</span>
        </span>
      </div>

      <p className="text-xs text-center text-[var(--checkout-muted)]">
        Payment will trigger automatically once {amount} {currency} arrives in your wallet
      </p>
    </div>
  );
}
