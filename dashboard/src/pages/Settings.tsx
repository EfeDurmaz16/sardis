
import { useState } from 'react'
import {
  Key,
  Shield,
  DollarSign,
  Bell,
  Globe,
  Copy,
  Check,
  RefreshCw,
  Plus
} from 'lucide-react'
import clsx from 'clsx'
import { useAuth } from '../auth/AuthContext'

export default function SettingsPage() {
  const [copied, setCopied] = useState(false)
  const [generatedKey, setGeneratedKey] = useState<string | null>(null)
  const [keyName, setKeyName] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [activeKey, setActiveKey] = useState(localStorage.getItem('sardis_api_key') || '')
  const { token } = useAuth()

  const copyApiKey = () => {
    if (generatedKey) {
      navigator.clipboard.writeText(generatedKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const generateKey = async () => {
    if (!keyName) return;
    setIsGenerating(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: keyName,
          owner_id: 'admin_dashboard' // In a real app, this would be the logged-in user's ID
        })
      });

      if (response.ok) {
        const data = await response.json();
        setGeneratedKey(data.api_key);
        // Automatically set as active key for the dashboard
        localStorage.setItem('sardis_api_key', data.api_key);
        setActiveKey(data.api_key);
      }
    } catch (error) {
      console.error('Failed to generate key', error);
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Settings</h1>
        <p className="text-gray-400 mt-1">
          Configure your Sardis integration
        </p>
      </div>

      {/* API Keys */}
      <section className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <Key className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">API Keys</h2>
            <p className="text-sm text-gray-400">Manage your API access</p>
          </div>
        </div>

        <div className="space-y-4">
          {activeKey && (
            <div className="mb-6 p-4 bg-sardis-500/10 border border-sardis-500/20 rounded-lg">
              <label className="block text-sm font-medium text-sardis-400 mb-1">
                Active Dashboard Key
              </label>
              <div className="font-mono text-sm text-white break-all">
                {activeKey}
              </div>
            </div>
          )}

          {!generatedKey ? (
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-400 mb-2">
                  Key Name
                </label>
                <input
                  type="text"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g. Production Key"
                  className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
                />
              </div>
              <button
                onClick={generateKey}
                disabled={!keyName || isGenerating}
                className="px-6 py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isGenerating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
                Generate Key
              </button>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">
                New API Key (Copy now, it won't be shown again)
              </label>
              <div className="flex gap-2">
                <div className="flex-1 px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg font-mono text-sm text-green-400 break-all">
                  {generatedKey}
                </div>
                <button
                  onClick={copyApiKey}
                  className="px-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-gray-400 hover:text-white transition-colors"
                >
                  {copied ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                </button>
                <button
                  onClick={() => {
                    setGeneratedKey(null);
                    setKeyName('');
                  }}
                  className="px-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-gray-400 hover:text-white transition-colors"
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}

          <p className="text-xs text-gray-500">
            Keep your API key secret. Do not share it or expose it in client-side code.
          </p>
        </div>
      </section>

      {/* Fee Configuration */}
      <section className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Fee Configuration</h2>
            <p className="text-sm text-gray-400">Transaction fee settings</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Base Fee (USDC)
            </label>
            <input
              type="text"
              defaultValue="0.10"
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Percentage Fee
            </label>
            <input
              type="text"
              defaultValue="0%"
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Max Fee (USDC)
            </label>
            <input
              type="text"
              defaultValue="10.00"
              className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
            />
          </div>
        </div>
      </section>

      {/* Risk Thresholds */}
      <section className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Risk Thresholds</h2>
            <p className="text-sm text-gray-400">Configure fraud prevention</p>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-400">
                Block Threshold
              </label>
              <span className="text-sm text-white">90</span>
            </div>
            <input
              type="range"
              min="50"
              max="100"
              defaultValue="90"
              className="w-full h-2 bg-dark-300 rounded-lg appearance-none cursor-pointer"
            />
            <p className="text-xs text-gray-500 mt-1">
              Transactions with risk score above this will be blocked
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-400">
                Alert Threshold
              </label>
              <span className="text-sm text-white">70</span>
            </div>
            <input
              type="range"
              min="30"
              max="90"
              defaultValue="70"
              className="w-full h-2 bg-dark-300 rounded-lg appearance-none cursor-pointer"
            />
            <p className="text-xs text-gray-500 mt-1">
              Transactions with risk score above this will trigger alerts
            </p>
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <Bell className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Notifications</h2>
            <p className="text-sm text-gray-400">Email and alert preferences</p>
          </div>
        </div>

        <div className="space-y-4">
          {[
            { label: 'Transaction alerts', description: 'Get notified of high-value transactions', enabled: true },
            { label: 'Risk alerts', description: 'Receive alerts for suspicious activity', enabled: true },
            { label: 'Daily summary', description: 'Daily digest of agent activity', enabled: false },
            { label: 'Webhook failures', description: 'Alert when webhook delivery fails', enabled: true },
          ].map((item, i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-dark-100 last:border-0">
              <div>
                <p className="text-sm font-medium text-white">{item.label}</p>
                <p className="text-xs text-gray-500">{item.description}</p>
              </div>
              <button
                className={clsx(
                  'w-12 h-6 rounded-full transition-colors relative',
                  item.enabled ? 'bg-sardis-500' : 'bg-dark-100'
                )}
              >
                <div className={clsx(
                  'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                  item.enabled ? 'translate-x-7' : 'translate-x-1'
                )} />
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Supported Chains */}
      <section className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-sardis-500/10 rounded-lg flex items-center justify-center">
            <Globe className="w-5 h-5 text-sardis-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Supported Chains</h2>
            <p className="text-sm text-gray-400">Blockchain network configuration</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: 'Base', status: 'active', color: '#0052FF' },
            { name: 'Polygon', status: 'active', color: '#8247E5' },
            { name: 'Ethereum', status: 'active', color: '#627EEA' },
            { name: 'Solana', status: 'coming', color: '#14F195' },
          ].map((chain) => (
            <div
              key={chain.name}
              className={clsx(
                'p-4 rounded-lg border',
                chain.status === 'active'
                  ? 'border-sardis-500/30 bg-sardis-500/5'
                  : 'border-dark-100 bg-dark-300'
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: chain.color }}
                />
                <span className="font-medium text-white">{chain.name}</span>
              </div>
              <span className={clsx(
                'text-xs',
                chain.status === 'active' ? 'text-sardis-400' : 'text-gray-500'
              )}>
                {chain.status === 'active' ? 'Active' : 'Coming Soon'}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Save Button */}
      <div className="flex justify-end">
        <button className="px-6 py-3 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover">
          Save Changes
        </button>
      </div>
    </div>
  )
}
