/**
 * KYCBanner — shows identity verification status as a dismissible top-of-page banner.
 *
 * Behaviour:
 * - Fetches GET /api/v2/kyc/status on mount
 * - Renders a coloured banner based on status (not_started | pending | approved | rejected | expired)
 * - "Verify Now" / "Retry" / "Re-verify" calls POST /api/v2/kyc/initiate and opens redirect_url
 * - Silently hides on 503 (KYC not configured) or any network error
 * - Dismissible via X — persisted in sessionStorage for the browser session
 * - "approved" banner auto-dismisses after 5 s
 */

import { useEffect, useState, useRef } from 'react'
import {
  CheckCircle,
  Clock,
  ShieldWarning,
  SpinnerGap,
  Warning,
  X,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'

const API_BASE = import.meta.env.VITE_API_URL || ''
const DISMISS_KEY = 'sardis_kyc_banner_dismissed'

type KYCStatus = 'not_started' | 'pending' | 'approved' | 'rejected' | 'expired'

interface KYCStatusResponse {
  status: KYCStatus
  provider?: string
  verified_at?: string
  expires_at?: string
}

interface KYCInitiateResponse {
  redirect_url: string
  session_token?: string
  provider?: string
  message?: string
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

export default function KYCBanner() {
  const { token } = useAuth()
  const [kycStatus, setKycStatus] = useState<KYCStatusResponse | null>(null)
  const [visible, setVisible] = useState(false)
  const [initiating, setInitiating] = useState(false)
  const autoDismissRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    // If the user already dismissed the banner this session, skip the fetch entirely
    if (sessionStorage.getItem(DISMISS_KEY) === '1') return

    async function fetchStatus() {
      try {
        const res = await fetch(`${API_BASE}/api/v2/kyc/status`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })

        // 503 = KYC not configured — hide banner
        if (res.status === 503) return

        if (!res.ok) return

        const data: KYCStatusResponse = await res.json()
        setKycStatus(data)
        setVisible(true)

        // Auto-dismiss approved banner after 5 s
        if (data.status === 'approved') {
          autoDismissRef.current = setTimeout(() => setVisible(false), 5000)
        }
      } catch {
        // Network error — hide banner
      }
    }

    fetchStatus()

    // Poll every 3s while status is pending (waiting for webhook)
    const pollId = setInterval(async () => {
      if (kycStatus?.status !== 'pending' && kycStatus?.status !== 'not_started') return
      try {
        const res = await fetch(`${API_BASE}/api/v2/kyc/status`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        if (res.ok) {
          const data: KYCStatusResponse = await res.json()
          if (data.status !== kycStatus?.status) {
            setKycStatus(data)
            if (data.status === 'approved') {
              autoDismissRef.current = setTimeout(() => setVisible(false), 5000)
            }
          }
        }
      } catch { /* ignore */ }
    }, 3000)

    return () => {
      clearInterval(pollId)
      if (autoDismissRef.current) clearTimeout(autoDismissRef.current)
    }
  }, [token, kycStatus?.status])

  function dismiss() {
    sessionStorage.setItem(DISMISS_KEY, '1')
    setVisible(false)
  }

  async function handleInitiate() {
    setInitiating(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/kyc/initiate`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data: KYCInitiateResponse = await res.json()
        if (data.redirect_url) {
          window.open(data.redirect_url, '_blank', 'noopener,noreferrer')
        }
      }
    } catch {
      // silently ignore
    } finally {
      setInitiating(false)
    }
  }

  if (!visible || !kycStatus) return null

  const config = BANNER_CONFIG[kycStatus.status]
  if (!config) return null

  return (
    <div
      className={clsx(
        'flex items-center gap-3 px-4 py-3 rounded-lg border text-sm transition-all',
        config.wrapper
      )}
      role="alert"
    >
      {/* Icon */}
      <div className="shrink-0">{config.icon}</div>

      {/* Message */}
      <div className="flex-1 min-w-0">
        <span className={clsx('font-medium', config.textPrimary)}>{config.message}</span>
        {kycStatus.status === 'approved' && kycStatus.verified_at && (
          <span className={clsx('ml-2 text-xs', config.textSecondary)}>
            Verified {formatDate(kycStatus.verified_at)}
            {kycStatus.expires_at ? ` · Expires ${formatDate(kycStatus.expires_at)}` : ''}
          </span>
        )}
        {kycStatus.status === 'pending' && (
          <span className={clsx('ml-2 text-xs', config.textSecondary)}>
            This usually takes a few minutes.
          </span>
        )}
      </div>

      {/* CTA button */}
      {config.ctaLabel && (
        <button
          onClick={handleInitiate}
          disabled={initiating}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded shrink-0 transition-colors disabled:opacity-50',
            config.ctaClass
          )}
        >
          {initiating && <SpinnerGap className="w-3.5 h-3.5 animate-spin" />}
          {config.ctaLabel}
        </button>
      )}

      {/* Dismiss */}
      <button
        onClick={dismiss}
        className={clsx('shrink-0 p-0.5 rounded transition-colors', config.dismissClass)}
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

// ── Banner variant config ─────────────────────────────────────────────────────

interface BannerConfig {
  wrapper: string
  icon: React.ReactNode
  message: string
  textPrimary: string
  textSecondary: string
  ctaLabel?: string
  ctaClass?: string
  dismissClass: string
}

const BANNER_CONFIG: Record<KYCStatus, BannerConfig> = {
  not_started: {
    wrapper: 'bg-amber-500/10 border-amber-500/30',
    icon: <Warning className="w-4 h-4 text-amber-400" />,
    message: 'Complete identity verification to enable live payments.',
    textPrimary: 'text-amber-300',
    textSecondary: 'text-amber-400/70',
    ctaLabel: 'Verify Now',
    ctaClass: 'bg-amber-500 text-dark-400 hover:bg-amber-400',
    dismissClass: 'text-amber-400/60 hover:text-amber-300',
  },
  pending: {
    wrapper: 'bg-blue-500/10 border-blue-500/30',
    icon: <Clock className="w-4 h-4 text-blue-400 animate-pulse" />,
    message: 'Verification in progress…',
    textPrimary: 'text-blue-300',
    textSecondary: 'text-blue-400/70',
    dismissClass: 'text-blue-400/60 hover:text-blue-300',
  },
  approved: {
    wrapper: 'bg-green-500/10 border-green-500/30',
    icon: <CheckCircle className="w-4 h-4 text-green-400" />,
    message: 'Identity verified.',
    textPrimary: 'text-green-300',
    textSecondary: 'text-green-400/70',
    dismissClass: 'text-green-400/60 hover:text-green-300',
  },
  rejected: {
    wrapper: 'bg-red-500/10 border-red-500/30',
    icon: <ShieldWarning className="w-4 h-4 text-red-400" />,
    message: 'Verification failed. Please try again.',
    textPrimary: 'text-red-300',
    textSecondary: 'text-red-400/70',
    ctaLabel: 'Retry',
    ctaClass: 'bg-red-500 text-white hover:bg-red-400',
    dismissClass: 'text-red-400/60 hover:text-red-300',
  },
  expired: {
    wrapper: 'bg-amber-500/10 border-amber-500/30',
    icon: <Warning className="w-4 h-4 text-amber-400" />,
    message: 'Verification expired. Please re-verify.',
    textPrimary: 'text-amber-300',
    textSecondary: 'text-amber-400/70',
    ctaLabel: 'Re-verify',
    ctaClass: 'bg-amber-500 text-dark-400 hover:bg-amber-400',
    dismissClass: 'text-amber-400/60 hover:text-amber-300',
  },
}
