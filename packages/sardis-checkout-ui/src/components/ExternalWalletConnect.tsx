import { useState, useEffect, useCallback } from "react";
import { useConnect, useAccount, useDisconnect, useSignMessage } from "wagmi";
import { connectExternalWallet } from "@/lib/api";

interface ExternalWalletConnectProps {
  clientSecret: string;
  onConnected: (address: string) => void;
  onError: (message: string) => void;
}

const CONNECTOR_LABELS: Record<string, { label: string; subtitle: string }> = {
  "Coinbase Wallet": {
    label: "Coinbase Wallet / Smart Wallet",
    subtitle: "Browser extension or passkey-based Smart Wallet",
  },
  WalletConnect: {
    label: "WalletConnect",
    subtitle: "MetaMask, Rainbow, and 300+ wallets",
  },
};

function getConnectorInfo(name: string) {
  return CONNECTOR_LABELS[name] ?? { label: `Connect ${name}`, subtitle: "" };
}

export default function ExternalWalletConnect({
  clientSecret,
  onConnected,
  onError,
}: ExternalWalletConnectProps) {
  const { connectors, connect } = useConnect();
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const { signMessageAsync } = useSignMessage();
  const [verifying, setVerifying] = useState(false);
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verify = useCallback(async () => {
    if (!address || verified || verifying) return;
    setVerifying(true);
    setError(null);
    try {
      const csPrefix = clientSecret.slice(0, 8);
      const message = `Sardis Checkout: connect ${address} to session ${csPrefix}`;
      const signature = await signMessageAsync({ message });
      await connectExternalWallet(clientSecret, {
        address,
        signature,
        message,
      });
      setVerified(true);
      onConnected(address);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Wallet verification failed";
      setError(msg);
      onError(msg);
    } finally {
      setVerifying(false);
    }
  }, [address, clientSecret, verified, verifying, signMessageAsync, onConnected, onError]);

  useEffect(() => {
    if (isConnected && address && !verified && !verifying && !error) {
      verify();
    }
  }, [isConnected, address, verified, verifying, error, verify]);

  if (verified && address) {
    return (
      <div className="flex items-center gap-2 px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
        <span className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-xs text-[var(--checkout-secondary)]">
          Connected
        </span>
        <span
          className="ml-auto text-xs text-[var(--checkout-primary)] truncate max-w-[180px]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {address.slice(0, 6)}...{address.slice(-4)}
        </span>
      </div>
    );
  }

  if (verifying) {
    return (
      <div className="flex items-center justify-center py-3 text-sm text-[var(--checkout-secondary)]">
        <div className="w-4 h-4 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin mr-2" />
        Verifying wallet...
      </div>
    );
  }

  // Error state: show message + retry/disconnect buttons
  if (error && isConnected) {
    return (
      <div className="space-y-3">
        <div className="px-3 py-2.5 rounded-lg bg-red-50 border border-red-200">
          <p className="text-xs text-red-700">{error}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setError(null);
              verify();
            }}
            className="flex-1 py-2.5 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors"
          >
            Try Again
          </button>
          <button
            onClick={() => {
              setError(null);
              disconnect();
            }}
            className="flex-1 py-2.5 px-4 border border-[var(--checkout-border)] text-[var(--checkout-secondary)] font-medium text-sm rounded-lg transition-colors hover:bg-[var(--checkout-bg)]"
          >
            Disconnect
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {connectors.map((connector) => {
        const info = getConnectorInfo(connector.name);
        return (
          <button
            key={connector.uid}
            onClick={() => connect({ connector })}
            className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors text-left"
          >
            <span className="block">{info.label}</span>
            {info.subtitle && (
              <span className="block text-[11px] font-normal opacity-75 mt-0.5">
                {info.subtitle}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
