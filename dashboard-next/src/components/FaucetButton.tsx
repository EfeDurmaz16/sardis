"use client";
import { useState } from 'react'
import { Droplets, Loader2 } from 'lucide-react'

export function FaucetButton() {
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

  async function handleDrip() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/v2/faucet/drip`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        credentials: 'include', body: JSON.stringify({}),
      })
      if (res.ok) { setSuccess(true); setTimeout(() => setSuccess(false), 3000) }
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  return (
    <button onClick={handleDrip} disabled={loading}
      className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full text-sm text-gray-400 hover:text-white hover:bg-dark-100 transition-colors disabled:opacity-50"
      title="Get testnet USDC">
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Droplets className="w-4 h-4 text-blue-400" />}
      {success ? 'Sent!' : 'Faucet'}
    </button>
  )
}
