/**
 * API Keys Management Page
 *
 * Features:
 * - List all API keys with prefix, scopes, status, dates
 * - Create new key modal with name, scopes, expiration
 * - Show full key once on creation with copy button
 * - Revoke key with confirmation dialog
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertTriangle,
  AlertCircle,
  X,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

// ── Types ──────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  scopes: string[];
  rate_limit: number | null;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

interface ApiKeyListResponse {
  keys: ApiKey[];
}

interface CreateKeyResponse {
  key_id: string;
  api_key: string;
  key_prefix: string;
  name: string;
  scopes: string[];
}

type ScopeOption = 'read' | 'write' | 'admin';
type ExpirationOption = '30' | '90' | '365' | 'never';

const SCOPE_OPTIONS: { value: ScopeOption; label: string; description: string }[] = [
  { value: 'read', label: 'Read', description: 'Read-only access to all resources' },
  { value: 'write', label: 'Write', description: 'Create and update resources' },
  { value: 'admin', label: 'Admin', description: 'Full access including deletion' },
];

const EXPIRATION_OPTIONS: { value: ExpirationOption; label: string }[] = [
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
  { value: '365', label: '1 year' },
  { value: 'never', label: 'Never' },
];

// ── Helpers ────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function keyStatus(key: ApiKey): 'active' | 'revoked' | 'expired' {
  if (!key.is_active) return 'revoked';
  if (key.expires_at && new Date(key.expires_at) < new Date()) return 'expired';
  return 'active';
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: 'active' | 'revoked' | 'expired' }) {
  const styles: Record<string, string> = {
    active: 'bg-green-500/20 text-green-300 border border-green-500/30',
    revoked: 'bg-red-500/20 text-red-300 border border-red-500/30',
    expired: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  };
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${styles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function ScopeBadge({ scope }: { scope: string }) {
  const styles: Record<string, string> = {
    read: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
    write: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
    admin: 'bg-red-500/20 text-red-300 border border-red-500/30',
  };
  const cls = styles[scope] ?? 'bg-gray-500/20 text-gray-300 border border-gray-500/30';
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{scope}</span>
  );
}

// ── Copy Button ────────────────────────────────────────────────────────────

function CopyButton({ text, className = '' }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-dark-200 text-gray-300 hover:bg-dark-100 hover:text-white transition-colors border border-dark-100 ${className}`}
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

// ── Create Key Modal ───────────────────────────────────────────────────────

interface CreateKeyModalProps {
  token: string | null;
  onClose: () => void;
  onCreated: () => void;
}

function CreateKeyModal({ token, onClose, onCreated }: CreateKeyModalProps) {
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<ScopeOption[]>(['read']);
  const [expiration, setExpiration] = useState<ExpirationOption>('never');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  function toggleScope(scope: ScopeOption) {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name is required.');
      return;
    }
    if (scopes.length === 0) {
      setError('Select at least one scope.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const body: Record<string, unknown> = {
        name: name.trim(),
        scopes,
      };
      if (expiration !== 'never') {
        body.expires_in_days = parseInt(expiration, 10);
      }

      const res = await fetch(`${API_BASE}/api/v2/auth/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError((data as { detail?: string }).detail ?? `Request failed (${res.status})`);
        return;
      }

      const data: CreateKeyResponse = await res.json();
      setCreatedKey(data.api_key);
      onCreated();
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  // If the key was just created, show the reveal screen
  if (createdKey) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
        <div className="card w-full max-w-lg p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">API Key Created</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="card p-4 border-amber-500/40 bg-amber-500/5 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <p className="text-sm text-amber-300 font-medium">
              Save this key now — you won't be able to see it again after closing this dialog.
            </p>
          </div>

          <div>
            <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Your API Key</p>
            <div className="flex items-stretch gap-2">
              <code className="flex-1 font-mono text-sm text-sardis-400 bg-dark-200 border border-dark-100 px-3 py-2 rounded overflow-x-auto whitespace-nowrap">
                {createdKey}
              </code>
              <CopyButton text={createdKey} />
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors rounded"
          >
            I've saved the key — Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="card w-full max-w-md p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Create API Key</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production agent key"
              className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 rounded focus:outline-none focus:border-sardis-500/60 placeholder:text-gray-600"
              autoFocus
            />
          </div>

          {/* Scopes */}
          <div>
            <p className="text-sm font-medium text-gray-300 mb-2">Scopes</p>
            <div className="space-y-2">
              {SCOPE_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-start gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={scopes.includes(opt.value)}
                    onChange={() => toggleScope(opt.value)}
                    className="mt-0.5 accent-sardis-500"
                  />
                  <span>
                    <span className="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
                      {opt.label}
                    </span>
                    <span className="block text-xs text-gray-500">{opt.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Expiration */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Expiration</label>
            <select
              value={expiration}
              onChange={(e) => setExpiration(e.target.value as ExpirationOption)}
              className="w-full bg-dark-200 border border-dark-100 text-white text-sm px-3 py-2 rounded focus:outline-none focus:border-sardis-500/60"
            >
              {EXPIRATION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 text-sm font-medium bg-dark-200 text-gray-300 hover:bg-dark-100 hover:text-white transition-colors border border-dark-100 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {submitting ? 'Creating...' : 'Create Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Revoke Confirmation Dialog ─────────────────────────────────────────────

interface RevokeDialogProps {
  keyName: string;
  onConfirm: () => void;
  onCancel: () => void;
  revoking: boolean;
}

function RevokeDialog({ keyName, onConfirm, onCancel, revoking }: RevokeDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="card w-full max-w-sm p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center shrink-0">
            <Trash2 className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Revoke API Key</h2>
            <p className="text-sm text-gray-400 mt-0.5">This cannot be undone.</p>
          </div>
        </div>

        <p className="text-sm text-gray-300">
          Are you sure you want to revoke{' '}
          <span className="font-semibold text-white">{keyName}</span>? Any services using this
          key will immediately lose access.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={revoking}
            className="flex-1 py-2 text-sm font-medium bg-dark-200 text-gray-300 hover:bg-dark-100 hover:text-white transition-colors border border-dark-100 rounded disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={revoking}
            className="flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium bg-red-600 text-white hover:bg-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded"
          >
            {revoking && <Loader2 className="w-4 h-4 animate-spin" />}
            {revoking ? 'Revoking...' : 'Revoke Key'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function APIKeysPage() {
  const { token } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<ApiKey | null>(null);
  const [revoking, setRevoking] = useState(false);

  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/auth/api-keys`, { headers: authHeaders });
      if (!res.ok) {
        setFetchError(`Failed to load API keys (${res.status})`);
        return;
      }
      const data: ApiKeyListResponse = await res.json();
      setKeys(data.keys ?? []);
    } catch {
      setFetchError('Network error. Could not load API keys.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  async function handleRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    try {
      const res = await fetch(`${API_BASE}/api/v2/api-keys/${revokeTarget.id}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (res.ok) {
        setRevokeTarget(null);
        await fetchKeys();
      }
    } catch {
      // silent — user can retry
    } finally {
      setRevoking(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">API Keys</h1>
          <p className="text-gray-400 mt-1">
            Manage programmatic access keys for your agents and integrations
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Error state */}
      {fetchError && (
        <div className="card p-4 border-red-500/30 bg-red-500/5 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-300">{fetchError}</p>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sardis-500" />
        </div>
      ) : keys.length === 0 ? (
        /* Empty state */
        <div className="card p-12 flex flex-col items-center justify-center text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-dark-200 flex items-center justify-center">
            <Key className="w-6 h-6 text-gray-500" />
          </div>
          <p className="text-white font-medium">No API keys yet</p>
          <p className="text-sm text-gray-500">Create one to get started.</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-2 flex items-center gap-2 px-4 py-2 text-sm font-medium bg-sardis-500 text-dark-400 hover:bg-sardis-400 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create API Key
          </button>
        </div>
      ) : (
        /* Keys table */
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-100">
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Name
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Key Prefix
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Scopes
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Created
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Last Used
                  </th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider px-5 py-3">
                    Status
                  </th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-100">
                {keys.map((key) => {
                  const status = keyStatus(key);
                  return (
                    <tr key={key.id} className="hover:bg-dark-200/40 transition-colors">
                      <td className="px-5 py-3.5 text-white font-medium">{key.name}</td>
                      <td className="px-5 py-3.5">
                        <code className="font-mono text-sardis-400 text-xs bg-dark-200 px-2 py-0.5 rounded">
                          {key.key_prefix}...
                        </code>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {key.scopes.length > 0 ? (
                            key.scopes.map((s) => <ScopeBadge key={s} scope={s} />)
                          ) : (
                            <span className="text-gray-600 text-xs">—</span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-gray-400">{formatDate(key.created_at)}</td>
                      <td className="px-5 py-3.5 text-gray-400">{formatDate(key.last_used_at)}</td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={status} />
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {status === 'active' && (
                          <button
                            onClick={() => setRevokeTarget(key)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-400 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 transition-colors ml-auto"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreateModal && (
        <CreateKeyModal
          token={token}
          onClose={() => setShowCreateModal(false)}
          onCreated={fetchKeys}
        />
      )}

      {revokeTarget && (
        <RevokeDialog
          keyName={revokeTarget.name}
          onConfirm={handleRevoke}
          onCancel={() => setRevokeTarget(null)}
          revoking={revoking}
        />
      )}
    </div>
  );
}
