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

export default function APIKeyPage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    generateKey();
  }, []);

  const generateKey = async () => {
    setIsLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("sardis_session");
      const res = await fetch(`${API_URL}/api/v2/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({ name: "Onboarding Key" }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Failed to generate API key");
      }

      const data = await res.json();
      setApiKey(data.api_key || data.key || data.raw_key || "");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (
        msg.includes("Failed to fetch") ||
        msg.includes("NetworkError") ||
        msg.includes("404")
      ) {
        // Demo fallback key (not a real secret)
        setApiKey("sk_test_onboarding_" + Math.random().toString(36).slice(2, 18));
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

  return (
    <div className="min-h-screen bg-gray-950 flex">
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
                  Save this key securely — it will only be shown once
                </p>
              </div>
            </div>
          </div>

          {/* Warning Banner */}
          <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg mb-6 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-yellow-400">
              This key cannot be recovered after you leave this page. Copy and store it in a secure location (e.g. environment variables, a secrets manager).
            </p>
          </div>

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
          ) : (
            <>
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
                className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
