import { useState, useCallback } from 'react'
import {
  CheckCircle,
  Copy,
  Download,
  FileJs,
  Package,
  ShieldCheck,
  ShieldWarning,
  SpinnerGap,
  WarningCircle,
  X,
} from '@phosphor-icons/react'
import clsx from 'clsx'
import { evidenceApi } from '../api/client'

/* ─── Types ─── */

interface EvidenceSection {
  status: 'available' | 'not_available'
  data?: Record<string, unknown> | null
  reason?: string | null
}

interface IntegrityMetadata {
  algorithm: string
  content_hash: string
  signature: string
  signed_at: string
  signer: string
  version: string
}

interface EvidenceBundle {
  tx_id: string
  exported_at: string
  version: string
  sections: Record<string, EvidenceSection>
  integrity?: IntegrityMetadata | null
}

interface EvidenceExportModalProps {
  txId: string
  onClose: () => void
}

/* ─── Section labels ─── */

const SECTION_LABELS: Record<string, string> = {
  transaction: 'Transaction Details',
  policy_decision: 'Policy Decision',
  approval: 'Approval State',
  execution_receipt: 'Execution Receipt',
  ledger_artifacts: 'Ledger Artifacts',
  side_effects: 'Side Effects',
  exception_state: 'Exception State',
  webhook_logs: 'Webhook Delivery Logs',
}

/* ─── Section row ─── */

