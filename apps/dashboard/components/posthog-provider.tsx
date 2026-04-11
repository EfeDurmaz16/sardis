"use client"

import { useEffect } from "react"
import posthog from "posthog-js"
import { getCookieConsent } from "@/components/cookie-consent"
import { useSession } from "@/lib/auth-client"

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
  const session = useSession()
  const user = session.data?.user

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

  useEffect(() => {
    if (!initialized) return
    if (user?.id) {
      posthog.identify(user.id, {
        email: user.email,
        name: user.name,
      })
    } else {
      posthog.reset()
    }
  }, [user?.id, user?.email, user?.name])

  return null
}
