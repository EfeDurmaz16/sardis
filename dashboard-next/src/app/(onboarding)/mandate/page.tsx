"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  ChevronRight,
  Loader2,
  Building2,
  FileText,
  Key,
  Zap,
  Users,
  Star,
} from "lucide-react";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").trim();

const STEPS = [
  { label: "KYB Verification", icon: Building2, done: true },
  { label: "Terms of Service", icon: FileText, done: true },
  { label: "API Key", icon: Key, done: true },
  { label: "Create Mandate", icon: Shield, active: true },
  { label: "First Payment", icon: Zap, active: false },
  { label: "Go Live", icon: Users, active: false },
];

type TemplateId = "dev-tools" | "api-payments" | "custom";

const TEMPLATES: {
  id: TemplateId;
  name: string;
  description: string;
  recommended?: boolean;
  amount: string;
  period: string;
  vendors: string;
}[] = [
  {
    id: "dev-tools",
    name: "Dev Tools",
    description: "Allow your agent to purchase dev tools and API credits",
    recommended: true,
    amount: "200",
    period: "day",
    vendors: "OpenAI, Anthropic, AWS, GCP, Vercel",
  },
  {
    id: "api-payments",
    name: "API Payments",
    description: "Unlimited API payment processing for your agent",
    amount: "10000",
    period: "month",
    vendors: "",
  },
  {
    id: "custom",
    name: "Custom",
    description: "Define your own spending limits and rules",
    amount: "",
    period: "day",
    vendors: "",
  },
];

export default function MandatePage() {
  const router = useRouter();
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateId>("dev-tools");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Custom form fields
  const [customAmount, setCustomAmount] = useState("");
  const [customPeriod, setCustomPeriod] = useState("day");
  const [customVendors, setCustomVendors] = useState("");

  const template = TEMPLATES.find((t) => t.id === selectedTemplate)!;
  const isCustom = selectedTemplate === "custom";
  const amount = isCustom ? customAmount : template.amount;
  const period = isCustom ? customPeriod : template.period;
  const vendors = isCustom ? customVendors : template.vendors;

  const handleSubmit = async () => {
    if (!amount) return;

    setIsLoading(true);
    setError("");

    try {
      const token = localStorage.getItem("sardis_session");
      const res = await fetch(`${API_URL}/api/v2/mandates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          max_amount: parseFloat(amount),
          period,
          allowed_vendors: vendors
            ? vendors.split(",").map((v) => v.trim())
            : [],
          template: selectedTemplate,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || "Failed to create mandate");
      }

      const data = await res.json();
      // Store mandate ID for the first payment step
      if (data.mandate_id) {
        sessionStorage.setItem("sardis_onboarding_mandate_id", data.mandate_id);
      }
      router.push("/first-payment");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (
        msg.includes("Failed to fetch") ||
        msg.includes("NetworkError") ||
        msg.includes("404")
      ) {
        sessionStorage.setItem("sardis_onboarding_mandate_id", "mandate_demo");
        router.push("/first-payment");
      } else {
        setError(msg);
      }
    } finally {
      setIsLoading(false);
    }
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
        <p className="text-xs text-gray-600 mt-auto">Step 4 of 6</p>
      </div>

      {/* Right Pane */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-sardis-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white font-display">
                  Create a Spending Mandate
                </h1>
                <p className="text-sm text-gray-400">
                  Define how much your agent can spend and where
                </p>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Template Picker */}
          <div className="space-y-3 mb-6">
            {TEMPLATES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedTemplate(t.id)}
                className={`w-full text-left p-4 rounded-lg border transition-all ${
                  selectedTemplate === t.id
                    ? "border-sardis-500/50 bg-sardis-500/5"
                    : "border-dark-100 bg-dark-300 hover:border-gray-600"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{t.name}</span>
                    {t.recommended && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-sardis-500/10 text-sardis-400 text-xs rounded-full">
                        <Star className="w-3 h-3" />
                        Recommended
                      </span>
                    )}
                  </div>
                  {t.id !== "custom" && (
                    <span className="text-sm text-gray-400 font-mono">
                      ${t.amount}/{t.period}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500">{t.description}</p>
              </button>
            ))}
          </div>

          {/* Custom Form */}
          {isCustom && (
            <div className="space-y-4 mb-6 p-4 bg-dark-300 border border-dark-100 rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Max Amount <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                    <input
                      type="number"
                      required
                      value={customAmount}
                      onChange={(e) => setCustomAmount(e.target.value)}
                      className="w-full pl-7 pr-3 py-3 bg-dark-400 border border-dark-100 rounded-lg text-white font-mono focus:outline-none focus:border-sardis-500/50"
                      placeholder="500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    Period
                  </label>
                  <select
                    value={customPeriod}
                    onChange={(e) => setCustomPeriod(e.target.value)}
                    className="w-full px-4 py-3 bg-dark-400 border border-dark-100 rounded-lg text-white appearance-none focus:outline-none focus:border-sardis-500/50"
                  >
                    <option value="transaction">Per Transaction</option>
                    <option value="day">Per Day</option>
                    <option value="week">Per Week</option>
                    <option value="month">Per Month</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1.5">
                  Allowed Vendors <span className="text-gray-600">(comma-separated, optional)</span>
                </label>
                <input
                  type="text"
                  value={customVendors}
                  onChange={(e) => setCustomVendors(e.target.value)}
                  className="w-full px-4 py-3 bg-dark-400 border border-dark-100 rounded-lg text-white placeholder-gray-600 focus:outline-none focus:border-sardis-500/50"
                  placeholder="OpenAI, AWS, Stripe"
                />
              </div>
            </div>
          )}

          {/* Summary */}
          {amount && (
            <div className="p-4 bg-dark-200 border border-dark-100 rounded-lg mb-6">
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Mandate Summary</p>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-400">Spending limit</span>
                <span className="text-white font-mono">${amount}/{period}</span>
              </div>
              {vendors && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Allowed vendors</span>
                  <span className="text-gray-300 text-xs">{vendors}</span>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={isLoading || !amount}
            className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating Mandate...
              </>
            ) : (
              <>
                Create Mandate
                <ChevronRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
