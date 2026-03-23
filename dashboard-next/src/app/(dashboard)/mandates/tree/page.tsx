"use client";

import { useState, useEffect, useCallback } from "react";
import {
  GitBranch,
  ChevronRight,
  ChevronDown,
  Search,
  Loader2,
  Shield,
  User,
  DollarSign,
  ArrowRight,
  AlertCircle,
} from "lucide-react";
import clsx from "clsx";
import { getAuthHeaders } from "@/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MandateTreeNode {
  id: string;
  agent_id: string | null;
  purpose_scope: string | null;
  amount_total: string | null;
  spent_total: string;
  status: string;
  currency: string;
  delegation_depth: number;
  parent_mandate_id: string | null;
  expires_at: string | null;
  created_at: string;
  children: MandateTreeNode[];
}

// ---------------------------------------------------------------------------
// Status badge (matches mandates/page.tsx palette)
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> =
  {
    active: {
      bg: "bg-green-500/10",
      text: "text-green-500",
      dot: "bg-green-500",
    },
    suspended: {
      bg: "bg-yellow-500/10",
      text: "text-yellow-500",
      dot: "bg-yellow-500",
    },
    revoked: { bg: "bg-red-500/10", text: "text-red-500", dot: "bg-red-500" },
    expired: {
      bg: "bg-gray-500/10",
      text: "text-gray-500",
      dot: "bg-gray-500",
    },
    draft: {
      bg: "bg-gray-500/10",
      text: "text-gray-400",
      dot: "bg-gray-400",
    },
    consumed: {
      bg: "bg-blue-500/10",
      text: "text-blue-400",
      dot: "bg-blue-400",
    },
  };

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.draft;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium capitalize",
        c.bg,
        c.text,
      )}
    >
      <span className={clsx("w-1.5 h-1.5 rounded-full", c.dot)} />
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Budget bar (compact)
// ---------------------------------------------------------------------------

