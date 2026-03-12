import { useState, useEffect, useCallback } from "react";
import { useConnect, useAccount, useDisconnect, useSignTypedData } from "wagmi";
import {
  connectExternalWallet,
  getExternalWalletConnectParams,
} from "@/lib/api";

interface ExternalWalletConnectProps {
  clientSecret: string;
  connectedAddress?: string | null;
  allowReconnect?: boolean;
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

function normalizeAddress(address: string | null | undefined) {
  return address?.toLowerCase() ?? null;
}

export default function ExternalWalletConnect({
  clientSecret,
  connectedAddress,
  allowReconnect = false,
  onConnected,
  onError,
}: ExternalWalletConnectProps) {
  const { connectors, connect } = useConnect();
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();
  const { signTypedDataAsync } = useSignTypedData();
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedConnectedAddress = normalizeAddress(connectedAddress);
  const normalizedAccountAddress = normalizeAddress(address);
  const walletMatchesSession =
    !!normalizedConnectedAddress &&
    normalizedConnectedAddress === normalizedAccountAddress;
  const shouldOfferReconnect =
    !!connectedAddress && allowReconnect && !walletMatchesSession;

  const verify = useCallback(async () => {
    if (!address || verifying) return;
    if (walletMatchesSession) {
      onConnected(address);
      return;
    }

    setVerifying(true);
    setError(null);
    try {
      const params = await getExternalWalletConnectParams(clientSecret, address);
      const { EIP712Domain: _domain, ...types } = params.typed_data.types;
      const signature = await (signTypedDataAsync as (args: {
        domain: Record<string, unknown>;
        types: Record<string, Array<{ name: string; type: string }>>;
        primaryType: string;
        message: Record<string, unknown>;
      }) => Promise<`0x${string}`>)({
        domain: params.typed_data.domain,
        types,
        primaryType: params.typed_data.primaryType,
        message: params.typed_data.message,
      });

      await connectExternalWallet(clientSecret, {
        address,
        signature,
        session_id: params.session_id,
        chain_id: params.chain_id,
        nonce: params.nonce,
      });
      onConnected(address);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Wallet verification failed";
      setError(msg);
      onError(msg);
    } finally {
      setVerifying(false);
    }
  }, [
    address,
    clientSecret,
    onConnected,
    onError,
    signTypedDataAsync,
    verifying,
    walletMatchesSession,
  ]);

  useEffect(() => {
    if (isConnected && address && !verifying && !error && !walletMatchesSession) {
      verify();
    }
  }, [isConnected, address, verifying, error, walletMatchesSession, verify]);

  const renderConnectorButtons = () => (
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

  if (verifying) {
    return (
      <div className="flex items-center justify-center py-3 text-sm text-[var(--checkout-secondary)]">
        <div className="w-4 h-4 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin mr-2" />
        Verifying wallet...
      </div>
    );
  }

  if (error && isConnected && !walletMatchesSession) {
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

  if (connectedAddress) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-3 py-2.5 bg-[var(--checkout-bg)] rounded-lg">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-xs text-[var(--checkout-secondary)]">
            Wallet verified for this checkout
          </span>
          <span
            className="ml-auto text-xs text-[var(--checkout-primary)] truncate max-w-[180px]"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {connectedAddress.slice(0, 6)}...{connectedAddress.slice(-4)}
          </span>
        </div>

        {shouldOfferReconnect && (
          <div className="space-y-3">
            <div className="px-3 py-2.5 rounded-lg bg-blue-50 border border-blue-200">
              <p className="text-xs text-blue-700">
                Reconnect this wallet to authorize the transfer, or connect a
                different wallet to update this checkout session.
              </p>
            </div>

            {isConnected && address && !walletMatchesSession ? (
              <button
                onClick={() => disconnect()}
                className="w-full py-2.5 px-4 border border-[var(--checkout-border)] text-[var(--checkout-secondary)] font-medium text-sm rounded-lg transition-colors hover:bg-[var(--checkout-bg)]"
              >
                Disconnect {address.slice(0, 6)}...{address.slice(-4)}
              </button>
            ) : (
              renderConnectorButtons()
            )}
          </div>
        )}
      </div>
    );
  }

  return renderConnectorButtons();
}
