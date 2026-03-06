import { useState } from "react";
import { connectWallet, paySession, getBalance } from "@/lib/api";
import type { PaymentResult } from "@/lib/types";

interface PayFromWalletProps {
  sessionId: string;
  amount: string;
  currency: string;
  onSuccess: (result: PaymentResult) => void;
  onError: (message: string) => void;
  onProcessing: () => void;
}

export default function PayFromWallet({
  sessionId,
  amount,
  currency,
  onSuccess,
  onError,
  onProcessing,
}: PayFromWalletProps) {
  const [walletId, setWalletId] = useState("");
  const [balance, setBalance] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleConnect = async () => {
    if (!walletId.trim()) return;
    setLoading(true);
    try {
      await connectWallet(sessionId, walletId);
      const balData = await getBalance(sessionId);
      setBalance(balData.balance);
      setConnected(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setLoading(false);
    }
  };

  const handlePay = async () => {
    onProcessing();
    try {
      const result = await paySession(sessionId, walletId);
      onSuccess(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Payment failed");
    }
  };

  const hasEnough =
    balance !== null && parseFloat(balance) >= parseFloat(amount);

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
          disabled={connected}
          className="w-full px-3 py-2.5 text-sm border border-[var(--checkout-border)] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[var(--checkout-blue)] focus:border-transparent disabled:opacity-50 disabled:bg-[var(--checkout-bg)]"
          style={{ fontFamily: "var(--font-mono)" }}
        />
      </div>

      {connected && balance !== null && (
        <div className="flex items-center justify-between px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
          <span className="text-xs text-[var(--checkout-secondary)] uppercase tracking-wider">
            Balance
          </span>
          <span
            className="text-sm font-medium"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            <span className="text-[var(--checkout-usdc)]">
              {parseFloat(balance).toFixed(2)}
            </span>{" "}
            <span className="text-[var(--checkout-muted)]">{currency}</span>
          </span>
        </div>
      )}

      {!connected ? (
        <button
          onClick={handleConnect}
          disabled={loading || !walletId.trim()}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Connecting..." : "Connect Wallet"}
        </button>
      ) : (
        <button
          onClick={handlePay}
          disabled={!hasEnough}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {hasEnough
            ? `Pay ${amount} ${currency}`
            : "Insufficient balance"}
        </button>
      )}
    </div>
  );
}