function BudgetBar({
  spent,
  total,
}: {
  spent: string;
  total: string | null;
}) {
  if (!total)
    return <span className="text-xs text-gray-500 italic">No limit</span>;
  const s = parseFloat(spent);
  const t = parseFloat(total);
  const pct = t > 0 ? Math.min(100, (s / t) * 100) : 0;
  return (
    <div className="flex items-center gap-2 min-w-[140px]">
      <div className="flex-1 h-1.5 rounded-full bg-dark-100">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            background:
              pct > 80 ? "#EF4444" : pct > 60 ? "#F59E0B" : "#22C55E",
          }}
        />
      </div>
      <span className="text-xs text-gray-400 whitespace-nowrap">
        ${s.toFixed(2)} / ${t.toFixed(2)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Depth path indicator
// ---------------------------------------------------------------------------

function DepthPath({ depth }: { depth: number }) {
  if (depth === 0) return <span className="text-xs text-gray-500">Root</span>;
  return (
    <span className="text-xs text-gray-500 flex items-center gap-0.5">
      {Array.from({ length: depth }).map((_, i) => (
        <span key={i} className="flex items-center gap-0.5">
          {i > 0 && <ArrowRight size={8} className="text-gray-600" />}
          <span className="w-4 h-4 rounded bg-dark-100 flex items-center justify-center text-[9px] text-gray-400 font-mono">
            L{i + 1}
          </span>
        </span>
      ))}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Recursive tree node component
// ---------------------------------------------------------------------------

function TreeNode({
  node,
  depth,
}: {
  node: MandateTreeNode;
  depth: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div>
      {/* The node row */}
      <div
        className={clsx(
          "group flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer",
          "border-dark-100 bg-dark-200 hover:border-dark-50",
        )}
        style={{ marginLeft: depth * 28 }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand / collapse toggle */}
        <button
          className={clsx(
            "mt-0.5 w-5 h-5 flex items-center justify-center rounded text-gray-500 hover:text-white transition-colors shrink-0",
            !hasChildren && "invisible",
          )}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(!expanded);
          }}
        >
          {expanded ? (
            <ChevronDown size={14} />
          ) : (
            <ChevronRight size={14} />
          )}
        </button>

        {/* Connector line for children */}
        {depth > 0 && (
          <div className="w-px h-full bg-dark-100 absolute" style={{ left: depth * 28 - 14 }} />
        )}

        {/* Body */}
        <div className="flex-1 min-w-0 space-y-1.5">
          {/* Top row: ID + status */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-sm text-white truncate max-w-[200px]">
              {node.id}
            </span>
            <StatusBadge status={node.status} />
            <DepthPath depth={node.delegation_depth} />
          </div>

          {/* Details row */}
          <div className="flex items-center gap-4 flex-wrap text-xs">
            {node.agent_id && (
              <span className="flex items-center gap-1 text-gray-400">
                <User size={11} />
                <span className="font-mono truncate max-w-[120px]">
                  {node.agent_id}
                </span>
              </span>
            )}
            {node.purpose_scope && (
              <span className="flex items-center gap-1 text-gray-400">
                <Shield size={11} />
                {node.purpose_scope}
              </span>
            )}
            <span className="flex items-center gap-1 text-gray-400">
              <DollarSign size={11} />
              <BudgetBar spent={node.spent_total} total={node.amount_total} />
            </span>
          </div>

          {/* Meta row */}
          <div className="flex items-center gap-4 text-[11px] text-gray-600">
            {node.expires_at && (
              <span>
                Expires{" "}
                {new Date(node.expires_at).toLocaleDateString()}
              </span>
            )}
            {hasChildren && (
              <span>
                {node.children.length} sub-mandate
                {node.children.length > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Delegate button */}
        <a
          href={`/mandates?delegate=${node.id}`}
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-md border border-dark-100 text-gray-400 hover:text-sardis-400 hover:border-sardis-500/40 transition-colors opacity-0 group-hover:opacity-100"
        >
          Delegate
        </a>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="mt-1.5 space-y-1.5 relative">
          {/* Vertical connector */}
          <div
            className="absolute top-0 bottom-0 w-px bg-dark-100"
            style={{ left: (depth + 1) * 28 - 14 }}
          />
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function MandateTreePage() {
  const [mandateId, setMandateId] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [tree, setTree] = useState<MandateTreeNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch tree for a given mandate ID
  const fetchTree = useCallback(async (id: string) => {
    if (!id.trim()) return;
    setLoading(true);
    setError(null);
    setTree(null);
    try {
      const res = await fetch(`/api/v2/mandates/${encodeURIComponent(id)}/tree`, {
        headers: {
          ...getAuthHeaders(),
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(
          body?.detail ?? body?.message ?? `Request failed (${res.status})`,
        );
      }
      const data: MandateTreeNode = await res.json();
      setTree(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch mandate tree");
    } finally {
      setLoading(false);
    }
  }, []);

  // Accept mandate ID from URL search params (?id=...)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const urlId = params.get("id");
    if (urlId) {
      setMandateId(urlId);
      setInputValue(urlId);
      fetchTree(urlId);
    }
  }, [fetchTree]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    setMandateId(trimmed);
    // Update URL without full navigation
    const url = new URL(window.location.href);
    url.searchParams.set("id", trimmed);
    window.history.replaceState({}, "", url.toString());
    fetchTree(trimmed);
  };

  // Count all nodes in tree recursively
  const countNodes = (node: MandateTreeNode): number => {
    return 1 + (node.children ?? []).reduce((sum, c) => sum + countNodes(c), 0);
  };

  // Find max depth in tree
  const maxDepth = (node: MandateTreeNode): number => {
    if (!node.children || node.children.length === 0) return node.delegation_depth;
    return Math.max(...node.children.map(maxDepth));
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">
          Mandate Tree
        </h1>
        <p className="text-gray-400 mt-1">
          Visualize parent-to-child delegation hierarchy
        </p>
      </div>

      {/* Mandate ID search / selector */}
      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <div className="relative flex-1 max-w-lg">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Enter mandate ID (e.g. mnd_abc123)..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 text-sm focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !inputValue.trim()}
          className="px-5 py-2.5 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50 text-sm"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            "Load Tree"
          )}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <AlertCircle size={18} className="text-red-400 shrink-0" />
          <div>
            <p className="text-red-400 text-sm font-medium">
              Failed to load mandate tree
            </p>
            <p className="text-red-400/70 text-xs mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="card p-4 animate-pulse"
              style={{ marginLeft: (i - 1) * 28 }}
            >
              <div className="h-4 bg-dark-100 rounded w-1/3 mb-2" />
              <div className="h-3 bg-dark-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {/* Tree content */}
      {tree && !loading && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="flex items-center gap-6 text-sm text-gray-400">
            <span className="flex items-center gap-1.5">
              <GitBranch size={14} />
              {countNodes(tree)} node{countNodes(tree) !== 1 ? "s" : ""} in tree
            </span>
            <span>Max depth: {maxDepth(tree)}</span>
            <span>
              Root: <span className="font-mono text-white">{tree.id}</span>
            </span>
          </div>

          {/* Tree visualization */}
          <div className="space-y-1.5 relative">
            <TreeNode node={tree} depth={0} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!tree && !loading && !error && mandateId && (
        <div className="card p-12 text-center">
          <GitBranch className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            No tree data
          </h3>
          <p className="text-gray-400">
            The mandate tree could not be loaded. Verify the ID and try again.
          </p>
        </div>
      )}

      {/* Initial state - no ID entered yet */}
      {!tree && !loading && !error && !mandateId && (
        <div className="card p-12 text-center">
          <GitBranch className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">
            View Delegation Tree
          </h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Enter a mandate ID above to visualize its full delegation hierarchy.
            Each node shows the mandate status, agent, budget, and purpose scope.
          </p>
        </div>
      )}
    </div>
  );
}
