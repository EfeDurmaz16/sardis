import { Routes, Route } from "react-router-dom";
import CheckoutPage from "./pages/CheckoutPage";
import DemoPage from "./pages/DemoPage";

function RedirectToMain() {
  window.location.href = "https://sardis.sh";
  return null;
}

export default function App() {
  return (
    <Routes>
      <Route path="/demo" element={<DemoPage />} />
      <Route path="/s/:clientSecret" element={<CheckoutPage />} />
      <Route path="/link/:slug" element={<LinkRedirect />} />
      {/* Legacy route: redirect old session URLs */}
      <Route path="/:sessionId" element={<LegacyRedirect />} />
      <Route path="*" element={<RedirectToMain />} />
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
