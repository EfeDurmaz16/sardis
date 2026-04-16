"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { CheckCircle, ShieldCheck, Warning } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import {
  getKycStatus,
  initiateKyc,
  type KycStatus,
} from "@/lib/sardis-api"
import type { StepContext } from "../onboarding-wizard"

const POLL_INTERVAL_MS = 5_000

const TERMINAL_STATUSES: KycStatus[] = ["approved", "declined", "expired"]

export function KycStep({ ctx }: { ctx: StepContext }) {
  const [status, setStatus] = useState<KycStatus | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cancelled = useRef(false)

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current)
      pollTimer.current = null
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      const result = await getKycStatus()
      if (cancelled.current) return
      setStatus(result.status)
      setReason(result.reason)
    } catch (err) {
      console.error("[onboarding/kyc] status fetch failed", err)
    }
  }, [])

  useEffect(() => {
    cancelled.current = false
    void refresh()
    return () => {
      cancelled.current = true
      stopPolling()
    }
  }, [refresh, stopPolling])

  // Poll while pending or needs_review.
  useEffect(() => {
    stopPolling()
    if (status && !TERMINAL_STATUSES.includes(status) && status !== "not_started") {
      pollTimer.current = setTimeout(() => {
        void refresh()
      }, POLL_INTERVAL_MS)
    }
    return stopPolling
  }, [status, refresh, stopPolling])

  const startVerification = useCallback(async () => {
    setStarting(true)
    setError(null)
    try {
      const result = await initiateKyc()
      if (result.redirect_url) {
        window.open(result.redirect_url, "_blank", "noopener,noreferrer")
      }
      // Optimistically flip to pending so the polling loop kicks in.
      setStatus("pending")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start verification")
    } finally {
      setStarting(false)
    }
  }, [])

  const isApproved = status === "approved"
  const isPending = status === "pending" || status === "needs_review"
  const isDeclined = status === "declined" || status === "expired"

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        We need to verify your identity for regulatory compliance. Didit handles the
        verification flow and it takes about two minutes.
      </p>

      {error && (
        <div className="rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {isApproved && (
        <div className="flex items-start gap-2 rounded border border-emerald-500/40 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
          <CheckCircle className="mt-0.5 size-4 shrink-0" weight="fill" />
          <span>Identity verified. You can use mainnet from your live API key.</span>
        </div>
      )}

      {isPending && (
        <div className="flex items-start gap-2 rounded border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>
            Verification in progress. This page checks status every 5 seconds — you can
            keep this tab open while you finish in the Didit window.
          </span>
        </div>
      )}

      {isDeclined && (
        <div className="flex items-start gap-2 rounded border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm text-amber-600 dark:text-amber-400">
          <Warning className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>
            Verification {status === "expired" ? "expired" : "was declined"}
            {reason ? `: ${reason}` : "."} You can retry below.
          </span>
        </div>
      )}

      {(status === "not_started" || isDeclined) && (
        <Button
          type="button"
          size="sm"
          onClick={startVerification}
          disabled={starting || ctx.pending}
        >
          {starting ? "Starting…" : "Start verification"}
        </Button>
      )}

      <div className="rounded border border-dashed border-border bg-background/40 px-3 py-2 text-xs text-muted-foreground">
        You can skip this for now and finish onboarding, but you will not be able to
        execute mainnet transactions until KYC is complete.
      </div>

      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={ctx.goSkip}
          disabled={ctx.pending}
        >
          I will do this later
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={ctx.goNext}
          disabled={!isApproved || ctx.pending}
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
