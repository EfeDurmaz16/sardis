import { useState, useEffect } from 'react'
import {
  Sparkles,
  AlertCircle,
  Check,
  X,
  ChevronDown,
  DollarSign,
  Shield,
  Clock,
  Ban,
  Info
} from 'lucide-react'
import clsx from 'clsx'

interface SpendingLimit {
  vendor_pattern: string
  max_amount: number
  period: string
  currency: string
}

interface CategoryRestrictions {
  allowed_categories: string[]
  blocked_categories: string[]
}

interface ParsedPolicy {
  name: string
  description: string
  spending_limits: SpendingLimit[]
  category_restrictions?: CategoryRestrictions
  requires_approval_above?: number
  global_daily_limit?: number
  global_monthly_limit?: number
  is_active: boolean
  warnings: string[]
}

interface Template {
  name: string
  description: string
  trust_level: string
  per_tx?: string
  daily?: string
  monthly?: string
}

interface PolicyBuilderProps {
  agentId?: string
  onPolicyCreated?: (policyId: string) => void
}

export default function PolicyBuilder({ agentId, onPolicyCreated }: PolicyBuilderProps) {
  const [naturalLanguage, setNaturalLanguage] = useState('')
  const [parsedPolicy, setParsedPolicy] = useState<ParsedPolicy | null>(null)
  const [templates, setTemplates] = useState<Record<string, Template>>({})
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ allowed: boolean; reason: string } | null>(null)
  const [showTemplates, setShowTemplates] = useState(false)

  // Fetch templates on mount
  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/v2/policies/templates')
      const data = await response.json()
      setTemplates(data.templates || {})
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    }
  }

  const handleParse = async () => {
    if (!naturalLanguage.trim()) {
      setError('Please enter a policy description')
      return
    }

    setLoading(true)
    setError(null)
    setParsedPolicy(null)

    try {
      const response = await fetch('/api/v2/policies/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          natural_language: naturalLanguage,
          agent_id: agentId,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to parse policy')
      }

      const data = await response.json()
      setParsedPolicy(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse policy')
    } finally {
      setLoading(false)
    }
  }

  const handleTestPolicy = async () => {
    if (!parsedPolicy || !agentId) return

    setLoading(true)
    try {
      // This would need to be implemented - preview what would be blocked
      const response = await fetch('/api/v2/policies/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          natural_language: naturalLanguage,
          agent_id: agentId,
          confirm: false,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to preview policy')
      }

      const data = await response.json()
      setTestResult({ allowed: true, reason: data.confirmation_message })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test policy')
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePolicy = async () => {
    if (!parsedPolicy || !agentId) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v2/policies/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          natural_language: naturalLanguage,
          agent_id: agentId,
          confirm: true,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create policy')
      }

      const data = await response.json()
      if (onPolicyCreated && data.policy_id) {
        onPolicyCreated(data.policy_id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create policy')
    } finally {
      setLoading(false)
    }
  }

  const handleTemplateSelect = (templateKey: string) => {
    setSelectedTemplate(templateKey)
    setShowTemplates(false)

    // Generate example natural language based on template
    const examples: Record<string, string> = {
      saas_only: 'Max $500 per transaction, SaaS and digital services only, $5000 monthly limit',
      procurement: 'Allow AWS, Google, Azure, GitHub, and Stripe with $1000 per transaction, $10000 monthly limit',
      travel: 'Max $2000 per transaction for travel and services, $5000 daily limit, block gambling and alcohol',
      research: 'Max $100 per transaction for data and digital tools, $1000 monthly limit',
      conservative: 'Max $50 per transaction, $100 daily limit, require approval above $100',
      cloud: 'Allow AWS, Google, Azure, DigitalOcean, and Cloudflare only, $500 per transaction, $5000 monthly limit',
      ai_ml: 'Allow OpenAI and Anthropic only, $200 per transaction, $3000 monthly limit',
    }

    setNaturalLanguage(examples[templateKey] || '')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-sardis-400" />
            Natural Language Policy Builder
          </h2>
          <p className="text-gray-400 mt-1">
            Create spending policies using plain English
          </p>
        </div>
      </div>

      {/* Template Selector */}
      <div className="bg-dark-300 border border-dark-100 rounded-lg p-4">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className="w-full flex items-center justify-between text-left"
        >
          <span className="text-sm font-medium text-gray-300">
            {selectedTemplate
              ? `Template: ${templates[selectedTemplate]?.name || selectedTemplate}`
              : 'Choose a template (optional)'}
          </span>
          <ChevronDown
            className={clsx(
              'w-5 h-5 text-gray-400 transition-transform',
              showTemplates && 'rotate-180'
            )}
          />
        </button>

        {showTemplates && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(templates).map(([key, template]) => (
              <button
                key={key}
                onClick={() => handleTemplateSelect(key)}
                className={clsx(
                  'p-3 text-left rounded-lg border transition-all',
                  selectedTemplate === key
                    ? 'bg-sardis-500/10 border-sardis-500/50'
                    : 'bg-dark-200 border-dark-100 hover:border-sardis-500/30'
                )}
              >
                <div className="font-medium text-white text-sm">{template.name}</div>
                <div className="text-xs text-gray-400 mt-1">{template.description}</div>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  {template.per_tx && <span>{template.per_tx}/tx</span>}
                  {template.monthly && <span>{template.monthly}/mo</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="bg-dark-300 border border-dark-100 rounded-lg p-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Policy Description
        </label>
        <textarea
          value={naturalLanguage}
          onChange={(e) => setNaturalLanguage(e.target.value)}
          placeholder="Example: Max $500/day on AWS and OpenAI, block gambling"
          rows={4}
          className="w-full bg-dark-200 border border-dark-100 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500"
        />

        <div className="mt-4 flex gap-3">
          <button
            onClick={handleParse}
            disabled={loading || !naturalLanguage.trim()}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
              loading || !naturalLanguage.trim()
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-sardis-500 text-dark-400 hover:bg-sardis-400'
            )}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-dark-400 border-t-transparent" />
                Parsing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Parse Policy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-red-400 font-medium">Error</div>
            <div className="text-red-300 text-sm mt-1">{error}</div>
          </div>
        </div>
      )}

      {/* Parsed Policy Display */}
      {parsedPolicy && (
        <div className="space-y-4">
          {/* Warnings */}
          {parsedPolicy.warnings && parsedPolicy.warnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-yellow-400 font-medium mb-2">Warnings</div>
                  <ul className="space-y-1">
                    {parsedPolicy.warnings.map((warning, idx) => (
                      <li key={idx} className="text-yellow-300 text-sm">
                        • {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Parsed Rules */}
          <div className="bg-dark-300 border border-dark-100 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Check className="w-5 h-5 text-green-400" />
              Parsed Policy Rules
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Spending Limits */}
              {parsedPolicy.spending_limits && parsedPolicy.spending_limits.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                    <DollarSign className="w-4 h-4 text-sardis-400" />
                    Spending Limits
                  </div>
                  {parsedPolicy.spending_limits.map((limit, idx) => (
                    <div
                      key={idx}
                      className="bg-dark-200 border border-dark-100 rounded px-3 py-2"
                    >
                      <div className="text-white text-sm font-medium">
                        ${limit.max_amount.toLocaleString()} / {limit.period}
                      </div>
                      <div className="text-gray-400 text-xs mt-1">
                        Vendor: {limit.vendor_pattern}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Global Limits */}
              {(parsedPolicy.global_daily_limit || parsedPolicy.global_monthly_limit) && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                    <Clock className="w-4 h-4 text-blue-400" />
                    Global Limits
                  </div>
                  {parsedPolicy.global_daily_limit && (
                    <div className="bg-dark-200 border border-dark-100 rounded px-3 py-2">
                      <div className="text-white text-sm font-medium">
                        ${parsedPolicy.global_daily_limit.toLocaleString()} / day
                      </div>
                      <div className="text-gray-400 text-xs mt-1">All vendors combined</div>
                    </div>
                  )}
                  {parsedPolicy.global_monthly_limit && (
                    <div className="bg-dark-200 border border-dark-100 rounded px-3 py-2">
                      <div className="text-white text-sm font-medium">
                        ${parsedPolicy.global_monthly_limit.toLocaleString()} / month
                      </div>
                      <div className="text-gray-400 text-xs mt-1">All vendors combined</div>
                    </div>
                  )}
                </div>
              )}

              {/* Blocked Categories */}
              {parsedPolicy.category_restrictions?.blocked_categories &&
                parsedPolicy.category_restrictions.blocked_categories.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                      <Ban className="w-4 h-4 text-red-400" />
                      Blocked Categories
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {parsedPolicy.category_restrictions.blocked_categories.map(
                        (category, idx) => (
                          <div
                            key={idx}
                            className="bg-red-500/10 border border-red-500/30 rounded px-3 py-1 text-red-300 text-xs font-medium flex items-center gap-1"
                          >
                            <X className="w-3 h-3" />
                            {category}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

              {/* Approval Threshold */}
              {parsedPolicy.requires_approval_above && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                    <Shield className="w-4 h-4 text-purple-400" />
                    Approval Required
                  </div>
                  <div className="bg-dark-200 border border-dark-100 rounded px-3 py-2">
                    <div className="text-white text-sm font-medium">
                      Above ${parsedPolicy.requires_approval_above.toLocaleString()}
                    </div>
                    <div className="text-gray-400 text-xs mt-1">
                      Transactions require manual approval
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-3">
              {agentId && (
                <>
                  <button
                    onClick={handleTestPolicy}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-dark-200 border border-dark-100 text-white rounded-lg hover:bg-dark-100 transition-all"
                  >
                    <Info className="w-4 h-4" />
                    Test Policy
                  </button>
                  <button
                    onClick={handleCreatePolicy}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-400 transition-all"
                  >
                    <Check className="w-4 h-4" />
                    Create Policy
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
              <div className="text-blue-400 font-medium mb-2">Preview</div>
              <div className="text-blue-300 text-sm whitespace-pre-line">
                {testResult.reason}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
