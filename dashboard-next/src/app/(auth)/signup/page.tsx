"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Shield, Copy, Check } from "lucide-react";
import { signIn, signUp } from "@/lib/auth-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [agentId, setAgentId] = useState("");
  const [copied, setCopied] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setIsLoading(true);

    try {
      // Try better-auth signup
      const { error: authError } = await signUp.email({
        email: email.trim().toLowerCase(),
        password,
        name: displayName.trim() || email.trim().toLowerCase(),
      });

      if (authError) {
        // Fallback: try legacy API registration
        const response = await fetch(`${API_URL}/api/v2/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
            password,
            display_name: displayName.trim() || undefined,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          // Sign in via better-auth after legacy registration
          await signIn.email({ email: email.trim().toLowerCase(), password });
          if (data.agent_id) {
            setAgentId(data.agent_id);
          }
          if (data.api_key) {
            setApiKey(data.api_key);
          } else {
            router.push(
              `/onboarding?agentId=${encodeURIComponent(data.agent_id || "")}`
            );
          }
          return;
        }

        if (response.status === 409) {
          setError("An account with this email already exists. Try logging in.");
          return;
        }

        if (response.status === 429) {
          setError("Too many signup attempts. Please try again later.");
          return;
        }

        const errData = await response.json().catch(() => null);
        setError(errData?.detail || "Registration failed. Please try again.");
        return;
      }

      // better-auth signup succeeded -- now try legacy register for API key + agent provisioning
      const response = await fetch(`${API_URL}/api/v2/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password,
          display_name: displayName.trim() || undefined,
        }),
      }).catch(() => null);

      if (response && response.ok) {
        const data = await response.json();
        // Store session token so middleware allows dashboard access
        if (data.access_token) {
          sessionStorage.setItem("sardis_session", data.access_token);
          document.cookie = `better-auth.session_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;
        }
        if (data.agent_id) {
          setAgentId(data.agent_id);
        }
        if (data.api_key) {
          setApiKey(data.api_key);
          return;
        }
      }

      // No API key returned -- go straight to onboarding
      router.push("/onboarding");
    } catch {
      setError("Network error. Please check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleContinue = () => {
    router.push(
      `/onboarding?apiKey=${encodeURIComponent(apiKey)}&agentId=${encodeURIComponent(agentId || "")}`
    );
  };

  // Show API key screen after successful registration
  if (apiKey) {
    return (
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-green-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Check className="w-8 h-8 text-green-400" />
          </div>
          <h1 className="text-3xl font-bold text-white font-display">Welcome to Sardis</h1>
          <p className="text-gray-400 mt-2">Your account has been created</p>
        </div>

        <div className="card p-8 space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-yellow-400">
                Your API Key
              </label>
              <span className="text-xs text-yellow-400/70">Save this — you won&apos;t see it again</span>
            </div>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-green-400 text-sm font-mono break-all">
                {apiKey}
              </code>
              <button
                onClick={handleCopyKey}
                className="shrink-0 p-3 bg-dark-300 border border-dark-100 rounded-lg text-gray-400 hover:text-white transition-colors"
                title="Copy API key"
              >
                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-xs">
            This key provides access to the Sardis API. Store it securely — it cannot be recovered after you leave this page.
          </div>

          <button
            onClick={handleContinue}
            className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
          >
            Continue to Setup &rarr;
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-sardis-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Shield className="w-8 h-8 text-sardis-400" />
        </div>
        <h1 className="text-3xl font-bold text-white font-display">Create Account</h1>
        <p className="text-gray-400 mt-2">Start building with Sardis in minutes</p>
      </div>

      <div className="card p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 transition-colors"
              placeholder="you@company.com"
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Display Name <span className="text-gray-600">(optional)</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 transition-colors"
              placeholder="Your name"
              autoComplete="name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 transition-colors"
              placeholder="At least 8 characters"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 transition-colors"
              placeholder="Repeat password"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">
            Already have an account?{" "}
            <Link href="/login" className="text-sardis-400 hover:text-sardis-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      <p className="text-center text-xs text-gray-600 mt-4">
        By creating an account you agree to our{" "}
        <a href="https://sardis.sh/docs/terms" className="underline text-gray-500" target="_blank" rel="noopener noreferrer">Terms</a>
        {" "}and{" "}
        <a href="https://sardis.sh/docs/privacy" className="underline text-gray-500" target="_blank" rel="noopener noreferrer">Privacy Policy</a>.
      </p>
    </div>
  );
}
