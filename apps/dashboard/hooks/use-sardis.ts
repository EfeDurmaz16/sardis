"use client"

import { useCallback, useEffect, useRef, useState } from "react"

type UseSardisResult<T> = {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useSardis<T>(path: string | null): UseSardisResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    if (!path) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/sardis/${path.replace(/^\//, "")}`, {
        credentials: "include",
        cache: "no-store",
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.error || `API returned ${res.status}`)
      }
      const json = await res.json()
      if (mountedRef.current) setData(json)
    } catch (err) {
      if (mountedRef.current) setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [path])

  useEffect(() => {
    mountedRef.current = true
    fetchData()
    return () => {
      mountedRef.current = false
    }
  }, [fetchData])

  return { data, loading, error, refetch: fetchData }
}
