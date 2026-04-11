"use client"

import { useEffect } from "react"
import Intercom, { shutdown, update } from "@intercom/messenger-js-sdk"
import { getCookieConsent } from "@/components/cookie-consent"
import { useSession } from "@/lib/auth-client"

const INTERCOM_APP_ID = process.env.NEXT_PUBLIC_INTERCOM_APP_ID

let booted = false

function bootIntercom() {
  if (booted || !INTERCOM_APP_ID || typeof window === "undefined") return
  Intercom({ app_id: INTERCOM_APP_ID })
  booted = true
}

function toUnixSeconds(value: Date | string | number | null | undefined): number | undefined {
  if (value == null) return undefined
  const ms = value instanceof Date ? value.getTime() : new Date(value).getTime()
  if (Number.isNaN(ms)) return undefined
  return Math.floor(ms / 1000)
}

export function IntercomProvider() {
  const session = useSession()
  const user = session.data?.user

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

  useEffect(() => {
    if (!booted) return
    if (user?.id) {
      update({
        user_id: user.id,
        email: user.email ?? undefined,
        name: user.name ?? undefined,
        created_at: toUnixSeconds((user as { createdAt?: Date | string }).createdAt),
      })
    } else {
      shutdown()
      booted = false
    }
  }, [user?.id, user?.email, user?.name])

  return null
}
