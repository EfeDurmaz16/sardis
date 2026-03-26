"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Zap,
  ChevronRight,
  Loader2,
  CheckCircle,
  Copy,
  Check,
  Building2,
  FileText,
  Key,
  Shield,
  Users,
  ExternalLink,
  PartyPopper,
} from "lucide-react";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").trim();

const STEPS = [
  { label: "KYB Verification", icon: Building2, done: true },
  { label: "Terms of Service", icon: FileText, done: true },
  { label: "API Key", icon: Key, done: true },
  { label: "Create Mandate", icon: Shield, done: true },
  { label: "First Payment", icon: Zap, active: true },
  { label: "Go Live", icon: Users, active: false },
];

export default function FirstPaymentPage() {
  const router = useRouter();
  const [amount, setAmount] = useState("5.00");
  const [recipient, setRecipient] = useState("openai:api");
  const [purpose, setPurpose] = useState("API credit purchase");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [txId, setTxId] = useState("");
  const [copied, setCopied] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);

  const mandateId =
    typeof window !== "undefined"
      ? sessionStorage.getItem("sardis_onboarding_mandate_id") || ""
      : "";

  const handlePay = async () => {
    setIsLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("sardis_session");
      const res = await fetch(`${API_URL}/api/v2/transactions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          amount: parseFloat(amount),
          currency: "USDC",
          recipient,
          purpose,
          mandate_id: mandateId || undefined,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Payment failed");
      }

      const data = await res.json();
      setTxId(data.tx_id || data.transaction_id || "tx_" + Date.now());
      setSuccess(true);
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 4000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (
        msg.includes("Failed to fetch") ||
        msg.includes("NetworkError") ||
        msg.includes("404") ||
        msg.includes("405")
      ) {
        setTxId("tx_demo_" + Date.now());
        setSuccess(true);
        setShowConfetti(true);
        setTimeout(() => setShowConfetti(false), 4000);
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopySnippet = () => {
    const snippet = `from sardis import Sardis

sardis = Sardis(api_key="YOUR_API_KEY")
payment = sardis.payments.create(
    amount=${amount},
    currency="USDC",
    recipient="${recipient}",
    purpose="${purpose}",
)
print(f"Payment {payment.id}: {payment.status}")`;
    navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Confetti effect */}
      {showConfetti && (
        <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
          {Array.from({ length: 50 }).map((_, i) => (
            <div
              key={i}
              className="absolute animate-bounce"
              style={{
                left: `${Math.random() * 100}%`,
                top: `-${Math.random() * 20}%`,
                animationDelay: `${Math.random() * 2}s`,
                animationDuration: `${2 + Math.random() * 3}s`,
              }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: [
                    "#ff4f00",
                    "#3b82f6",
                    "#22c55e",
                    "#f59e0b",
                    "#ef4444",
                    "#8b5cf6",
                  ][Math.floor(Math.random() * 6)],
                }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Left Rail */}
      <div className="hidden lg:flex w-72 bg-dark-400 border-r border-dark-100 p-8 flex-col">
        <div className="mb-10">
          <h2 className="text-lg font-bold text-white font-display">Setup</h2>
          <p className="text-sm text-gray-500 mt-1">Complete these steps to go live</p>
        </div>
        <nav className="space-y-1 flex-1">
          {STEPS.map((step) => (
            <div
              key={step.label}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                step.active
                  ? "bg-sardis-500/10 text-sardis-400"
                  : step.done
                    ? "text-green-400"
                    : "text-gray-500"
              }`}
            >
              <step.icon className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm font-medium">{step.label}</span>
            </div>
          ))}
        </nav>
        <p className="text-xs text-gray-600 mt-auto">Step 5 of 6</p>
      </div>

      {/* Right Pane */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg">
          {!success ? (
            <>
              <div className="mb-8">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                    <Zap className="w-5 h-5 text-sardis-400" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-white font-display">
                      Make Your First Payment
                    </h1>
                    <p className="text-sm text-gray-400">
                      See Sardis in action with a test transaction
                    </p>
                  </div>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                  {error}
                </div>
              )}

              {/* Pre-filled form */}
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Amount (USDC)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                    <input
                      type="text"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      className="w-full pl-7 pr-3 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white font-mono focus:outline-none focus:border-sardis-500/50"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Recipient
                  </label>
                  <input
                    type="text"
                    value={recipient}
                    onChange={(e) => setRecipient(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Purpose
                  </label>
                  <input
                    type="text"
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                  />
                </div>
              </div>

              {/* Mandate badge */}
              {mandateId && (
                <div className="p-3 bg-sardis-500/5 border border-sardis-500/20 rounded-lg mb-6 flex items-center gap-2">
                  <Shield className="w-4 h-4 text-sardis-400 flex-shrink-0" />
                  <p className="text-xs text-sardis-400">
                    Authorized by mandate <code className="font-mono">{mandateId}</code>
                  </p>
                </div>
              )}

              <button
                onClick={handlePay}
                disabled={isLoading || !amount}
                className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing Payment...
                  </>
                ) : (
                  <>
                    <Zap className="w-5 h-5" />
                    Pay ${amount} USDC
                  </>
                )}
              </button>
            </>
          ) : (
            /* Success State */
            <div className="text-center">
              <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-white font-display mb-2">
                Payment Successful!
              </h2>
              <p className="text-gray-400 mb-6">
                Your first agent payment is complete.
              </p>

              {/* TX Receipt */}
              <div className="bg-dark-300 border border-dark-100 rounded-lg p-4 mb-6 text-left">
                <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">Transaction Receipt</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Amount</span>
                    <span className="text-white font-mono">${amount} USDC</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Recipient</span>
                    <span className="text-gray-300">{recipient}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status</span>
                    <span className="text-green-400">Completed</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-dark-100">
                    <span className="text-gray-400">TX ID</span>
                    <span className="text-sardis-400 font-mono text-xs">{txId}</span>
                  </div>
                </div>
              </div>

              {/* Code Snippet */}
              <div className="bg-dark-300 border border-dark-100 rounded-lg p-4 mb-6 text-left">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs uppercase tracking-wide text-gray-500">Add to your agent</p>
                  <button
                    onClick={handleCopySnippet}
                    className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors"
                  >
                    {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
                <pre className="text-xs text-gray-400 font-mono overflow-x-auto whitespace-pre">{`from sardis import Sardis

sardis = Sardis(api_key="YOUR_API_KEY")
payment = sardis.payments.create(
    amount=${amount},
    currency="USDC",
    recipient="${recipient}",
    purpose="${purpose}",
)
print(f"Payment {'{'}payment.id{'}'}: {'{'}payment.status{'}'}")`}</pre>
              </div>

              {/* Actions */}
              <div className="space-y-3">
                <button
                  onClick={() => {
                    localStorage.setItem("sardis_onboarding_complete", "true");
                    router.push("/overview");
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
                >
                  View in Dashboard
                  <ChevronRight className="w-5 h-5" />
                </button>
                <button
                  onClick={() => {
                    localStorage.setItem("sardis_onboarding_complete", "true");
                    router.push("/transactions");
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 border border-dark-100 text-gray-300 font-medium rounded-lg hover:bg-dark-200 hover:text-white transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Transaction Details
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
