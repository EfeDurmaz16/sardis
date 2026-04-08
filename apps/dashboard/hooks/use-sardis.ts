"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { extractListOrThrow } from "@/lib/collection-response"

type UseSardisResult<T> = {
  data: T | null
  loading: boolean
  error: string | null
  refetch: () => void
}

type UseSardisOptions<T> = {
  normalize?: (payload: unknown) => T
}

export function useSardis<T>(path: string | null, options: UseSardisOptions<T> = {}): UseSardisResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)
  const normalizeRef = useRef(options.normalize)

  useEffect(() => {
    normalizeRef.current = options.normalize
  }, [options.normalize])

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
      const normalized = normalizeRef.current ? normalizeRef.current(json) : (json as T)
      if (mountedRef.current) setData(normalized)
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
export function useSardisList<T>(path: string | null, label = "API response"): UseSardisResult<T[]> {
  return useSardis<T[]>(path, {
    normalize: (payload) => extractListOrThrow<T>(payload, label),
  })
}
