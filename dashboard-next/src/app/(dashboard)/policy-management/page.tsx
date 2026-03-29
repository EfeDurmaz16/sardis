"use client";

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function PolicyManagementRedirect() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/policy-manager')
  }, [router])
  return (
    <p className="text-sm text-gray-400 p-8">Redirecting to Policy Manager...</p>
  )
}
