import { useState, useCallback } from "react";
import { useWriteContract } from "wagmi";
import { parseUnits, type Address } from "viem";
import { connectWallet, paySession, getBalance, confirmExternalPayment } from "@/lib/api";
import { USDC_ADDRESS, USDC_DECIMALS } from "@/lib/wallet-config";
import ExternalWalletConnect from "./ExternalWalletConnect";
import type { PaymentResult } from "@/lib/types";

const ERC20_TRANSFER_ABI = [
  {
    name: "transfer",
    type: "function",
    stateMutability: "nonpayable",
    inputs: [
      { name: "to", type: "address" },
      { name: "amount", type: "uint256" },
    ],
    outputs: [{ type: "bool" }],
  },
  {
    name: "balanceOf",
    type: "function",
    stateMutability: "view",
    inputs: [{ name: "account", type: "address" }],
    outputs: [{ type: "uint256" }],
  },
] as const;

interface PayFromWalletProps {
  clientSecret: string;
  amount: string;
  currency: string;
  settlementAddress: string | null;
  onSuccess: (result: PaymentResult) => void;
  onError: (message: string) => void;
  onProcessing: () => void;
}

export default function PayFromWallet({
  clientSecret,
  amount,
  currency,
  settlementAddress,
  onSuccess,
  onError,
  onProcessing,
}: PayFromWalletProps) {
  const [externalAddress, setExternalAddress] = useState<string | null>(null);
  const [showSardisWallet, setShowSardisWallet] = useState(false);
  const [paying, setPaying] = useState(false);

  // Sardis wallet state
  const [walletId, setWalletId] = useState("");
  const [balance, setBalance] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  // wagmi write contract for external wallet USDC transfer
  const { writeContractAsync } = useWriteContract();

  const handleExternalPay = useCallback(async () => {
    if (!externalAddress || !settlementAddress) return;
    setPaying(true);
    onProcessing();
    try {
      const txHash = await writeContractAsync({
        address: USDC_ADDRESS as Address,
        abi: ERC20_TRANSFER_ABI,
        functionName: "transfer",
        args: [
          settlementAddress as Address,
          parseUnits(amount, USDC_DECIMALS),
        ],
      });

      const result = await confirmExternalPayment(clientSecret, {
        tx_hash: txHash,
        address: externalAddress,
      });
      onSuccess(result);
    } catch (e) {
      setPaying(false);
      onError(e instanceof Error ? e.message : "Payment failed");
    }
  }, [externalAddress, settlementAddress, amount, clientSecret, writeContractAsync, onProcessing, onSuccess, onError]);

  // Sardis wallet handlers
  const handleSardisConnect = async () => {
    if (!walletId.trim()) return;
    setLoading(true);
    try {
      await connectWallet(clientSecret, walletId);
      const balData = await getBalance(clientSecret);
      setBalance(balData.balance);
      setConnected(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setLoading(false);
    }
  };

  const handleSardisPay = async () => {
    onProcessing();
    try {
      const result = await paySession(clientSecret, walletId);
      onSuccess(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Payment failed");
    }
  };

  const sardisHasEnough =
    balance !== null && parseFloat(balance) >= parseFloat(amount);

  return (
    <div className="space-y-4">
      {/* Primary: External Wallet via WalletConnect / Coinbase Wallet */}
      <ExternalWalletConnect
        clientSecret={clientSecret}
        onConnected={(addr) => setExternalAddress(addr)}
        onError={onError}
      />

      {externalAddress && settlementAddress && (
        <button
          onClick={handleExternalPay}
          disabled={paying}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {paying ? "Confirming..." : `Pay ${amount} ${currency}`}
        </button>
      )}

      {externalAddress && !settlementAddress && (
        <p className="text-xs text-center text-[var(--checkout-muted)]">
          Merchant settlement address not configured. Use Sardis wallet instead.
        </p>
      )}

      {/* Divider */}
      {!externalAddress && (
        <>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-[var(--checkout-border)]" />
            <span className="text-xs text-[var(--checkout-muted)]">or</span>
            <div className="flex-1 h-px bg-[var(--checkout-border)]" />
          </div>

          {/* Secondary: Sardis Wallet ID */}
          <button
            onClick={() => setShowSardisWallet(!showSardisWallet)}
            className="w-full text-left text-xs text-[var(--checkout-secondary)] hover:text-[var(--checkout-primary)] transition-colors"
          >
            {showSardisWallet ? "Hide" : "Use Sardis Wallet ID"}
          </button>
        </>
      )}

      {showSardisWallet && !externalAddress && (
        <div className="space-y-3">
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
              onClick={handleSardisConnect}
              disabled={loading || !walletId.trim()}
              className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Connecting..." : "Connect Wallet"}
            </button>
          ) : (
            <button
              onClick={handleSardisPay}
              disabled={!sardisHasEnough}
              className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sardisHasEnough
                ? `Pay ${amount} ${currency}`
                : "Insufficient balance"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
