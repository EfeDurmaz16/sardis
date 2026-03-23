"use client";

import { useEffect, useState } from "react";
import { getAuthHeaders } from "../api/client";

type KYCStatus = "not_started" | "pending" | "approved" | "rejected" | "expired";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function KYCBanner() {
  const [status, setStatus] = useState<KYCStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Poll KYC status every 30 seconds
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    async function fetchStatus() {
      try {
        const res = await fetch(`${API_URL}/api/v2/kyc/status`, {
          headers: getAuthHeaders(),
        });
        if (!res.ok) return;
        const data = await res.json();
        setStatus(data.status as KYCStatus);

        // Stop polling once approved
        if (data.status === "approved" && interval) {
          clearInterval(interval);
        }
      } catch {
        // Silent fail — banner is non-critical
      }
    }

    fetchStatus();
    interval = setInterval(fetchStatus, 30_000);

    return () => clearInterval(interval);
  }, []);

  // Don't render if approved, loading, or dismissed
  if (status === "approved" || status === null || dismissed) return null;

  async function initiate() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v2/kyc/initiate`, {
        method: "POST",
        headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error("Failed to initiate KYC");
      const data = await res.json();
      if (data.verification_url) {
        window.open(data.verification_url, "_blank", "noopener");
      }
      setStatus("pending");
    } catch {
      // Stay on current state
    } finally {
      setLoading(false);
    }
  }

  const config: Record<string, { bg: string; border: string; text: string; action: string }> = {
    not_started: {
      bg: "bg-amber-950/30",
      border: "border-amber-800/40",
      text: "Complete identity verification to unlock full transaction limits.",
      action: "Verify Now",
    },
    pending: {
      bg: "bg-blue-950/30",
      border: "border-blue-800/40",
      text: "Identity verification in progress. This usually takes a few minutes.",
      action: "",
    },
    rejected: {
      bg: "bg-red-950/30",
      border: "border-red-800/40",
      text: "Identity verification was unsuccessful. Please try again or contact support.",
      action: "Retry Verification",
    },
    expired: {
      bg: "bg-neutral-800/50",
      border: "border-neutral-700/50",
      text: "Your identity verification has expired. Please re-verify to maintain access.",
      action: "Re-verify",
    },
  };

  const c = config[status] || config.not_started;

  return (
    <div className={`${c.bg} ${c.border} border rounded-lg px-4 py-3 flex items-center justify-between gap-4 mb-4`}>
      <div className="flex items-center gap-3 min-w-0">
        <div className="shrink-0">
          {status === "pending" ? (
            <svg className="w-5 h-5 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>
        <p className="text-sm text-neutral-300 truncate">{c.text}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {c.action && (
          <button
            onClick={initiate}
            disabled={loading}
            className="text-sm font-medium px-3 py-1.5 rounded-md bg-white/10 hover:bg-white/15 text-white transition-colors disabled:opacity-50"
          >
            {loading ? "..." : c.action}
          </button>
        )}
        <button
          onClick={() => setDismissed(true)}
          className="text-neutral-500 hover:text-neutral-300 transition-colors"
          aria-label="Dismiss"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
