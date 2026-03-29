"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  ChevronRight,
  Building2,
  Key,
  Shield,
  Zap,
  Users,
} from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";

const STEPS = [
  { label: "KYB Verification", icon: Building2, done: true },
  { label: "Terms of Service", icon: FileText, active: true },
  { label: "API Key", icon: Key, active: false },
  { label: "Create Mandate", icon: Shield, active: false },
  { label: "First Payment", icon: Zap, active: false },
  { label: "Go Live", icon: Users, active: false },
];

const TOS_TEXT = `SARDIS PLATFORM TERMS OF SERVICE

Last updated: March 2026

1. ACCEPTANCE OF TERMS
By accessing or using the Sardis platform ("Platform"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree, do not use the Platform.

2. PLATFORM DESCRIPTION
Sardis provides payment infrastructure for AI agents, including non-custodial MPC wallets, spending mandates, and compliance tools.

3. ELIGIBILITY
You must be at least 18 years old and have the legal authority to enter into these Terms on behalf of your organization.

4. ACCOUNT RESPONSIBILITIES
- You are responsible for maintaining the security of your API keys and credentials.
- You are responsible for all activity that occurs under your account.
- You must notify Sardis immediately of any unauthorized use.

5. ACCEPTABLE USE
You agree not to use the Platform to:
- Facilitate money laundering, terrorist financing, or sanctions evasion.
- Process payments for illegal goods or services.
- Circumvent spending policies or compliance controls.
- Reverse-engineer or attempt to access other users' data.

6. FEES AND BILLING
- Transaction fees are charged per the pricing schedule at sardis.sh/pricing.
- Fees are non-refundable except as required by law.

7. DATA AND PRIVACY
- Sardis processes data in accordance with our Privacy Policy.
- Transaction data is stored in an append-only audit ledger.
- We do not sell your data to third parties.

8. LIMITATION OF LIABILITY
Sardis is not liable for indirect, incidental, or consequential damages arising from use of the Platform.

9. TERMINATION
Either party may terminate at any time. Upon termination, outstanding balances become immediately due.

10. GOVERNING LAW
These Terms are governed by the laws of the State of Delaware.`;

export default function TermsPage() {
  const router = useRouter();
  const [accepted, setAccepted] = useState(false);

  const handleAccept = () => {
    localStorage.setItem("sardis_terms_accepted", "true");
    router.push("/api-key");
  };

  return (
    <div className="min-h-screen bg-gray-950 flex">
      {/* Left Rail - Steps */}
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
        <p className="text-xs text-gray-600 mt-auto">Step 2 of 6</p>
      </div>

      {/* Right Pane */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg">
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-sardis-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white font-display">
                  Terms of Service
                </h1>
                <p className="text-sm text-gray-400">
                  Please review and accept to continue
                </p>
              </div>
            </div>
          </div>

          <div className="bg-dark-300 border border-dark-100 rounded-lg p-4 mb-6 max-h-80 overflow-y-auto custom-scrollbar">
            <pre className="text-xs text-gray-400 whitespace-pre-wrap font-sans leading-relaxed">
              {TOS_TEXT}
            </pre>
          </div>

          <div className="flex items-start gap-3 mb-6">
            <Checkbox
              id="accept-terms"
              checked={accepted}
              onCheckedChange={(checked) => setAccepted(checked === true)}
              className="mt-1"
            />
            <label
              htmlFor="accept-terms"
              className="text-sm text-gray-300 hover:text-white transition-colors cursor-pointer"
            >
              I have read and agree to the Sardis Terms of Service and Privacy Policy
            </label>
          </div>

          <button
            onClick={handleAccept}
            disabled={!accepted}
            className="w-full flex items-center justify-center gap-2 py-3 bg-sardis-500 text-white font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Accept &amp; Continue
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
