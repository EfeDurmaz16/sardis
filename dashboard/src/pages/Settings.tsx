/**
 * Settings Page — tabbed layout
 *
 * Tabs:
 *  - Profile    : display name, email, password change, MFA (TOTP) setup
 *  - Organization: org name, org ID (copyable), team members, role
 *  - API Keys   : link card → /api-keys, active key count
 *  - Billing    : link card → /billing, current plan badge
 *  - Notifications: Slack webhook, email toggle, alert severities, test channel
 */

import { useState, useEffect, useCallback } from 'react'
import {
  User,
  Building2,
  Key,
  CreditCard,
  Bell,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  ShieldCheck,
  ShieldAlert,
  CheckCircle,
  Clock,
  ExternalLink,
  Send,
  ChevronRight,
  Eye,
  EyeOff,
} from 'lucide-react'
import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const API_BASE = import.meta.env.VITE_API_URL || ''

// ── Types ───────────────────────────────────────────────────────────────────

interface UserProfile {
  id: string
  email: string
  display_name: string | null
  role: string
  org_id: string | null
  org_name: string | null
  mfa_enabled: boolean
}

interface TeamMember {
  id: string
  email: string
  display_name: string | null
  role: string
}

interface AlertChannel {
  id: string
  type: 'slack' | 'email'
  destination: string
  enabled: boolean
  severities: string[]
}

type TabId = 'profile' | 'organization' | 'api-keys' | 'billing' | 'notifications'

// ── Helpers ─────────────────────────────────────────────────────────────────

