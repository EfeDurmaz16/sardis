"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"

const STORAGE_KEY = "sardis:cookie-consent"

export type CookieConsentValue = "accepted" | "rejected"

export function getCookieConsent(): CookieConsentValue | null {
  if (typeof window === "undefined") return null
  const v = window.localStorage.getItem(STORAGE_KEY)
  return v === "accepted" || v === "rejected" ? v : null
}

export function CookieConsent() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (getCookieConsent() === null) setVisible(true)
    })
    return () => cancelAnimationFrame(frame)
  }, [])

  const decide = (value: CookieConsentValue) => {
    window.localStorage.setItem(STORAGE_KEY, value)
    window.dispatchEvent(new CustomEvent("sardis:cookie-consent", { detail: value }))
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      role="dialog"
      aria-label="Cookie consent"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4 text-sm text-foreground sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground">
          We use cookies for essential site functionality and, with your permission, analytics to improve Sardis. No analytics fire until you accept.
        </p>
        <div className="flex shrink-0 gap-2">
          <Button variant="outline" size="sm" onClick={() => decide("rejected")}>
            Reject
          </Button>
          <Button size="sm" onClick={() => decide("accepted")}>
            Accept
          </Button>
        </div>
      </div>
    </div>
  )
}
