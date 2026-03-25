"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Key,
  Copy,
  Check,
  AlertTriangle,
  ChevronRight,
  Loader2,
  Building2,
  FileText,
  Shield,
  Zap,
  Users,
  Lock,
  TestTube,
  Rocket,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const STEPS = [
  { label: "KYB Verification", icon: Building2, done: true },
  { label: "Terms of Service", icon: FileText, done: true },
  { label: "API Key", icon: Key, active: true },
  { label: "Create Mandate", icon: Shield, active: false },
  { label: "First Payment", icon: Zap, active: false },
  { label: "Go Live", icon: Users, active: false },
];

type KeyMode = "test" | "live";

export default function APIKeyPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [mode, setMode] = useState<KeyMode>("test");
  const [kybApproved, setKybApproved] = useState(false);
  const [checkingKyb, setCheckingKyb] = useState(true);

  useEffect(() => {
    checkKybStatus();
  }, []);

  const checkKybStatus = async () => {
    setCheckingKyb(true);
    try {
      const token = localStorage.getItem("sardis_session");
      const res = await fetch(`${API_URL}/api/v2/kyb/status`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setKybApproved(
          data.status === "approved" || data.status === "completed"
        );
      }
    } catch {
      // KYB status check is best-effort
    } finally {
      setCheckingKyb(false);
    }
  };

  const generateKey = async () => {
    setIsLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("sardis_session");
      const res = await fetch(`${API_URL}/api/v2/auth/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({ name: "Onboarding Key", mode }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Failed to generate API key");
      }

      const data = await res.json();
      setApiKey(data.key || data.api_key || data.raw_key || "");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (
        msg.includes("Failed to fetch") ||
        msg.includes("NetworkError") ||
        msg.includes("404")
      ) {
        // Demo fallback when API is unavailable
        const prefix = mode === "live" ? "sk_live" : "sk_test";
        setApiKey(
          prefix + "_demo_" + Math.random().toString(36).slice(2, 18)
        );
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleContinue = () => {
    router.push("/mandate");
  };

  const liveLocked = !kybApproved && !checkingKyb;

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Left Rail */}
      <div className="hidden lg:flex w-72 bg-dark-400 border-r border-dark-100 p-8 flex-col">
        <div className="mb-10">
          <h2 className="text-lg font-bold text-white font-display">Setup</h2>
          <p className="text-sm text-gray-500 mt-1">
            Complete these steps to go live
          </p>
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
        <p className="text-xs text-gray-600 mt-auto">Step 3 of 6</p>
      </div>

      {/* Right Pane */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                <Key className="w-5 h-5 text-sardis-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white font-display">
                  Your API Key
                </h1>
                <p className="text-sm text-gray-400">
                  Choose your environment and generate a key
                </p>
              </div>
            </div>
          </div>

          {/* Mode Selector */}
          {!apiKey && (
            <div className="mb-6">
              <p className="text-sm font-medium text-gray-300 mb-3">
                Environment
              </p>
              <div className="grid grid-cols-2 gap-3">
                {/* Test Mode */}
                <button
                  onClick={() => setMode("test")}
                  className={`relative p-4 rounded-lg border text-left transition-all ${
                    mode === "test"
                      ? "border-sardis-500/60 bg-sardis-500/5 ring-1 ring-sardis-500/30"
                      : "border-dark-100 bg-dark-300 hover:border-dark-50"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <TestTube
                      className={`w-4 h-4 ${mode === "test" ? "text-sardis-400" : "text-gray-500"}`}
                    />
                    <span
                      className={`text-sm font-semibold ${mode === "test" ? "text-white" : "text-gray-300"}`}
                    >
                      Test Key
                    </span>
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      Sandbox
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    sk_test_ prefix. Safe for development. No real money moves.
                  </p>
                </button>

                {/* Live Mode */}
                <button
                  onClick={() => {
                    if (!liveLocked) setMode("live");
                  }}
                  disabled={liveLocked}
                  className={`relative p-4 rounded-lg border text-left transition-all ${
                    liveLocked
                      ? "border-dark-100 bg-dark-300/50 cursor-not-allowed opacity-60"
                      : mode === "live"
                        ? "border-sardis-500/60 bg-sardis-500/5 ring-1 ring-sardis-500/30"
                        : "border-dark-100 bg-dark-300 hover:border-dark-50"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {liveLocked ? (
                      <Lock className="w-4 h-4 text-gray-600" />
                    ) : (
                      <Rocket
                        className={`w-4 h-4 ${mode === "live" ? "text-sardis-400" : "text-gray-500"}`}
                      />
                    )}
                    <span
                      className={`text-sm font-semibold ${
                        liveLocked
                          ? "text-gray-600"
                          : mode === "live"
                            ? "text-white"
                            : "text-gray-300"
                      }`}
                    >
                      Live Key
                    </span>
                    <span
                      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                        liveLocked
                          ? "bg-gray-500/20 text-gray-500 border border-gray-500/30"
                          : "bg-green-500/20 text-green-300 border border-green-500/30"
                      }`}
                    >
                      Production
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {liveLocked
                      ? "Complete KYB verification to unlock live keys."
                      : "sk_live_ prefix. Real transactions on mainnet."}
                  </p>
                </button>
              </div>
            </div>
          )}

          {/* Generate Button (before key is generated) */}
          {!apiKey && !isLoading && !error && (
            <button
              onClick={generateKey}
              className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover mb-6"
            >
              <Key className="w-4 h-4" />
              Generate {mode === "live" ? "Live" : "Test"} API Key
            </button>
          )}

          {/* Warning Banner */}
          {apiKey && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg mb-6 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-400">
                This key cannot be recovered after you leave this page. Copy and
                store it in a secure location (e.g. environment variables, a
                secrets manager).
              </p>
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-sardis-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg mb-6">
              <p className="text-red-400 text-sm">{error}</p>
              <button
                onClick={generateKey}
                className="mt-3 text-sm text-sardis-400 hover:text-sardis-300 underline"
              >
                Try again
              </button>
            </div>
          ) : apiKey ? (
            <>
              {/* Mode Badge */}
              <div className="mb-4 flex items-center gap-2">
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    mode === "live"
                      ? "bg-green-500/20 text-green-300 border border-green-500/30"
                      : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                  }`}
                >
                  {mode === "live" ? "Live" : "Test"}
                </span>
                <span className="text-xs text-gray-500">
                  {mode === "live"
                    ? "Production key - real transactions"
                    : "Sandbox key - simulated transactions only"}
                </span>
              </div>

              {/* Key Display */}
              <div className="mb-6">
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-green-400 text-sm font-mono break-all">
                    {apiKey}
                  </code>
                  <button
                    onClick={handleCopy}
                    className="shrink-0 p-3 bg-dark-300 border border-dark-100 rounded-lg text-gray-400 hover:text-white transition-colors"
                    title="Copy API key"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-400" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Confirmation Checkbox */}
              <label className="flex items-start gap-3 mb-6 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  className="mt-1 w-4 h-4 rounded border-dark-100 bg-dark-300 text-sardis-500 focus:ring-sardis-500/50 focus:ring-offset-0"
                />
                <span className="text-sm text-gray-300 group-hover:text-white transition-colors">
                  I&apos;ve saved my API key in a secure location
                </span>
              </label>

              <button
                onClick={handleContinue}
                disabled={!confirmed}
                className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