function authHeaders(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ── Copy Button ─────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-dark-200 text-gray-400 hover:text-white border border-dark-100 transition-colors"
      title="Copy to clipboard"
      aria-label="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-sardis-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

// ── Input component ─────────────────────────────────────────────────────────

function FieldInput({
  label,
  value,
  onChange,
  readOnly = false,
  type = 'text',
  placeholder = '',
  hint,
  suffix,
}: {
  label: string
  value: string
  onChange?: (v: string) => void
  readOnly?: boolean
  type?: string
  placeholder?: string
  hint?: string
  suffix?: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1.5">{label}</label>
      <div className="flex gap-2 items-stretch">
        <input
          type={type}
          value={value}
          onChange={onChange ? (e) => onChange(e.target.value) : undefined}
          readOnly={readOnly}
          placeholder={placeholder}
          className={clsx(
            'flex-1 px-4 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white rounded',
            readOnly ? 'text-gray-400 cursor-default' : 'focus:border-sardis-500/60'
          )}
        />
        {suffix}
      </div>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  )
}

// ── Toggle ───────────────────────────────────────────────────────────────────

function Toggle({ enabled, onChange, label }: { enabled: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      role="switch"
      aria-checked={enabled}
      aria-label={label}
      className={clsx(
        'w-12 h-6 rounded-full transition-colors relative',
        enabled ? 'bg-sardis-500' : 'bg-dark-100'
      )}
    >
      <div
        className={clsx(
          'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
          enabled ? 'translate-x-7' : 'translate-x-1'
        )}
      />
    </button>
  )
}

// ── KYC STATUS TYPES ─────────────────────────────────────────────────────────

type KYCStatus = 'not_started' | 'pending' | 'approved' | 'rejected' | 'expired'

interface KYCStatusData {
  status: KYCStatus
  provider?: string
  verified_at?: string
  expires_at?: string
}

// ── VERIFICATION SECTION (used inside ProfileTab) ─────────────────────────────

function VerificationSection({ token }: { token: string | null }) {
  const [kycData, setKycData] = useState<KYCStatusData | null>(null)
  const [loading, setLoading] = useState(true)
  const [hidden, setHidden] = useState(false)
  const [initiating, setInitiating] = useState(false)
  const [initiateMsg, setInitiateMsg] = useState<string | null>(null)

  const hdrs = authHeaders(token)

  useEffect(() => {
    async function fetchKyc() {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/api/v2/kyc/status`, { headers: hdrs })
        if (res.status === 503) { setHidden(true); return }
        if (!res.ok) { setHidden(true); return }
        const data: KYCStatusData = await res.json()
        setKycData(data)
      } catch {
        setHidden(true)
      } finally {
        setLoading(false)
      }
    }
    fetchKyc()
  }, [token])

  async function handleInitiate() {
    setInitiating(true)
    setInitiateMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/v2/kyc/initiate`, {
        method: 'POST',
        headers: hdrs,
      })
      if (res.ok) {
        const data = await res.json()
        if (data.redirect_url) {
          window.open(data.redirect_url, '_blank', 'noopener,noreferrer')
          setInitiateMsg('Verification page opened in a new tab.')
        }
      } else {
        setInitiateMsg('Failed to start verification. Please try again.')
      }
    } catch {
      setInitiateMsg('Network error. Please try again.')
    } finally {
      setInitiating(false)
      setTimeout(() => setInitiateMsg(null), 5000)
    }
  }

  function formatDate(iso: string) {
    try {
      return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    } catch {
      return iso
    }
  }

  if (hidden || (loading && !kycData)) {
    if (loading) {
      return (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-base font-semibold text-white">Identity Verification</h3>
          </div>
          <div className="flex items-center gap-2 mt-4 text-sm text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading verification status...
          </div>
        </div>
      )
    }
    return null
  }

  const status = kycData?.status ?? 'not_started'

  const STATUS_CONFIG: Record<KYCStatus, {
    badge: string
    label: string
    icon: React.ReactNode
    iconBg: string
    headerIcon: React.ReactNode
  }> = {
    not_started: {
      badge: 'bg-gray-500/20 text-gray-300 border border-gray-500/30',
      label: 'Not Started',
      icon: <ShieldCheck className="w-4 h-4 text-gray-400" />,
      iconBg: 'bg-gray-500/10',
      headerIcon: <ShieldCheck className="w-5 h-5 text-gray-400" />,
    },
    pending: {
      badge: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
      label: 'Pending',
      icon: <Clock className="w-4 h-4 text-blue-400 animate-pulse" />,
      iconBg: 'bg-blue-500/10',
      headerIcon: <Clock className="w-5 h-5 text-blue-400" />,
    },
    approved: {
      badge: 'bg-green-500/20 text-green-300 border border-green-500/30',
      label: 'Verified',
      icon: <CheckCircle className="w-4 h-4 text-green-400" />,
      iconBg: 'bg-green-500/10',
      headerIcon: <CheckCircle className="w-5 h-5 text-green-400" />,
    },
    rejected: {
      badge: 'bg-red-500/20 text-red-300 border border-red-500/30',
      label: 'Failed',
      icon: <ShieldAlert className="w-4 h-4 text-red-400" />,
      iconBg: 'bg-red-500/10',
      headerIcon: <ShieldAlert className="w-5 h-5 text-red-400" />,
    },
    expired: {
      badge: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
      label: 'Expired',
      icon: <AlertCircle className="w-4 h-4 text-amber-400" />,
      iconBg: 'bg-amber-500/10',
      headerIcon: <AlertCircle className="w-5 h-5 text-amber-400" />,
    },
  }

  const cfg = STATUS_CONFIG[status]
  const showCta = status === 'not_started' || status === 'rejected' || status === 'expired'
  const ctaLabel = status === 'not_started' ? 'Verify Now' : status === 'rejected' ? 'Retry' : 'Re-verify'

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center', cfg.iconBg)}>
            {cfg.headerIcon}
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Identity Verification</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Required for live payment processing.
            </p>
          </div>
        </div>
        <span className={clsx('text-xs font-medium px-2.5 py-1 rounded-full', cfg.badge)}>
          {cfg.label}
        </span>
      </div>

      {/* Details for approved */}
      {status === 'approved' && kycData && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-dark-200/50 border border-dark-100 rounded p-4">
          {kycData.provider && (
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Provider</p>
              <p className="text-sm font-medium text-white capitalize">{kycData.provider}</p>
            </div>
          )}
          {kycData.verified_at && (
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Verified On</p>
              <p className="text-sm font-medium text-white">{formatDate(kycData.verified_at)}</p>
            </div>
          )}
          {kycData.expires_at && (
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 mb-1">Expires</p>
              <p className="text-sm font-medium text-white">{formatDate(kycData.expires_at)}</p>
            </div>
          )}
        </div>
      )}

      {/* Pending message */}
      {status === 'pending' && (
        <div className="flex items-center gap-2 p-3 bg-blue-500/10 border border-blue-500/20 rounded text-sm text-blue-300">
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          Verification is in progress. This usually takes a few minutes.
        </div>
      )}

      {/* Rejected message */}
      {status === 'rejected' && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-300">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          Verification failed. Please try again with valid documents.
        </div>
      )}

      {/* Expired message */}
      {status === 'expired' && (
        <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded text-sm text-amber-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          Your verification has expired. Please re-verify to continue using live payments.
        </div>
      )}

      {/* Initiate result message */}
      {initiateMsg && (
        <p className={clsx('text-sm', initiateMsg.includes('Failed') || initiateMsg.includes('Network') ? 'text-red-400' : 'text-sardis-400')}>
          {initiateMsg}
        </p>
      )}

      {/* CTA button */}
      {showCta && (
        <div className="flex justify-end">
          <button
            onClick={handleInitiate}
            disabled={initiating}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {initiating && <Loader2 className="w-4 h-4 animate-spin" />}
            {ctaLabel}
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}

// ── PROFILE TAB ──────────────────────────────────────────────────────────────

function ProfileTab({ token }: { token: string | null }) {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [displayName, setDisplayName] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  // Password change
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [pwdError, setPwdError] = useState<string | null>(null)
  const [pwdMsg, setPwdMsg] = useState<string | null>(null)
  const [pwdSaving, setPwdSaving] = useState(false)

  // MFA
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [mfaSetup, setMfaSetup] = useState<{ qr_uri: string; secret: string } | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [mfaLoading, setMfaLoading] = useState(false)
  const [mfaError, setMfaError] = useState<string | null>(null)
  const [mfaSuccess, setMfaSuccess] = useState(false)

  const hdrs = authHeaders(token)

  useEffect(() => {
    fetchProfile()
  }, [token])

  async function fetchProfile() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/me`, { headers: hdrs })
      if (res.ok) {
        const data: UserProfile = await res.json()
        setProfile(data)
        setDisplayName(data.display_name ?? '')
        setMfaEnabled(data.mfa_enabled)
      }
    } catch {
      // network unavailable — show empty form
    } finally {
      setLoading(false)
    }
  }

  async function saveProfile() {
    setSaving(true)
    setSaveMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/me`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...hdrs },
        body: JSON.stringify({ display_name: displayName }),
      })
      setSaveMsg(res.ok ? 'Profile saved.' : 'Failed to save. Try again.')
      setTimeout(() => setSaveMsg(null), 3000)
    } catch {
      setSaveMsg('Network error.')
    } finally {
      setSaving(false)
    }
  }

  async function changePassword() {
    setPwdError(null)
    setPwdMsg(null)
    if (!currentPwd || !newPwd || !confirmPwd) {
      setPwdError('All fields are required.')
      return
    }
    if (newPwd !== confirmPwd) {
      setPwdError('New passwords do not match.')
      return
    }
    if (newPwd.length < 8) {
      setPwdError('Password must be at least 8 characters.')
      return
    }
    setPwdSaving(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...hdrs },
        body: JSON.stringify({ current_password: currentPwd, new_password: newPwd }),
      })
      if (res.ok) {
        setPwdMsg('Password updated.')
        setCurrentPwd('')
        setNewPwd('')
        setConfirmPwd('')
      } else {
        const d = await res.json().catch(() => ({}))
        setPwdError((d as { detail?: string }).detail ?? `Error (${res.status})`)
      }
    } catch {
      setPwdError('Network error.')
    } finally {
      setPwdSaving(false)
    }
  }

  async function startMfaSetup() {
    setMfaLoading(true)
    setMfaError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/mfa/setup`, {
        method: 'POST',
        headers: hdrs,
      })
      if (res.ok) {
        const data = await res.json()
        setMfaSetup(data)
      } else {
        setMfaError('Failed to start MFA setup.')
      }
    } catch {
      setMfaError('Network error.')
    } finally {
      setMfaLoading(false)
    }
  }

  async function verifyMfa() {
    if (!totpCode || totpCode.length !== 6) {
      setMfaError('Enter the 6-digit code from your authenticator.')
      return
    }
    setMfaLoading(true)
    setMfaError(null)
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/mfa/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...hdrs },
        body: JSON.stringify({ code: totpCode }),
      })
      if (res.ok) {
        setMfaEnabled(true)
        setMfaSetup(null)
        setTotpCode('')
        setMfaSuccess(true)
      } else {
        setMfaError('Invalid code. Try again.')
      }
    } catch {
      setMfaError('Network error.')
    } finally {
      setMfaLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-sardis-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Basic info */}
      <div className="card p-6 space-y-5">
        <h3 className="text-base font-semibold text-white">Basic Information</h3>

        <FieldInput
          label="Display Name"
          value={displayName}
          onChange={setDisplayName}
          placeholder="Your name"
        />

        <FieldInput
          label="Email"
          value={profile?.email ?? ''}
          readOnly
          hint="Email cannot be changed here. Contact support."
        />

        <div className="flex items-center justify-between pt-1">
          <div>
            {saveMsg && (
              <p className={clsx('text-sm', saveMsg.startsWith('Profile') ? 'text-sardis-400' : 'text-red-400')}>
                {saveMsg}
              </p>
            )}
          </div>
          <button
            onClick={saveProfile}
            disabled={saving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Profile
          </button>
        </div>
      </div>

      {/* Change password */}
      <div className="card p-6 space-y-4">
        <h3 className="text-base font-semibold text-white">Change Password</h3>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1.5">Current Password</label>
          <div className="relative">
            <input
              type={showPwd ? 'text' : 'password'}
              value={currentPwd}
              onChange={(e) => setCurrentPwd(e.target.value)}
              placeholder="Current password"
              className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white rounded focus:border-sardis-500/60 pr-10"
            />
            <button
              type="button"
              onClick={() => setShowPwd((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              aria-label={showPwd ? "Hide password" : "Show password"}
            >
              {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <FieldInput
          label="New Password"
          value={newPwd}
          onChange={setNewPwd}
          type={showPwd ? 'text' : 'password'}
          placeholder="At least 8 characters"
        />

        <FieldInput
          label="Confirm New Password"
          value={confirmPwd}
          onChange={setConfirmPwd}
          type={showPwd ? 'text' : 'password'}
          placeholder="Repeat new password"
        />

        {pwdError && (
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {pwdError}
          </div>
        )}
        {pwdMsg && <p className="text-sm text-sardis-400">{pwdMsg}</p>}

        <div className="flex justify-end">
          <button
            onClick={changePassword}
            disabled={pwdSaving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-dark-200 border border-dark-100 text-gray-300 hover:text-white hover:bg-dark-100 transition-colors disabled:opacity-50"
          >
            {pwdSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            Update Password
          </button>
        </div>
      </div>

      {/* MFA */}
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-sardis-500/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-sardis-400" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Two-Factor Authentication</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                {mfaEnabled ? 'MFA is enabled on your account.' : 'Add an extra layer of security.'}
              </p>
            </div>
          </div>
          {mfaEnabled ? (
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-green-500/20 text-green-300 border border-green-500/30">
              Enabled
            </span>
          ) : (
            !mfaSetup && (
              <button
                onClick={startMfaSetup}
                disabled={mfaLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50"
              >
                {mfaLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                Enable MFA
              </button>
            )
          )}
        </div>

        {mfaSuccess && (
          <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded text-sm text-green-300">
            <Check className="w-4 h-4" />
            MFA has been successfully enabled.
          </div>
        )}

        {mfaSetup && (
          <div className="space-y-4 border-t border-dark-100 pt-4">
            <p className="text-sm text-gray-400">
              Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code below.
            </p>

            <div className="flex flex-col sm:flex-row gap-6 items-start">
              {/* QR code displayed as a URI link fallback — real impl would use a QR library */}
              <div className="bg-white p-3 rounded-lg shrink-0">
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(mfaSetup.qr_uri)}`}
                  alt="TOTP QR Code"
                  className="w-40 h-40"
                />
              </div>

              <div className="flex-1 space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1 uppercase tracking-wider">Manual entry key</p>
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-sm text-sardis-400 bg-dark-200 border border-dark-100 px-3 py-1.5 rounded flex-1 break-all">
                      {mfaSetup.secret}
                    </code>
                    <CopyButton text={mfaSetup.secret} />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Verification Code</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="123456"
                    className="w-full px-4 py-2.5 bg-dark-200 border border-dark-100 text-sm text-white rounded focus:border-sardis-500/60 font-mono tracking-widest"
                  />
                </div>

                {mfaError && (
                  <div className="flex items-center gap-2 text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {mfaError}
                  </div>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={() => { setMfaSetup(null); setTotpCode(''); setMfaError(null) }}
                    className="px-4 py-2 text-sm bg-dark-200 border border-dark-100 text-gray-400 hover:text-white transition-colors rounded"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={verifyMfa}
                    disabled={mfaLoading || totpCode.length !== 6}
                    className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded"
                  >
                    {mfaLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                    Verify & Enable
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Identity Verification */}
      <VerificationSection token={token} />
    </div>
  )
}

