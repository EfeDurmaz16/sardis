import { useState, useEffect, useCallback } from "react";
import { useConnect, useAccount, useDisconnect, useSignMessage } from "wagmi";
import { connectExternalWallet } from "@/lib/api";

interface ExternalWalletConnectProps {
  clientSecret: string;
  onConnected: (address: string) => void;
  onError: (message: string) => void;
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

  const verify = useCallback(async () => {
    if (!address || verified || verifying) return;
    setVerifying(true);
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
      disconnect();
      onError(e instanceof Error ? e.message : "Wallet verification failed");
    } finally {
      setVerifying(false);
    }
  }, [address, clientSecret, verified, verifying, signMessageAsync, disconnect, onConnected, onError]);

  useEffect(() => {
    if (isConnected && address && !verified && !verifying) {
      verify();
    }
  }, [isConnected, address, verified, verifying, verify]);

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

  return (
    <div className="space-y-2">
      {connectors.map((connector) => (
        <button
          key={connector.uid}
          onClick={() => connect({ connector })}
          className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors"
        >
          Connect {connector.name}
        </button>
      ))}
    </div>
  );
}
