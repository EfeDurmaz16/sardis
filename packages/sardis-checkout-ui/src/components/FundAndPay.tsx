import { useState, useEffect, useCallback } from "react";
import { useWriteContract } from "wagmi";
import { parseUnits, type Address } from "viem";
import { connectWallet, paySession, getOnrampToken, confirmExternalPayment } from "@/lib/api";
import { useBalancePoll } from "@/hooks/useBalancePoll";
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
] as const;

interface FundAndPayProps {
  clientSecret: string;
  amount: string;
  currency: string;
  settlementAddress: string | null;
  onSuccess: (result: PaymentResult) => void;
  onError: (message: string) => void;
  onProcessing: () => void;
}

function openOnrampPopup(): Window | null {
  const w = 460;
  const h = 700;
  const left = window.screenX + (window.outerWidth - w) / 2;
  const top = window.screenY + (window.outerHeight - h) / 2;
  return window.open(
    "about:blank",
    "coinbase-onramp",
    `width=${w},height=${h},left=${left},top=${top},toolbar=no,menubar=no,location=no,status=no`,
  );
}

export default function FundAndPay({
  clientSecret,
  amount,
  currency,
  settlementAddress,
  onSuccess,
  onError,
  onProcessing,
}: FundAndPayProps) {
  // External wallet state
  const [externalAddress, setExternalAddress] = useState<string | null>(null);
  const [showSardisWallet, setShowSardisWallet] = useState(false);

  // Sardis wallet state
  const [walletId, setWalletId] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [sardisConnected, setSardisConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);

  // Shared state
  const [autoPaying, setAutoPaying] = useState(false);
  const [onrampLoading, setOnrampLoading] = useState(false);
  const [onrampOpened, setOnrampOpened] = useState(false);

  // Determine which wallet is connected
  const isConnected = !!externalAddress || sardisConnected;
  const activeAddress = externalAddress || walletAddress;

  const { balance } = useBalancePoll(clientSecret, sardisConnected, 5000);
  // For external wallet, we only need enough to trigger the onramp
  const hasEnough = parseFloat(balance) >= parseFloat(amount);

  const { writeContractAsync } = useWriteContract();

  // Auto-trigger payment when balance is sufficient (Sardis wallet flow)
  useEffect(() => {
    if (sardisConnected && hasEnough && !autoPaying && !externalAddress) {
      setAutoPaying(true);
      onProcessing();
      paySession(clientSecret, walletId)
        .then(onSuccess)
        .catch((e) => {
          setAutoPaying(false);
          onError(e instanceof Error ? e.message : "Payment failed");
        });
    }
  }, [sardisConnected, hasEnough, autoPaying, clientSecret, walletId, externalAddress, onSuccess, onError, onProcessing]);

  const handleSardisConnect = useCallback(async () => {
    if (!walletId.trim()) return;
    setConnecting(true);
    try {
      const result = await connectWallet(clientSecret, walletId);
      setWalletAddress(result.wallet_address);
      setSardisConnected(true);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to connect wallet");
    } finally {
      setConnecting(false);
    }
  }, [clientSecret, walletId, onError]);

  const handleOpenOnramp = useCallback(async () => {
    if (!activeAddress) {
      onError("Connect a wallet first to buy USDC");
      return;
    }
    const popup = openOnrampPopup();
    setOnrampLoading(true);
    try {
      const { onramp_url } = await getOnrampToken(clientSecret, activeAddress);
      if (popup && !popup.closed) {
        popup.location.href = onramp_url;
      }
      setOnrampOpened(true);
    } catch (e) {
      if (popup && !popup.closed) popup.close();
      onError(e instanceof Error ? e.message : "Failed to start Coinbase Onramp");
    } finally {
      setOnrampLoading(false);
    }
  }, [clientSecret, activeAddress, onError]);

  const handleExternalPay = useCallback(async () => {
    if (!externalAddress || !settlementAddress) return;
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
      onError(e instanceof Error ? e.message : "Payment failed");
    }
  }, [externalAddress, settlementAddress, amount, clientSecret, writeContractAsync, onProcessing, onSuccess, onError]);

  // Step 1: Connect wallet
  if (!isConnected) {
    return (
      <div className="space-y-4">
        <ExternalWalletConnect
          clientSecret={clientSecret}
          onConnected={(addr) => setExternalAddress(addr)}
          onError={onError}
        />

        {import.meta.env.VITE_SHOW_SARDIS_WALLET === "true" && (
          <>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-[var(--checkout-border)]" />
              <span className="text-xs text-[var(--checkout-muted)]">or</span>
              <div className="flex-1 h-px bg-[var(--checkout-border)]" />
            </div>

            <button
              onClick={() => setShowSardisWallet(!showSardisWallet)}
              className="w-full text-left text-xs text-[var(--checkout-secondary)] hover:text-[var(--checkout-primary)] transition-colors"
            >
              {showSardisWallet ? "Hide" : "Use Sardis Wallet ID"}
            </button>

            {showSardisWallet && (
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
                    className="w-full px-3 py-2.5 text-sm border border-[var(--checkout-border)] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[var(--checkout-blue)] focus:border-transparent"
                    style={{ fontFamily: "var(--font-mono)" }}
                  />
                </div>
                <button
                  onClick={handleSardisConnect}
                  disabled={connecting || !walletId.trim()}
                  className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connecting ? "Connecting..." : "Connect Wallet"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // Step 2: Buy USDC via Coinbase Onramp + pay
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

      {/* External wallet: manual pay after onramp */}
      {externalAddress && settlementAddress && onrampOpened && (
        <button
          onClick={handleExternalPay}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors"
        >
          Pay {amount} {currency}
        </button>
      )}

      {/* Balance polling (Sardis wallet) */}
      {sardisConnected && (
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
      )}

      {sardisConnected && (
        <p className="text-xs text-center text-[var(--checkout-muted)]">
          Payment triggers automatically once {amount} {currency} arrives in your wallet
        </p>
      )}

      {/* Wallet info */}
      {activeAddress && (
        <div className="text-center">
          <p className="text-[10px] text-[var(--checkout-muted)] font-mono truncate">
            {activeAddress}
          </p>
        </div>
      )}
    </div>
  );
}