// ── ORGANIZATION TAB ─────────────────────────────────────────────────────────

const ROLE_BADGE: Record<string, string> = {
  owner: 'bg-sardis-500/20 text-sardis-300 border border-sardis-500/30',
  admin: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
  member: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
}

function OrganizationTab({ token }: { token: string | null }) {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [members, setMembers] = useState<TeamMember[]>([])
  const [orgName, setOrgName] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<string | null>(null)

  const hdrs = authHeaders(token)

  useEffect(() => {
    fetchData()
  }, [token])

  async function fetchData() {
    setLoading(true)
    try {
      const [meRes, membersRes] = await Promise.all([
        fetch(`${API_BASE}/api/v2/auth/me`, { headers: hdrs }).catch(() => null),
        fetch(`${API_BASE}/api/v2/org/members`, { headers: hdrs }).catch(() => null),
      ])

      if (meRes && meRes.ok) {
        const data: UserProfile = await meRes.json()
        setProfile(data)
        setOrgName(data.org_name ?? '')
      }

      if (membersRes && membersRes.ok) {
        const data = await membersRes.json()
        setMembers(Array.isArray(data) ? data : (data.members ?? []))
      }
    } catch {
      // network unavailable
    } finally {
      setLoading(false)
    }
  }

  async function saveOrg() {
    setSaving(true)
    setSaveMsg(null)
    try {
      const res = await fetch(`${API_BASE}/api/v2/org`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...hdrs },
        body: JSON.stringify({ name: orgName }),
      })
      setSaveMsg(res.ok ? 'Organization saved.' : 'Failed to save.')
      setTimeout(() => setSaveMsg(null), 3000)
    } catch {
      setSaveMsg('Network error.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-sardis-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Org details */}
      <div className="card p-6 space-y-5">
        <h3 className="text-base font-semibold text-white">Organization Details</h3>

        <FieldInput
          label="Organization Name"
          value={orgName}
          onChange={setOrgName}
          placeholder="Your organization"
        />

        <FieldInput
          label="Organization ID"
          value={profile?.org_id ?? '—'}
          readOnly
          hint="Used in API requests and integrations."
          suffix={profile?.org_id ? <CopyButton text={profile.org_id} /> : undefined}
        />

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-400">Your role:</p>
            <span
              className={clsx(
                'text-xs font-medium px-2.5 py-0.5 rounded-full',
                ROLE_BADGE[profile?.role ?? 'member'] ?? ROLE_BADGE.member
              )}
            >
              {profile?.role ?? 'member'}
            </span>
          </div>

          <div className="flex items-center gap-4">
            {saveMsg && (
              <p className={clsx('text-sm', saveMsg.startsWith('Organization') ? 'text-sardis-400' : 'text-red-400')}>
                {saveMsg}
              </p>
            )}
            <button
              onClick={saveOrg}
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save
            </button>
          </div>
        </div>
      </div>

      {/* Team members */}
      <div className="card p-6">
        <h3 className="text-base font-semibold text-white mb-4">Team Members</h3>

        {members.length === 0 ? (
          <div className="text-center py-8 text-gray-500 text-sm">
            No team members found — invite your team from the API or contact support.
          </div>
        ) : (
          <div className="divide-y divide-dark-100">
            {members.map((m) => (
              <div key={m.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-white">{m.display_name ?? m.email}</p>
                  {m.display_name && <p className="text-xs text-gray-500">{m.email}</p>}
                </div>
                <span
                  className={clsx(
                    'text-xs font-medium px-2.5 py-0.5 rounded-full',
                    ROLE_BADGE[m.role] ?? ROLE_BADGE.member
                  )}
                >
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── API KEYS TAB ─────────────────────────────────────────────────────────────

function ApiKeysTab({ token }: { token: string | null }) {
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchCount() {
      try {
        const res = await fetch(`${API_BASE}/api/v2/api-keys`, { headers: authHeaders(token) })
        if (res.ok) {
          const data = await res.json()
          const keys = data.keys ?? []
          setCount(keys.filter((k: { is_active: boolean }) => k.is_active).length)
        }
      } catch {
        // silent
      } finally {
        setLoading(false)
      }
    }
    fetchCount()
  }, [token])

  return (
    <div className="space-y-4">
      <div className="card p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center shrink-0">
            <Key className="w-5 h-5 text-sardis-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white">API Keys</h3>
            <p className="text-sm text-gray-400 mt-0.5">
              Manage programmatic access keys for your agents and integrations.
            </p>
            {!loading && count !== null && (
              <p className="text-xs text-gray-500 mt-2">
                <span className="text-sardis-400 font-medium">{count}</span> active{' '}
                {count === 1 ? 'key' : 'keys'}
              </p>
            )}
          </div>
          <Link
            to="/api-keys"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors shrink-0"
          >
            Manage Keys
            <ExternalLink className="w-4 h-4" />
          </Link>
        </div>
      </div>

      <div className="card p-5 border-dark-100/50">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          Keep your API keys secret. Never expose them in client-side code or public repositories.
        </div>
      </div>
    </div>
  )
}

// ── BILLING TAB ──────────────────────────────────────────────────────────────

const PLAN_BADGE: Record<string, string> = {
  free: 'bg-gray-500/20 text-gray-300 border border-gray-500/30',
  starter: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  growth: 'bg-sardis-500/20 text-sardis-300 border border-sardis-500/30',
  enterprise: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
}

function BillingTab({ token }: { token: string | null }) {
  const [plan, setPlan] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('active')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchBilling() {
      try {
        const res = await fetch(`${API_BASE}/api/v2/billing/account`, { headers: authHeaders(token) })
        if (res.ok) {
          const data = await res.json()
          setPlan(data.plan ?? 'free')
          setStatus(data.status ?? 'active')
        } else {
          setPlan('free')
        }
      } catch {
        setPlan('free')
      } finally {
        setLoading(false)
      }
    }
    fetchBilling()
  }, [token])

  return (
    <div className="space-y-4">
      <div className="card p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center shrink-0">
            <CreditCard className="w-5 h-5 text-sardis-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white">Billing & Plan</h3>
            <p className="text-sm text-gray-400 mt-0.5">
              View your current plan, usage meters, and payment details.
            </p>
            {!loading && plan && (
              <div className="flex items-center gap-2 mt-2">
                <span
                  className={clsx(
                    'text-xs font-semibold px-2.5 py-0.5 rounded-full',
                    PLAN_BADGE[plan] ?? PLAN_BADGE.free
                  )}
                >
                  {plan.charAt(0).toUpperCase() + plan.slice(1)}
                </span>
                <span
                  className={clsx(
                    'text-xs font-medium px-2 py-0.5 rounded-full',
                    status === 'active'
                      ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  )}
                >
                  {status}
                </span>
              </div>
            )}
          </div>
          <Link
            to="/billing"
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors shrink-0"
          >
            Manage Billing
            <ExternalLink className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Quick-nav links */}
      {[
        { label: 'View plan comparison', to: '/billing', desc: 'Upgrade or downgrade your plan' },
        { label: 'Usage meters', to: '/billing', desc: 'API calls, agents, and volume limits' },
      ].map((item) => (
        <Link
          key={item.label}
          to={item.to}
          className="card p-4 flex items-center justify-between group hover:border-sardis-500/30 transition-colors"
        >
          <div>
            <p className="text-sm font-medium text-white group-hover:text-sardis-300 transition-colors">
              {item.label}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-sardis-400 transition-colors" />
        </Link>
      ))}
    </div>
  )
}

// ── NOTIFICATIONS TAB ────────────────────────────────────────────────────────

const SEVERITIES = ['info', 'warning', 'critical'] as const
type Severity = typeof SEVERITIES[number]

const SEVERITY_COLORS: Record<Severity, string> = {
  info: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
  warning: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  critical: 'bg-red-500/20 text-red-300 border border-red-500/30',
}

function NotificationsTab({ token }: { token: string | null }) {
  const [channels, setChannels] = useState<AlertChannel[]>([])
  const [loading, setLoading] = useState(true)

  // Slack form state
  const [slackUrl, setSlackUrl] = useState('')
  const [slackSeverities, setSlackSeverities] = useState<Severity[]>(['warning', 'critical'])
  const [slackSaving, setSlackSaving] = useState(false)
  const [slackMsg, setSlackMsg] = useState<string | null>(null)
  const [slackTesting, setSlackTesting] = useState(false)

  // Email toggle
  const [emailEnabled, setEmailEnabled] = useState(true)
  const [emailSeverities, setEmailSeverities] = useState<Severity[]>(['warning', 'critical'])
  const [emailSaving, setEmailSaving] = useState(false)
  const [emailMsg, setEmailMsg] = useState<string | null>(null)
  const [emailTesting, setEmailTesting] = useState(false)

  // Alert type toggles (legacy from old Settings)
  const [alertPrefs, setAlertPrefs] = useState({
    transaction: true,
    risk: true,
    daily_summary: false,
    webhook_failures: true,
  })

  const hdrs = authHeaders(token)

  const fetchChannels = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/alerts/channels`, { headers: hdrs })
      if (res.ok) {
        const data = await res.json()
        const list: AlertChannel[] = Array.isArray(data) ? data : (data.channels ?? [])
        setChannels(list)

        const slack = list.find((c) => c.type === 'slack')
        if (slack) {
          setSlackUrl(slack.destination)
          setSlackSeverities((slack.severities ?? ['warning', 'critical']) as Severity[])
        }

        const email = list.find((c) => c.type === 'email')
        if (email) {
          setEmailEnabled(email.enabled)
          setEmailSeverities((email.severities ?? ['warning', 'critical']) as Severity[])
        }
      }
    } catch {
      // network unavailable — show empty form
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  async function saveChannel(type: 'slack' | 'email', destination: string, enabled: boolean, severities: Severity[]) {
    const existing = channels.find((c) => c.type === type)
    const method = existing ? 'PUT' : 'POST'
    const url = existing
      ? `${API_BASE}/api/v2/alerts/channels/${existing.id}`
      : `${API_BASE}/api/v2/alerts/channels`

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...hdrs },
      body: JSON.stringify({ type, destination, enabled, severities }),
    })
    return res.ok
  }

  async function testChannel(type: 'slack' | 'email') {
    const existing = channels.find((c) => c.type === type)
    if (!existing) return false
    const res = await fetch(`${API_BASE}/api/v2/alerts/channels/${existing.id}/test`, {
      method: 'POST',
      headers: hdrs,
    })
    return res.ok
  }

  async function handleSaveSlack() {
    if (!slackUrl.trim()) {
      setSlackMsg('Slack webhook URL is required.')
      return
    }
    setSlackSaving(true)
    setSlackMsg(null)
    const ok = await saveChannel('slack', slackUrl.trim(), true, slackSeverities)
    setSlackMsg(ok ? 'Slack channel saved.' : 'Failed to save Slack channel.')
    if (ok) await fetchChannels()
    setSlackSaving(false)
    setTimeout(() => setSlackMsg(null), 3000)
  }

  async function handleTestSlack() {
    setSlackTesting(true)
    const ok = await testChannel('slack')
    setSlackMsg(ok ? 'Test message sent to Slack.' : 'Test failed. Check your webhook URL.')
    setSlackTesting(false)
    setTimeout(() => setSlackMsg(null), 4000)
  }

  async function handleSaveEmail() {
    setEmailSaving(true)
    setEmailMsg(null)
    const ok = await saveChannel('email', 'account_email', emailEnabled, emailSeverities)
    setEmailMsg(ok ? 'Email preferences saved.' : 'Failed to save email preferences.')
    if (ok) await fetchChannels()
    setEmailSaving(false)
    setTimeout(() => setEmailMsg(null), 3000)
  }

  async function handleTestEmail() {
    setEmailTesting(true)
    const ok = await testChannel('email')
    setEmailMsg(ok ? 'Test email sent.' : 'Test failed.')
    setEmailTesting(false)
    setTimeout(() => setEmailMsg(null), 4000)
  }

  function toggleSeverity(
    current: Severity[],
    set: (v: Severity[]) => void,
    s: Severity
  ) {
    set(current.includes(s) ? current.filter((x) => x !== s) : [...current, s])
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-sardis-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Alert type toggles */}
      <div className="card p-6">
        <h3 className="text-base font-semibold text-white mb-4">Alert Preferences</h3>
        <div className="space-y-1 divide-y divide-dark-100">
          {(
            [
              { key: 'transaction', label: 'Transaction alerts', desc: 'Get notified of high-value transactions' },
              { key: 'risk', label: 'Risk alerts', desc: 'Receive alerts for suspicious activity' },
              { key: 'daily_summary', label: 'Daily summary', desc: 'Daily digest of agent activity' },
              { key: 'webhook_failures', label: 'Webhook failures', desc: 'Alert when webhook delivery fails' },
            ] as const
          ).map((item) => (
            <div key={item.key} className="flex items-center justify-between py-3">
              <div>
                <p className="text-sm font-medium text-white">{item.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{item.desc}</p>
              </div>
              <Toggle
                enabled={alertPrefs[item.key]}
                onChange={(v) => setAlertPrefs((prev) => ({ ...prev, [item.key]: v }))}
                label={item.label}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Slack channel */}
      <div className="card p-6 space-y-4">
        <h3 className="text-base font-semibold text-white">Slack Notifications</h3>

        <FieldInput
          label="Slack Webhook URL"
          value={slackUrl}
          onChange={setSlackUrl}
          placeholder="https://hooks.slack.com/services/..."
          hint="Paste your Slack Incoming Webhook URL to receive alerts in a channel."
        />

        <div>
          <p className="text-sm font-medium text-gray-300 mb-2">Notify on severity</p>
          <div className="flex gap-2 flex-wrap">
            {SEVERITIES.map((s) => (
              <button
                key={s}
                onClick={() => toggleSeverity(slackSeverities, setSlackSeverities, s)}
                className={clsx(
                  'text-xs font-medium px-3 py-1 rounded-full border transition-colors',
                  slackSeverities.includes(s)
                    ? SEVERITY_COLORS[s]
                    : 'bg-dark-200 text-gray-500 border-dark-100 hover:text-gray-300'
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {slackMsg && (
          <p className={clsx('text-sm', slackMsg.includes('Failed') || slackMsg.includes('required') ? 'text-red-400' : 'text-sardis-400')}>
            {slackMsg}
          </p>
        )}

        <div className="flex gap-3 justify-end">
          <button
            onClick={handleTestSlack}
            disabled={slackTesting || !channels.find((c) => c.type === 'slack')}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-dark-200 border border-dark-100 text-gray-300 hover:text-white transition-colors disabled:opacity-40"
            title={!channels.find((c) => c.type === 'slack') ? 'Save first to test' : ''}
          >
            {slackTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Test
          </button>
          <button
            onClick={handleSaveSlack}
            disabled={slackSaving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50"
          >
            {slackSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Slack
          </button>
        </div>
      </div>

      {/* Email channel */}
      <div className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">Email Notifications</h3>
          <Toggle enabled={emailEnabled} onChange={setEmailEnabled} label="Email notifications" />
        </div>

        {emailEnabled && (
          <>
            <div>
              <p className="text-sm font-medium text-gray-300 mb-2">Notify on severity</p>
              <div className="flex gap-2 flex-wrap">
                {SEVERITIES.map((s) => (
                  <button
                    key={s}
                    onClick={() => toggleSeverity(emailSeverities, setEmailSeverities, s)}
                    className={clsx(
                      'text-xs font-medium px-3 py-1 rounded-full border transition-colors',
                      emailSeverities.includes(s)
                        ? SEVERITY_COLORS[s]
                        : 'bg-dark-200 text-gray-500 border-dark-100 hover:text-gray-300'
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-gray-500">
              Alerts will be sent to the email address on your account.
            </p>
          </>
        )}

        {emailMsg && (
          <p className={clsx('text-sm', emailMsg.includes('Failed') ? 'text-red-400' : 'text-sardis-400')}>
            {emailMsg}
          </p>
        )}

        <div className="flex gap-3 justify-end">
          {emailEnabled && (
            <button
              onClick={handleTestEmail}
              disabled={emailTesting || !channels.find((c) => c.type === 'email')}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-dark-200 border border-dark-100 text-gray-300 hover:text-white transition-colors disabled:opacity-40"
              title={!channels.find((c) => c.type === 'email') ? 'Save first to test' : ''}
            >
              {emailTesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Test
            </button>
          )}
          <button
            onClick={handleSaveEmail}
            disabled={emailSaving}
            className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50"
          >
            {emailSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Email
          </button>
        </div>
      </div>
    </div>
  )
}

// ── MAIN PAGE ────────────────────────────────────────────────────────────────

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'organization', label: 'Organization', icon: <Building2 className="w-4 h-4" /> },
  { id: 'api-keys', label: 'API Keys', icon: <Key className="w-4 h-4" /> },
  { id: 'billing', label: 'Billing', icon: <CreditCard className="w-4 h-4" /> },
  { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
]

function getInitialTab(): TabId {
  const hash = window.location.hash.replace('#', '')
  return TABS.some((t) => t.id === hash) ? (hash as TabId) : 'profile'
}

export default function SettingsPage() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab)

  function switchTab(id: TabId) {
    setActiveTab(id)
    window.location.hash = id
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Settings</h1>
        <p className="text-gray-400 mt-1">Configure your Sardis account and integrations</p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-dark-100">
        <nav className="-mb-px flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => switchTab(tab.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-sardis-500 text-sardis-400'
                  : 'border-transparent text-gray-400 hover:text-white hover:border-dark-100'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'profile' && <ProfileTab token={token} />}
        {activeTab === 'organization' && <OrganizationTab token={token} />}
        {activeTab === 'api-keys' && <ApiKeysTab token={token} />}
        {activeTab === 'billing' && <BillingTab token={token} />}
        {activeTab === 'notifications' && <NotificationsTab token={token} />}
      </div>
    </div>
  )
}
