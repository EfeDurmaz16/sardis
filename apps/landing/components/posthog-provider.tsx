"use client"

import { useEffect } from "react"
import posthog from "posthog-js"
import { getCookieConsent } from "@/components/cookie-consent"

const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com"

let initialized = false

function initPostHog() {
  if (initialized || !POSTHOG_KEY || typeof window === "undefined") return
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: true,
    capture_pageleave: true,
    persistence: "localStorage+cookie",
  })
  initialized = true
}

export function PostHogProvider() {
  useEffect(() => {
    if (!POSTHOG_KEY) return

    if (getCookieConsent() === "accepted") {
      initPostHog()
    }

    const onConsent = (event: Event) => {
      const detail = (event as CustomEvent<"accepted" | "rejected">).detail
      if (detail === "accepted") initPostHog()
    }

    window.addEventListener("sardis:cookie-consent", onConsent)
    return () => window.removeEventListener("sardis:cookie-consent", onConsent)
  }, [])

  return null
}
