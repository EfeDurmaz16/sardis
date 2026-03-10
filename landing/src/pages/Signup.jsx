import { useState } from 'react';
import { Link } from 'react-router-dom';

const API_URL = import.meta.env.VITE_API_URL || 'https://api.sardis.sh';

function SardisWordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 justify-center mb-8">
      <svg width="34" height="34" viewBox="0 0 28 28" fill="none">
        <path
          d="M20 5H10a7 7 0 000 14h2"
          stroke="#F5F5F5"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M8 23h10a7 7 0 000-14h-2"
          stroke="#F5F5F5"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      <span
        className="text-2xl font-bold leading-none"
        style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
      >
        Sardis
      </span>
    </Link>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4" />
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853" />
      <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05" />
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335" />
    </svg>
  );
}

function SuccessView({ apiKey, email }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full max-w-[440px] mx-auto text-center">
      <SardisWordmark />

      <div
        className="rounded-xl p-8"
        style={{
          background: '#0A0B0D',
          border: '1px solid rgba(34,197,94,0.2)',
        }}
      >
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-5"
          style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)' }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M5 13l4 4L19 7" stroke="#22C55E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        <h2
          className="text-xl font-semibold mb-2"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
        >
          You're in!
        </h2>
        <p className="text-sm mb-6" style={{ color: '#808080', fontFamily: "'Inter', sans-serif" }}>
          Account created for <span style={{ color: '#A0A0AA' }}>{email}</span>. Save your API key — it won't be shown again.
        </p>

        {/* API key display */}
        <div
          className="rounded-lg px-4 py-3 mb-2 flex items-center gap-3"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <code
            className="flex-1 text-sm text-left truncate"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: '#A0A0AA', fontSize: 13 }}
          >
            {apiKey}
          </code>
          <button
            onClick={handleCopy}
            className="shrink-0 transition-colors"
            style={{ color: copied ? '#22C55E' : '#505460' }}
            aria-label="Copy API key"
          >
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8l3.5 3.5L13 4" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="5.5" y="5.5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
                <path d="M3.5 10H3C2.448 10 2 9.552 2 9V3C2 2.448 2.448 2 3 2H9C9.552 2 10 2.448 10 3V3.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>

        <p className="text-xs mb-7" style={{ color: '#505460', fontFamily: "'Inter', sans-serif" }}>
          Store this in your environment as <code style={{ fontFamily: "'JetBrains Mono', monospace", color: '#606070' }}>SARDIS_API_KEY</code>
        </p>

        <div className="flex flex-col gap-3">
          <a
            href="https://dashboard.sardis.sh"
            className="w-full rounded-lg py-3 text-sm font-medium text-white text-center block transition-colors"
            style={{ backgroundColor: '#2563EB', fontFamily: "'Inter', sans-serif" }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#1D4ED8')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#2563EB')}
          >
            Go to Dashboard
          </a>
          <Link
            to="/docs/quickstart"
            className="w-full rounded-lg py-3 text-sm font-medium text-center block transition-colors"
            style={{
              color: '#A0A0AA',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              fontFamily: "'Inter', sans-serif",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.16)')}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)')}
          >
            Quickstart Guide
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function Signup() {
  const [form, setForm] = useState({ email: '', password: '', confirmPassword: '', displayName: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const [success, setSuccess] = useState(null); // { apiKey, email }

  const validate = () => {
    const next = {};
    if (!form.email) next.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = 'Enter a valid email address.';
    if (!form.password) next.password = 'Password is required.';
    else if (form.password.length < 8) next.password = 'Password must be at least 8 characters.';
    if (!form.confirmPassword) next.confirmPassword = 'Please confirm your password.';
    else if (form.password !== form.confirmPassword) next.confirmPassword = 'Passwords do not match.';
    return next;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: undefined }));
    if (apiError) setApiError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validation = validate();
    if (Object.keys(validation).length > 0) {
      setErrors(validation);
      return;
    }

    setLoading(true);
    setApiError('');

    try {
      const body = { email: form.email, password: form.password };
      if (form.displayName.trim()) body.display_name = form.displayName.trim();

      const res = await fetch(`${API_URL}/api/v2/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        setSuccess({ apiKey: data.api_key, email: form.email });
      } else if (res.status === 409) {
        setApiError('An account with this email already exists. Try signing in.');
      } else if (res.status === 422) {
        setApiError('Please check your details and try again.');
      } else if (res.status === 429) {
        setApiError('Too many requests. Please wait a moment and try again.');
      } else {
        setApiError(data.detail || data.message || 'Something went wrong. Please try again.');
      }
    } catch {
      setApiError('Unable to connect. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleOAuth = () => {
    window.location.href = `${API_URL}/api/v2/auth/google`;
  };

  if (success) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-5 py-16"
        style={{ backgroundColor: '#050506' }}
      >
        <SuccessView apiKey={success.apiKey} email={success.email} />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-5 py-16"
      style={{ backgroundColor: '#050506' }}
    >
      <div className="w-full max-w-[440px] mx-auto">
        <SardisWordmark />

        <div className="text-center mb-8">
          <h1
            className="text-2xl font-bold mb-2"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
          >
            Create your account
          </h1>
          <p className="text-sm" style={{ color: '#808080', fontFamily: "'Inter', sans-serif" }}>
            Free tier — no credit card required
          </p>
        </div>

        <div
          className="rounded-xl p-8"
          style={{
            background: '#0A0B0D',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          {/* Google OAuth */}
          <button
            type="button"
            onClick={handleGoogleOAuth}
            className="w-full flex items-center justify-center gap-3 rounded-lg py-3 text-sm font-medium mb-5 transition-colors"
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#E0E0E0',
              fontFamily: "'Inter', sans-serif",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
          >
            <GoogleIcon />
            Continue with Google
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
            <span className="text-xs" style={{ color: '#505460', fontFamily: "'Inter', sans-serif" }}>or</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.07)' }} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate>
            {apiError && (
              <div
                className="rounded-lg px-4 py-3 mb-5 text-sm"
                style={{
                  background: 'rgba(239,68,68,0.08)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  color: '#F87171',
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                {apiError}
              </div>
            )}

            {/* Display Name (optional) */}
            <div className="mb-4">
              <label
                htmlFor="displayName"
                className="block text-sm mb-1.5 font-medium"
                style={{ color: '#A0A0AA', fontFamily: "'Inter', sans-serif" }}
              >
                Display name <span style={{ color: '#505460', fontWeight: 400 }}>(optional)</span>
              </label>
              <input
                id="displayName"
                name="displayName"
                type="text"
                autoComplete="name"
                value={form.displayName}
                onChange={handleChange}
                placeholder="Your name or org"
                className="w-full rounded-lg px-4 py-3 text-sm outline-none transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.09)',
                  color: '#E0E0E0',
                  fontFamily: "'Inter', sans-serif",
                }}
                onFocus={(e) => (e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)')}
                onBlur={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)')}
              />
            </div>

            {/* Email */}
            <div className="mb-4">
              <label
                htmlFor="email"
                className="block text-sm mb-1.5 font-medium"
                style={{ color: '#A0A0AA', fontFamily: "'Inter', sans-serif" }}
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                className="w-full rounded-lg px-4 py-3 text-sm outline-none transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid ${errors.email ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.09)'}`,
                  color: '#E0E0E0',
                  fontFamily: "'Inter', sans-serif",
                }}
                onFocus={(e) => {
                  if (!errors.email) e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)';
                }}
                onBlur={(e) => {
                  if (!errors.email) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)';
                }}
              />
              {errors.email && (
                <p className="text-xs mt-1.5" style={{ color: '#F87171', fontFamily: "'Inter', sans-serif" }}>
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password */}
            <div className="mb-4">
              <label
                htmlFor="password"
                className="block text-sm mb-1.5 font-medium"
                style={{ color: '#A0A0AA', fontFamily: "'Inter', sans-serif" }}
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={handleChange}
                placeholder="Min. 8 characters"
                className="w-full rounded-lg px-4 py-3 text-sm outline-none transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid ${errors.password ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.09)'}`,
                  color: '#E0E0E0',
                  fontFamily: "'Inter', sans-serif",
                }}
                onFocus={(e) => {
                  if (!errors.password) e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)';
                }}
                onBlur={(e) => {
                  if (!errors.password) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)';
                }}
              />
              {errors.password && (
                <p className="text-xs mt-1.5" style={{ color: '#F87171', fontFamily: "'Inter', sans-serif" }}>
                  {errors.password}
                </p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="mb-6">
              <label
                htmlFor="confirmPassword"
                className="block text-sm mb-1.5 font-medium"
                style={{ color: '#A0A0AA', fontFamily: "'Inter', sans-serif" }}
              >
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder="Repeat your password"
                className="w-full rounded-lg px-4 py-3 text-sm outline-none transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: `1px solid ${errors.confirmPassword ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.09)'}`,
                  color: '#E0E0E0',
                  fontFamily: "'Inter', sans-serif",
                }}
                onFocus={(e) => {
                  if (!errors.confirmPassword) e.currentTarget.style.borderColor = 'rgba(59,130,246,0.5)';
                }}
                onBlur={(e) => {
                  if (!errors.confirmPassword) e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)';
                }}
              />
              {errors.confirmPassword && (
                <p className="text-xs mt-1.5" style={{ color: '#F87171', fontFamily: "'Inter', sans-serif" }}>
                  {errors.confirmPassword}
                </p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg py-3 text-sm font-medium text-white transition-colors mb-5"
              style={{
                backgroundColor: loading ? '#1e3a6e' : '#2563EB',
                fontFamily: "'Inter', sans-serif",
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
              onMouseEnter={(e) => {
                if (!loading) e.currentTarget.style.backgroundColor = '#1D4ED8';
              }}
              onMouseLeave={(e) => {
                if (!loading) e.currentTarget.style.backgroundColor = '#2563EB';
              }}
            >
              {loading ? 'Creating account...' : 'Create free account'}
            </button>

            {/* Terms */}
            <p className="text-xs text-center" style={{ color: '#505460', fontFamily: "'Inter', sans-serif" }}>
              By signing up you agree to our{' '}
              <Link to="/docs/terms" className="underline" style={{ color: '#707080' }}>
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link to="/docs/privacy" className="underline" style={{ color: '#707080' }}>
                Privacy Policy
              </Link>
              .
            </p>
          </form>
        </div>

        {/* Sign in link */}
        <p className="text-sm text-center mt-6" style={{ color: '#505460', fontFamily: "'Inter', sans-serif" }}>
          Already have an account?{' '}
          <a
            href="https://dashboard.sardis.sh"
            className="underline"
            style={{ color: '#A0A0AA' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#E0E0E0')}
            onMouseLeave={(e) => (e.currentTarget.style.color = '#A0A0AA')}
          >
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
