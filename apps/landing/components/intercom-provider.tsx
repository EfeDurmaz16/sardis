"use client"

import { useEffect } from "react"
import Intercom from "@intercom/messenger-js-sdk"
import { getCookieConsent } from "@/components/cookie-consent"

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID

let booted = false

function bootIntercom() {
  if (booted || !INTERCOM_APP_ID || typeof window === "undefined") return
  Intercom({ app_id: INTERCOM_APP_ID })
  booted = true
}

export function IntercomProvider() {
  useEffect(() => {
    if (!INTERCOM_APP_ID) return

    if (getCookieConsent() === "accepted") {
      bootIntercom()
    }

    const onConsent = (event: Event) => {
      const detail = (event as CustomEvent<"accepted" | "rejected">).detail
      if (detail === "accepted") bootIntercom()
    }

    window.addEventListener("sardis:cookie-consent", onConsent)
    return () => window.removeEventListener("sardis:cookie-consent", onConsent)
  }, [])

  return null
}
