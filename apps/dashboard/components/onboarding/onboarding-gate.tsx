"use client"

import { useEffect, useState } from "react"

import { AuthRequiredError, getOnboarding, type OnboardingState } from "@/lib/sardis-api"
import { isTourCompleted, startProductTour } from "@/lib/product-tour"
import { OnboardingWizard } from "./onboarding-wizard"

/**
 * Mounts inside the dashboard shell. On first render fetches the
 * caller's onboarding state. If the wizard has not yet been completed
 * (``completed_at`` is null), opens the wizard at whichever step the
 * user last left off on. Silently no-ops on auth errors so signed-out
 * preview/SSR fallthroughs do not throw.
 */
export function OnboardingGate() {
  const [state, setState] = useState<OnboardingState | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const initial = await getOnboarding()
        if (cancelled) return
        setState(initial)
        if (!initial.completed_at) {
          setOpen(true)
        }
      } catch (err) {
        if (err instanceof AuthRequiredError) return
        console.error("[onboarding-gate] failed to load state", err)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!state) return null

  return (
    <OnboardingWizard
      initialState={state}
      open={open}
      onOpenChange={setOpen}
      onComplete={() => {
        setOpen(false)
        if (!isTourCompleted()) {
          // Give the wizard dialog a frame to unmount before driver.js
          // takes over the viewport.
          setTimeout(() => {
            void startProductTour()
          }, 300)
        }
      }}
    />
  )
}
