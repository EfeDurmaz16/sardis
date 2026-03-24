import { useState } from "react";
import type { Transaction } from "./types";

interface TransactionListProps {
  transactions: Transaction[];
  isDark: boolean;
}

export function TransactionList({ transactions, isDark }: TransactionListProps) {
  if (transactions.length === 0) {
    return (
      <div style={{ fontSize: 13, opacity: 0.5, textAlign: "center", padding: 8 }}>
        No transactions yet
      </div>
    );
  }

  const borderColor = isDark ? "#374151" : "#e5e7eb";

  const headerStyle: React.CSSProperties = {
    fontSize: 11,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    opacity: 0.6,
    padding: "4px 0",
  };

  return (
    <div style={{ flex: "0 1 auto", overflow: "auto", maxHeight: 160 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${borderColor}` }}>
            <th style={{ ...headerStyle, textAlign: "left" }}>Date</th>
            <th style={{ ...headerStyle, textAlign: "left" }}>Recipient</th>
            <th style={{ ...headerStyle, textAlign: "right" }}>Amount</th>
            <th style={{ ...headerStyle, textAlign: "right" }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <TransactionRow key={tx.id} tx={tx} isDark={isDark} borderColor={borderColor} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TransactionRow({
  tx,
  isDark,
  borderColor,
}: {
  tx: Transaction;
  isDark: boolean;
  borderColor: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const cellStyle: React.CSSProperties = { padding: "6px 0" };

  const statusColors: Record<string, { bg: string; text: string }> = {
    completed: { bg: isDark ? "#064e3b" : "#dcfce7", text: isDark ? "#6ee7b7" : "#166534" },
    pending: { bg: isDark ? "#422006" : "#fef9c3", text: isDark ? "#fbbf24" : "#854d0e" },
    blocked: { bg: isDark ? "#450a0a" : "#fee2e2", text: isDark ? "#fca5a5" : "#991b1b" },
  };

  const statusStyle = statusColors[tx.status] ?? statusColors.pending;
  const isBlocked = tx.status === "blocked" && tx.explanation;

  return (
    <>
      <tr
        style={{
          borderBottom: `1px solid ${borderColor}`,
          cursor: isBlocked ? "pointer" : "default",
        }}
        onClick={() => isBlocked && setExpanded(!expanded)}
      >
        <td style={cellStyle}>{tx.date}</td>
        <td style={cellStyle}>{tx.recipient}</td>
        <td style={{ ...cellStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
          ${tx.amount.toFixed(2)}
        </td>
        <td style={{ ...cellStyle, textAlign: "right" }}>
          <span
            data-testid={`status-${tx.status}`}
            style={{
              display: "inline-block",
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 9999,
              backgroundColor: statusStyle.bg,
              color: statusStyle.text,
            }}
          >
            {tx.status}
          </span>
        </td>
      </tr>
      {isBlocked && expanded && tx.explanation && (
        <tr>
          <td
            colSpan={4}
            style={{
              padding: "8px 0 8px 16px",
              borderBottom: `1px solid ${borderColor}`,
              fontSize: 12,
            }}
          >
            <PolicyExplanation explanation={tx.explanation} isDark={isDark} />
          </td>
        </tr>
      )}
    </>
  );
}

function PolicyExplanation({
  explanation,
  isDark,
}: {
  explanation: { checks_failed: string[]; suggested_action: string };
  isDark: boolean;
}) {
  const labelColor = isDark ? "#9ca3af" : "#6b7280";

  return (
    <div
      data-testid="policy-explanation"
      style={{
        overflow: "hidden",
        transition: "max-height 0.2s ease, opacity 0.2s ease",
        maxHeight: 200,
        opacity: 1,
      }}
    >
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontWeight: 600, color: labelColor }}>Checks failed:</span>
        <ul style={{ margin: "2px 0 0 16px", padding: 0 }}>
          {explanation.checks_failed.map((check, i) => (
            <li key={i} style={{ color: isDark ? "#fca5a5" : "#991b1b" }}>
              {check}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <span style={{ fontWeight: 600, color: labelColor }}>Suggested action: </span>
        <span>{explanation.suggested_action}</span>
      </div>
    </div>
  );
}
