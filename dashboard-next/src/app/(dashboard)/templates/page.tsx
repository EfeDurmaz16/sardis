"use client";

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TemplatesRedirect() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/workflow-templates')
  }, [router])
  return (
    <p className="text-sm text-gray-400 p-8">Redirecting to Workflow Templates...</p>
  )
}