function SectionRow({
  name,
  section,
}: {
  name: string
  section: EvidenceSection
}) {
  const label = SECTION_LABELS[name] ?? name
  const available = section.status === 'available'

  return (
    <div className="flex items-start gap-3 px-4 py-3 bg-dark-200 border border-dark-100">
      <div
        className={clsx(
          'mt-0.5 w-4 h-4 flex-shrink-0 flex items-center justify-center',
          available ? 'text-green-400' : 'text-gray-600',
        )}
      >
        {available ? (
          <CheckCircle className="w-4 h-4" />
        ) : (
          <div className="w-2 h-2 bg-gray-600" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p
          className={clsx(
            'text-sm font-medium',
            available ? 'text-white' : 'text-gray-500',
          )}
        >
          {label}
        </p>
        {!available && section.reason && (
          <p className="text-xs text-gray-600 mt-0.5">{section.reason}</p>
        )}
      </div>
      <span
        className={clsx(
          'text-xs px-2 py-0.5 flex-shrink-0 font-mono',
          available
            ? 'bg-green-500/10 text-green-400'
            : 'bg-dark-300 text-gray-600',
        )}
      >
        {available ? 'available' : 'not available'}
      </span>
    </div>
  )
}

/* ─── Main modal ─── */

export default function EvidenceExportModal({
  txId,
  onClose,
}: EvidenceExportModalProps) {
  const [bundle, setBundle] = useState<EvidenceBundle | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const [verifying, setVerifying] = useState(false)
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string; verified_at: string } | null>(null)
  const [verifyError, setVerifyError] = useState<string | null>(null)

  const handleExport = useCallback(async () => {
    setLoading(true)
    setError(null)
    setVerifyResult(null)
    setVerifyError(null)
    try {
      const result = await evidenceApi.exportBundle(txId)
      setBundle(result as unknown as EvidenceBundle)
    } catch (err) {
      setError((err as Error).message ?? 'Failed to export evidence bundle')
    } finally {
      setLoading(false)
    }
  }, [txId])

  const handleVerify = useCallback(async () => {
    if (!bundle?.integrity) return
    setVerifying(true)
    setVerifyError(null)
    setVerifyResult(null)
    try {
      const result = await evidenceApi.verifyBundle({
        tx_id: bundle.tx_id,
        content_hash: bundle.integrity.content_hash,
        signature: bundle.integrity.signature,
      })
      setVerifyResult(result as unknown as { valid: boolean; message: string; verified_at: string })
    } catch (err) {
      setVerifyError((err as Error).message ?? 'Verification request failed')
    } finally {
      setVerifying(false)
    }
  }, [bundle])

  const handleCopy = useCallback(() => {
    if (!bundle) return
    const json = JSON.stringify(bundle, null, 2)
    navigator.clipboard.writeText(json).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }, [bundle])

  const downloadUrl = evidenceApi.downloadBundleUrl(txId)

  const sectionEntries = bundle
    ? Object.entries(bundle.sections)
    : []

  const availableCount = sectionEntries.filter(
    ([, s]) => s.status === 'available',
  ).length

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-full max-w-lg bg-dark-400 border border-dark-100 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-dark-100 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-sardis-500/10 border border-sardis-500/20">
              <Package className="w-4 h-4 text-sardis-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">
                Export Evidence Bundle
              </h2>
              <p className="text-xs text-gray-500 font-mono mt-0.5 truncate max-w-xs">
                {txId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          {/* Intro */}
          {!bundle && !loading && !error && (
            <div className="text-center py-6 space-y-3">
              <FileJs className="w-10 h-10 text-gray-600 mx-auto" />
              <p className="text-sm text-gray-400 max-w-xs mx-auto leading-relaxed">
                Export a JSON bundle with all available evidence artifacts:
                transaction details, policy decision, approval state, execution
                receipt, ledger artifacts, side effects, exception state, and
                webhook logs.
              </p>
              <button
                onClick={handleExport}
                className="mt-2 px-5 py-2.5 bg-sardis-500 hover:bg-sardis-600 text-white text-sm font-medium flex items-center gap-2 mx-auto transition-colors"
              >
                <Package className="w-4 h-4" />
                Generate Bundle
              </button>
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center justify-center py-10 gap-3 text-gray-400">
              <SpinnerGap className="w-5 h-5 animate-spin text-sardis-400" />
              <span className="text-sm">Collecting evidence artifacts…</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/25">
              <WarningCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-400">
                  Export failed
                </p>
                <p className="text-xs text-red-400/70 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Bundle preview */}
          {bundle && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="flex items-center gap-3 px-4 py-3 bg-dark-300 border border-dark-100">
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium">
                    Bundle ready
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {availableCount} of {sectionEntries.length} sections
                    available &middot; v{bundle.version} &middot;{' '}
                    {new Date(bundle.exported_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Section checklist */}
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                  Sections
                </p>
                <div className="space-y-px">
                  {sectionEntries.map(([name, section]) => (
                    <SectionRow key={name} name={name} section={section} />
                  ))}
                </div>
              </div>

              {/* Integrity */}
              {bundle.integrity && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">
                    Integrity
                  </p>
                  <div className="px-4 py-3 bg-dark-200 border border-dark-100 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Algorithm</span>
                      <span className="text-xs font-mono text-gray-300">{bundle.integrity.algorithm}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Content hash</span>
                      <span className="text-xs font-mono text-gray-300 truncate max-w-[180px]" title={bundle.integrity.content_hash}>
                        {bundle.integrity.content_hash.slice(0, 16)}…
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Signature</span>
                      <span className="text-xs font-mono text-gray-300 truncate max-w-[180px]" title={bundle.integrity.signature}>
                        {bundle.integrity.signature.slice(0, 16)}…
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Signed at</span>
                      <span className="text-xs font-mono text-gray-300">
                        {new Date(bundle.integrity.signed_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">Signer</span>
                      <span className="text-xs font-mono text-gray-300">{bundle.integrity.signer}</span>
                    </div>

                    {/* Verify button */}
                    <div className="pt-1">
                      <button
                        onClick={handleVerify}
                        disabled={verifying}
                        className="flex items-center gap-2 px-3 py-1.5 bg-dark-300 border border-dark-100 hover:border-sardis-500/40 text-gray-300 hover:text-white text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {verifying ? (
                          <SpinnerGap className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <ShieldCheck className="w-3.5 h-3.5" />
                        )}
                        {verifying ? 'Verifying…' : 'Verify Integrity'}
                      </button>
                    </div>

                    {/* Verify result */}
                    {verifyResult && (
                      <div className={clsx(
                        'flex items-start gap-2 px-3 py-2 border',
                        verifyResult.valid
                          ? 'bg-green-500/10 border-green-500/25'
                          : 'bg-red-500/10 border-red-500/25',
                      )}>
                        {verifyResult.valid ? (
                          <ShieldCheck className="w-3.5 h-3.5 text-green-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <ShieldWarning className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <p className={clsx(
                            'text-xs font-medium',
                            verifyResult.valid ? 'text-green-400' : 'text-red-400',
                          )}>
                            {verifyResult.message}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {new Date(verifyResult.verified_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Verify error */}
                    {verifyError && (
                      <div className="flex items-start gap-2 px-3 py-2 bg-red-500/10 border border-red-500/25">
                        <WarningCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-red-400">{verifyError}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer actions */}
        {bundle && (
          <div className="flex items-center gap-2 px-5 py-4 border-t border-dark-100 flex-shrink-0">
            <a
              href={downloadUrl}
              download={`sardis-evidence-${txId}.json`}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-sardis-500 hover:bg-sardis-600 text-white text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              Download JSON
            </a>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2.5 bg-dark-200 border border-dark-100 hover:border-sardis-500/40 text-gray-300 hover:text-white text-sm transition-colors"
            >
              {copied ? (
                <>
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  <span className="text-green-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy JSON
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
