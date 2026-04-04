"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Fingerprint } from "lucide-react";
import { signIn, authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "").trim();

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  // Conditional UI: trigger passkey autofill on mount if browser supports it
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!window.PublicKeyCredential?.isConditionalMediationAvailable) return;
    window.PublicKeyCredential.isConditionalMediationAvailable().then((available) => {
      if (available) {
        authClient.signIn.passkey({ autoFill: true });
      }
    });
  }, []);

  const handlePasskeySignIn = async () => {
    setError("");
    setIsLoading(true);
    try {
      await authClient.signIn.passkey({
        fetchOptions: {
          onSuccess: () => {
            window.location.href = "/";
          },
          onError: (ctx: { error: { message?: string } }) => {
            setError(ctx.error.message || "Passkey sign-in failed");
          },
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Passkey sign-in failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Login via FastAPI JWT endpoint
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch(`${API_URL}/api/v2/auth/login`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Invalid credentials");
      }

      const data = await response.json();

      if (data.access_token) {
        // Store JWT for API client + middleware
        localStorage.setItem("sardis_session", data.access_token);
        // Set cookies for middleware auth checks
        document.cookie = `better-auth.session_token=${data.access_token}; path=/; max-age=604800; SameSite=Lax`;
        document.cookie = `sardis_session=${data.access_token}; path=/; max-age=604800; SameSite=Lax`;
        // Hard navigation to ensure cookies are sent with the first request
        window.location.href = "/";
        return;
      }

      throw new Error("No access token received");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid email or password");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm mx-auto px-4">
      <div className="text-center mb-10">
        <div className="w-14 h-14 flex items-center justify-center mx-auto mb-5">
          <svg width="40" height="40" viewBox="0 0 28 28" fill="none">
            <path
              d="M20 5H10a7 7 0 000 14h2"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
            <path
              d="M8 23h10a7 7 0 000-14h-2"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">Sign in to Sardis</h1>
        <p className="text-sm text-gray-500 mt-2">
          Enter your credentials to access the dashboard
        </p>
      </div>

      <Card className="shadow-md bg-white border border-gray-300 w-full">
        <CardHeader className="pb-4 pt-6 px-8">
          <CardTitle className="text-base text-gray-900">Account</CardTitle>
        </CardHeader>
        <CardContent className="px-8 pb-8">
          <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
            {error && (
              <div className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label
                htmlFor="email"
                className="text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <Input
                id="email"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@company.com"
                autoComplete="username webauthn"
                required
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium text-gray-700"
              >
                Password
              </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="********"
                  className="pr-10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-900 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full bg-gray-900 text-white hover:bg-gray-800"
              disabled={isLoading}
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </Button>
          </form>

          {/* Separator */}
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-400">or</span>
            </div>
          </div>

          {/* Passkey sign-in */}
          <Button
            type="button"
            variant="outline"
            className="w-full"
            disabled={isLoading}
            onClick={handlePasskeySignIn}
          >
            <Fingerprint className="mr-2 h-4 w-4" />
            Sign in with Passkey
          </Button>
        </CardContent>
        <CardFooter className="flex flex-col gap-2 text-center text-sm border-t border-gray-200 bg-gray-50/50 pt-4">
          <Link
            href="/forgot-password"
            className="text-gray-500 hover:text-gray-900 transition-colors"
          >
            Forgot password?
          </Link>
          <p className="text-gray-500">
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="text-gray-900 font-medium hover:underline"
            >
              Create one
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
