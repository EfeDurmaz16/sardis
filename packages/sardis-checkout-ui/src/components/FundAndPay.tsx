import { useState, useEffect, useCallback } from "react";
import { connectWallet, paySession, getOnrampToken } from "@/lib/api";
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

function openOnrampPopup(url: string) {
  const w = 460;
  const h = 700;
  const left = window.screenX + (window.outerWidth - w) / 2;
  const top = window.screenY + (window.outerHeight - h) / 2;
  window.open(
    url,
    "coinbase-onramp",
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no,location=no,status=no`,
  );
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
  const [walletAddress, setWalletAddress] = useState("");
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [autoPaying, setAutoPaying] = useState(false);
  const [onrampLoading, setOnrampLoading] = useState(false);
  const [onrampOpened, setOnrampOpened] = useState(false);

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

  const handleConnect = useCallback(async () => {
    if (!walletId.trim()) return;
    setConnecting(true);
    try {
      const result = await connectWallet(sessionId, walletId);
      setWalletAddress(result.wallet_address);
      setConnected(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  }, [sessionId, walletId, onError]);

  const handleOpenOnramp = useCallback(async () => {
    if (!walletAddress) return;
    setOnrampLoading(true);
    try {
      const { onramp_url } = await getOnrampToken(sessionId, walletAddress);
      openOnrampPopup(onramp_url);
      setOnrampOpened(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to start Coinbase Onramp");
    } finally {
      setOnrampLoading(false);
    }
  }, [sessionId, walletAddress, onError]);

  // Step 1: Connect wallet
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

  // Step 2: Buy USDC via Coinbase Onramp + poll balance
  return (
    <div className="space-y-4">
      {/* Coinbase Onramp */}
      <div className="rounded-lg border border-[var(--checkout-border)] overflow-hidden">
        <div className="px-5 py-5 text-center">
          <p className="text-sm font-semibold text-[var(--checkout-primary)] mb-1">
            Buy USDC with Coinbase
          </p>
          <p className="text-xs text-[var(--checkout-muted)] mb-4">
            Purchase with card or bank transfer
          </p>
          <button
            onClick={handleOpenOnramp}
            disabled={onrampLoading}
            className="w-full py-3 px-4 text-sm font-semibold text-white rounded-lg transition-colors disabled:opacity-70"
            style={{ background: "#0052FF" }}
            onMouseOver={(e) => !onrampLoading && (e.currentTarget.style.background = "#0040D6")}
            onMouseOut={(e) => !onrampLoading && (e.currentTarget.style.background = "#0052FF")}
          >
            {onrampLoading ? "Opening Coinbase..." : `Buy ${amount} ${currency}`}
          </button>
        </div>
      </div>

      {/* Balance polling */}
      <div className="flex items-center justify-between px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ background: onrampOpened ? "#22c55e" : "var(--checkout-blue)" }}
          />
          <span className="text-xs text-[var(--checkout-secondary)]">
            {onrampOpened ? "Waiting for USDC..." : "Watching for funds..."}
          </span>
        </div>
        <span className="text-sm font-medium" style={{ fontFamily: "var(--font-mono)" }}>
          <span className="text-[var(--checkout-usdc)]">
            {parseFloat(balance).toFixed(2)}
          </span>{" "}
          <span className="text-[var(--checkout-muted)]">{currency}</span>
        </span>
      </div>

      <p className="text-xs text-center text-[var(--checkout-muted)]">
        Payment triggers automatically once {amount} {currency} arrives in your wallet
      </p>

      {/* Wallet info */}
      <div className="text-center">
        <p className="text-[10px] text-[var(--checkout-muted)] font-mono truncate">
          {walletAddress}
        </p>
      </div>
    </div>
  );
}
