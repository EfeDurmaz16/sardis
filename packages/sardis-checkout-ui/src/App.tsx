import { Routes, Route, Link } from "react-router-dom";
import CheckoutPage from "./pages/CheckoutPage";
import DemoPage from "./pages/DemoPage";

/**
 * Root landing for checkout.sardis.sh. Previously this app redirected
 * root visits to sardis.sh, which broke the Coinbase CDP review flow
 * because reviewers had to know the exact /demo path to see anything.
 * Now the root shows a minimal hero with clear entry points so the
 * checkout subdomain is self-explanatory.
 */
function CheckoutHome() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[540px] bg-white rounded-2xl shadow-sm border border-[var(--checkout-border)] p-8">
        <div className="space-y-2 mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Sardis Checkout</h1>
          <p className="text-sm text-[var(--checkout-muted)]">
            Stablecoin-native checkout for AI agents and merchants.
            Non-custodial MPC wallets, on-chain policy enforcement,
            fiat onramp through Coinbase, zero protocol fees.
          </p>
        </div>

        <div className="space-y-3">
          <Link
            to="/demo"
            className="block w-full text-center px-4 py-3 rounded-lg bg-[var(--checkout-blue)] text-white font-medium hover:opacity-90 transition-opacity"
          >
            View Live Demo
          </Link>
          <a
            href="https://sardis.sh"
            className="block w-full text-center px-4 py-3 rounded-lg border border-[var(--checkout-border)] text-[var(--checkout-fg)] font-medium hover:bg-[var(--checkout-muted-bg)] transition-colors"
          >
            Learn about Sardis
          </a>
        </div>

        <div className="mt-6 pt-6 border-t border-[var(--checkout-border)] text-xs text-[var(--checkout-muted)] space-y-1">
          <p>
            <span className="font-mono">/demo</span> — live end-to-end
            checkout demo with wallet connection and onramp
          </p>
          <p>
            <span className="font-mono">/s/&lt;client_secret&gt;</span> —
            merchant-initiated checkout session
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * 404 fallback for unknown paths. Previously this pushed users to
 * sardis.sh, which masked misconfigured merchant links as a silent
 * redirect. Now it shows an explicit not-found message with a clear
 * link back to the checkout home.
 */
function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6 text-center space-y-4">
        <h2 className="text-lg font-semibold">Page not found</h2>
        <p className="text-sm text-[var(--checkout-muted)]">
          The checkout link you followed is not valid. Please use the
          link provided by the merchant, or go back to the checkout home.
        </p>
        <Link
          to="/"
          className="inline-block px-4 py-2 rounded-lg border border-[var(--checkout-border)] text-sm font-medium hover:bg-[var(--checkout-muted-bg)] transition-colors"
        >
          Checkout home
        </Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CheckoutHome />} />
      <Route path="/demo" element={<DemoPage />} />
      <Route path="/s/:clientSecret" element={<CheckoutPage />} />
      <Route path="/link/:slug" element={<LinkRedirect />} />
      {/* Legacy route: redirect old session URLs */}
      <Route path="/:sessionId" element={<LegacyRedirect />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

/**
 * Checkout link route — the backend handles creating a session
 * and redirecting to /s/{client_secret}. This component just
 * shows a loading state while the redirect happens.
 */
function LinkRedirect() {
  const API_BASE = import.meta.env.VITE_API_BASE || "/api/v2/merchant-checkout";
  const slug = window.location.pathname.split("/link/")[1];
  if (slug) {
    window.location.href = `${API_BASE}/links/${slug}`;
  }
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-8 h-8 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin" />
    </div>
  );
}

/**
 * Legacy redirect for old /:sessionId URLs.
 * Shows a message since we can't resolve session_id to client_secret client-side.
 */
function LegacyRedirect() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--checkout-bg)]">
      <div className="w-full max-w-[420px] bg-white rounded-xl shadow-sm border border-[var(--checkout-border)] p-6 text-center">
        <p className="text-sm text-[var(--checkout-muted)]">
          This checkout URL format is no longer supported. Please use the updated link provided by the merchant.
        </p>
      </div>
    </div>
  );
}
