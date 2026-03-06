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

  return (
    <div className="space-y-4">
      {/* Coinbase Onramp placeholder */}
      <div className="border-2 border-dashed border-[var(--checkout-border)] rounded-lg p-6 text-center">
        <div className="w-10 h-10 mx-auto mb-3 bg-[#0052FF] rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">CB</span>
        </div>
        <p className="text-sm font-medium text-[var(--checkout-primary)] mb-1">
          Coinbase Onramp
        </p>
        <p className="text-xs text-[var(--checkout-muted)]">
          Purchase USDC with card or bank transfer — 0% fee
        </p>
        <a
          href={`https://pay.coinbase.com/buy?appId=sardis&addresses={"${walletId}":["base"]}&assets=["USDC"]&presetFiatAmount=${amount}`}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block px-4 py-2 text-sm font-medium text-white bg-[#0052FF] hover:bg-[#003ECB] rounded-lg transition-colors"
        >
          Buy USDC
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
