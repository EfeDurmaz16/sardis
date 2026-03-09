import { useState } from "react";

// ─── Outbound Data ────────────────────────────────────────────────────────────

const outboundData = {
  Transactions: {
    title: "Recent Transactions",
    columns: [
      { label: "", width: "24px" },
      { label: "Description", width: "200px" },
      { label: "Agent", width: "140px" },
      { label: "Token", width: "100px" },
      { label: "Amount", flex: true },
      { label: "Time", width: "60px", align: "right" },
    ],
    rows: [
      { color: "#4ADE80", description: "Invoice #4821: Vercel", agent: "procurement-agent", token: "USDC · Base", amount: "$249.00", time: "2m" },
      { color: "#E85D5D", description: "Transfer: Unknown Wallet", agent: "treasury-agent", token: "USDT · ETH", amount: "$8,400.00", time: "5m" },
      { color: "#4ADE80", description: "SaaS License: Linear", agent: "ops-agent", token: "USDC · Base", amount: "$120.00", time: "12m" },
      { color: "#E8A44A", description: "Payroll: Contractor #7", agent: "finance-agent", token: "EURC · Polygon", amount: "$3,200.00", time: "18m" },
      { color: "#4ADE80", description: "Cloud Hosting: Railway", agent: "devops-agent", token: "USDC · Arb", amount: "$67.50", time: "24m" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0 }}>
            <span style={{ fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)", display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
              {row.description}
            </span>
            <span style={{ fontSize: "11px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-muted)", display: "block" }}>
              {row.agent}
            </span>
          </span>
          <span style={{ width: "140px", flexShrink: 0 }} />
          <span style={{ width: "100px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.token}
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: "var(--landing-text-primary)" }}>
            {row.amount}
          </span>
          <span style={{ width: "60px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.time}
          </span>
        </div>
      );
    },
  },

  Agents: {
    title: "Active Agents",
    columns: [
      { label: "", width: "24px" },
      { label: "Agent", width: "200px" },
      { label: "Status", width: "120px" },
      { label: "Wallet", width: "160px" },
      { label: "Last Active", flex: true },
    ],
    rows: [
      { color: "#4ADE80", name: "procurement-agent", status: "active", statusColor: "#4ADE80", wallet: "0x4f2a…e81c", lastActive: "2m ago" },
      { color: "#4ADE80", name: "treasury-agent", status: "active", statusColor: "#4ADE80", wallet: "0x9b3d…a44f", lastActive: "5m ago" },
      { color: "#E8A44A", name: "ops-agent", status: "idle", statusColor: "#E8A44A", wallet: "0x1c7e…f903", lastActive: "18m ago" },
      { color: "#4ADE80", name: "finance-agent", status: "active", statusColor: "#4ADE80", wallet: "0x83a1…2b7d", lastActive: "22m ago" },
      { color: "#5B8DEF", name: "devops-agent", status: "syncing", statusColor: "#5B8DEF", wallet: "0x6d5c…c19a", lastActive: "31m ago" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0, fontSize: "13px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-primary)" }}>
            {row.name}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ width: "160px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-muted)" }}>
            {row.wallet}
          </span>
          <span style={{ flex: 1, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.lastActive}
          </span>
        </div>
      );
    },
  },

  Policies: {
    title: "Spending Policies",
    columns: [
      { label: "", width: "24px" },
      { label: "Policy", width: "220px" },
      { label: "Agent", width: "160px" },
      { label: "Status", width: "120px" },
      { label: "Limit", flex: true },
    ],
    rows: [
      { color: "#4ADE80", name: "Max $500/day SaaS", agent: "ops-agent", status: "active", statusColor: "#4ADE80", limit: "$500 / day" },
      { color: "#4ADE80", name: "Max $10k/tx Treasury", agent: "treasury-agent", status: "active", statusColor: "#4ADE80", limit: "$10,000 / tx" },
      { color: "#E8A44A", name: "Approved vendors only", agent: "procurement-agent", status: "warning", statusColor: "#E8A44A", limit: "Allowlist" },
      { color: "#4ADE80", name: "Payroll cap $5k", agent: "finance-agent", status: "active", statusColor: "#4ADE80", limit: "$5,000 / run" },
      { color: "#E85D5D", name: "No unverified wallets", agent: "all agents", status: "enforced", statusColor: "#E85D5D", limit: "Global" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "220px", flexShrink: 0, fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
            {row.name}
          </span>
          <span style={{ width: "160px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-muted)" }}>
            {row.agent}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.limit}
          </span>
        </div>
      );
    },
  },

  Wallets: {
    title: "Agent Wallets",
    columns: [
      { label: "", width: "24px" },
      { label: "Address", width: "160px" },
      { label: "Chain", width: "120px" },
      { label: "Balance", width: "140px" },
      { label: "Last Tx", flex: true },
    ],
    rows: [
      { color: "#4ADE80", address: "0x4f2a…e81c", chain: "Base", balance: "$2,840.00", lastTx: "2m ago" },
      { color: "#4ADE80", address: "0x9b3d…a44f", chain: "Ethereum", balance: "$41,200.00", lastTx: "5m ago" },
      { color: "#E8A44A", address: "0x1c7e…f903", chain: "Polygon", balance: "$980.50", lastTx: "18m ago" },
      { color: "#4ADE80", address: "0x83a1…2b7d", chain: "Arbitrum", balance: "$7,315.00", lastTx: "22m ago" },
      { color: "#5B8DEF", address: "0x6d5c…c19a", chain: "Optimism", balance: "$450.25", lastTx: "31m ago" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "160px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-primary)" }}>
            {row.address}
          </span>
          <span style={{ width: "120px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.chain}
          </span>
          <span style={{ width: "140px", flexShrink: 0, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: "var(--landing-text-primary)" }}>
            {row.balance}
          </span>
          <span style={{ flex: 1, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)" }}>
            {row.lastTx}
          </span>
        </div>
      );
    },
  },

  "Audit Log": {
    title: "Audit Log",
    columns: [
      { label: "", width: "24px" },
      { label: "Action", width: "200px" },
      { label: "Agent", width: "160px" },
      { label: "Result", width: "120px" },
      { label: "Timestamp", flex: true },
    ],
    rows: [
      { color: "#4ADE80", action: "Payment executed", agent: "procurement-agent", result: "approved", resultColor: "#4ADE80", timestamp: "09:14:22 UTC" },
      { color: "#E85D5D", action: "Policy blocked tx", agent: "treasury-agent", result: "denied", resultColor: "#E85D5D", timestamp: "09:11:05 UTC" },
      { color: "#4ADE80", action: "Wallet funded", agent: "finance-agent", result: "approved", resultColor: "#4ADE80", timestamp: "09:08:47 UTC" },
      { color: "#E8A44A", action: "AML flag raised", agent: "ops-agent", result: "review", resultColor: "#E8A44A", timestamp: "09:03:19 UTC" },
      { color: "#4ADE80", action: "Invoice settled", agent: "devops-agent", result: "approved", resultColor: "#4ADE80", timestamp: "08:56:33 UTC" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0, fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
            {row.action}
          </span>
          <span style={{ width: "160px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-muted)" }}>
            {row.agent}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.resultColor, background: `${row.resultColor}14` }}>
              {row.result}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-tertiary)" }}>
            {row.timestamp}
          </span>
        </div>
      );
    },
  },
};

// ─── Inbound Data ─────────────────────────────────────────────────────────────

const inboundData = {
  Transactions: {
    title: "All Transactions",
    columns: [
      { label: "", width: "24px" },
      { label: "Description", width: "200px" },
      { label: "Token", width: "100px" },
      { label: "Status", width: "120px" },
      { label: "Amount", flex: true },
      { label: "Time", width: "60px", align: "right" },
    ],
    rows: [
      { color: "#4ADE80", description: "Payment from Acme Corp", token: "USDC · Base", status: "confirmed", statusColor: "#4ADE80", amount: "+$3,200.00", time: "1m" },
      { color: "#5B8DEF", description: "x402 API fee: gpt-router", token: "USDC · Base", status: "verified", statusColor: "#5B8DEF", amount: "+$0.50", time: "4m" },
      { color: "#4ADE80", description: "Invoice #1099: Stripe", token: "USDC · Polygon", status: "confirmed", statusColor: "#4ADE80", amount: "+$1,200.00", time: "9m" },
      { color: "#E8A44A", description: "Transfer: 0x2c1a…d09f", token: "USDT · ETH", status: "screening", statusColor: "#E8A44A", amount: "+$22,000.00", time: "15m" },
      { color: "#4ADE80", description: "Deposit from OpenAI", token: "EURC · Base", status: "confirmed", statusColor: "#4ADE80", amount: "+$5,750.00", time: "27m" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0 }}>
            <span style={{ fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)", display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
              {row.description}
            </span>
          </span>
          <span style={{ width: "100px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.token}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: row.color }}>
            {row.amount}
          </span>
          <span style={{ width: "60px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.time}
          </span>
        </div>
      );
    },
  },

  Deposits: {
    title: "Deposits",
    columns: [
      { label: "", width: "24px" },
      { label: "Description", width: "200px" },
      { label: "Token", width: "100px" },
      { label: "Status", width: "120px" },
      { label: "Amount", flex: true },
      { label: "Time", width: "60px", align: "right" },
    ],
    rows: [
      { color: "#4ADE80", description: "Deposit from Helicone", token: "USDC · Base", status: "confirmed", statusColor: "#4ADE80", amount: "+$2,400.00", time: "3m" },
      { color: "#E8A44A", description: "Deposit: 0x8f3a…c21d", token: "USDT · ETH", status: "aml-screening", statusColor: "#E8A44A", amount: "+$15,000.00", time: "8m" },
      { color: "#4ADE80", description: "Invoice #1092: Acme", token: "USDC · Polygon", status: "confirmed", statusColor: "#4ADE80", amount: "+$890.00", time: "14m" },
      { color: "#5B8DEF", description: "x402: API access fee", token: "USDC · Base", status: "verified", statusColor: "#5B8DEF", amount: "+$0.50", time: "21m" },
      { color: "#4ADE80", description: "Deposit from OpenAI", token: "EURC · Base", status: "confirmed", statusColor: "#4ADE80", amount: "+$5,750.00", time: "30m" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0 }}>
            <span style={{ fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)", display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
              {row.description}
            </span>
          </span>
          <span style={{ width: "100px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.token}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: row.color }}>
            {row.amount}
          </span>
          <span style={{ width: "60px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.time}
          </span>
        </div>
      );
    },
  },

  "Payment Requests": {
    title: "Payment Requests",
    columns: [
      { label: "", width: "24px" },
      { label: "Requester", width: "180px" },
      { label: "Token", width: "120px" },
      { label: "Status", width: "120px" },
      { label: "Amount", flex: true },
      { label: "Age", width: "60px", align: "right" },
    ],
    rows: [
      { color: "#E8A44A", requester: "vendor-agent@acme", token: "USDC · Base", status: "pending", statusColor: "#E8A44A", amount: "$1,800.00", age: "4m" },
      { color: "#4ADE80", requester: "billing@stripe.com", token: "USDC · Polygon", status: "approved", statusColor: "#4ADE80", amount: "$560.00", age: "11m" },
      { color: "#E8A44A", requester: "ops-agent@openai", token: "EURC · Base", status: "pending", statusColor: "#E8A44A", amount: "$240.00", age: "19m" },
      { color: "#E85D5D", requester: "0x9f2b…aa01", token: "USDT · ETH", status: "rejected", statusColor: "#E85D5D", amount: "$50,000.00", age: "25m" },
      { color: "#4ADE80", requester: "payments@vercel.com", token: "USDC · Base", status: "approved", statusColor: "#4ADE80", amount: "$120.00", age: "33m" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "180px", flexShrink: 0, fontSize: "13px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
            {row.requester}
          </span>
          <span style={{ width: "120px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.token}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: "var(--landing-text-primary)" }}>
            {row.amount}
          </span>
          <span style={{ width: "60px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.age}
          </span>
        </div>
      );
    },
  },

  Invoices: {
    title: "Invoices",
    columns: [
      { label: "", width: "24px" },
      { label: "Invoice", width: "120px" },
      { label: "Client", width: "180px" },
      { label: "Status", width: "120px" },
      { label: "Amount", flex: true },
      { label: "Due", width: "80px", align: "right" },
    ],
    rows: [
      { color: "#4ADE80", number: "#INV-2041", client: "Acme Corp", status: "paid", statusColor: "#4ADE80", amount: "$3,200.00", due: "Paid" },
      { color: "#E85D5D", number: "#INV-2042", client: "Helicone", status: "overdue", statusColor: "#E85D5D", amount: "$1,400.00", due: "2d ago" },
      { color: "#E8A44A", number: "#INV-2043", client: "OpenAI", status: "pending", statusColor: "#E8A44A", amount: "$8,750.00", due: "In 3d" },
      { color: "#4ADE80", number: "#INV-2044", client: "Vercel", status: "paid", statusColor: "#4ADE80", amount: "$249.00", due: "Paid" },
      { color: "#5B8DEF", number: "#INV-2045", client: "Anthropic", status: "draft", statusColor: "#5B8DEF", amount: "$12,000.00", due: "In 7d" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "120px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-muted)" }}>
            {row.number}
          </span>
          <span style={{ width: "180px", flexShrink: 0, fontSize: "13px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-primary)" }}>
            {row.client}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: "var(--landing-text-primary)" }}>
            {row.amount}
          </span>
          <span style={{ width: "80px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.due}
          </span>
        </div>
      );
    },
  },

  "x402 Challenges": {
    title: "x402 HTTP Challenges",
    columns: [
      { label: "", width: "24px" },
      { label: "Endpoint", width: "200px" },
      { label: "Token", width: "100px" },
      { label: "Status", width: "120px" },
      { label: "Amount", flex: true },
      { label: "Time", width: "60px", align: "right" },
    ],
    rows: [
      { color: "#4ADE80", endpoint: "GET /api/v1/infer", token: "USDC · Base", status: "paid", statusColor: "#4ADE80", amount: "+$0.002", time: "1m" },
      { color: "#5B8DEF", endpoint: "POST /api/v1/embed", token: "USDC · Base", status: "challenged", statusColor: "#5B8DEF", amount: "+$0.010", time: "3m" },
      { color: "#4ADE80", endpoint: "GET /api/v2/search", token: "USDC · Base", status: "paid", statusColor: "#4ADE80", amount: "+$0.005", time: "7m" },
      { color: "#E8A44A", endpoint: "POST /api/v1/generate", token: "EURC · Base", status: "pending", statusColor: "#E8A44A", amount: "+$0.050", time: "12m" },
      { color: "#4ADE80", endpoint: "GET /api/v3/data", token: "USDC · Base", status: "paid", statusColor: "#4ADE80", amount: "+$0.001", time: "18m" },
    ],
    renderRow(row, i) {
      return (
        <div
          key={i}
          className="flex items-center py-3 px-3 cursor-default"
          style={{ background: i % 2 === 1 ? "var(--landing-border)" : "transparent" }}
        >
          <span style={{ width: "24px", flexShrink: 0 }}>
            <span className="w-1.5 h-1.5 rounded-[3px] inline-block" style={{ background: row.color }} />
          </span>
          <span style={{ width: "200px", flexShrink: 0, fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "var(--landing-text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", paddingRight: "8px" }}>
            {row.endpoint}
          </span>
          <span style={{ width: "100px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-tertiary)" }}>
            {row.token}
          </span>
          <span style={{ width: "120px", flexShrink: 0 }}>
            <span className="rounded-sm py-0.5 px-2 inline-block" style={{ fontSize: "10px", fontFamily: "'JetBrains Mono', monospace", color: row.statusColor, background: `${row.statusColor}14` }}>
              {row.status}
            </span>
          </span>
          <span style={{ flex: 1, fontSize: "13px", fontFamily: "Inter, sans-serif", fontWeight: 500, color: row.color }}>
            {row.amount}
          </span>
          <span style={{ width: "60px", flexShrink: 0, fontSize: "12px", fontFamily: "Inter, sans-serif", color: "var(--landing-text-muted)", textAlign: "right" }}>
            {row.time}
          </span>
        </div>
      );
    },
  },
};

// ─── Dot color maps ───────────────────────────────────────────────────────────

const outboundDots = {
  Transactions: "#4ADE80",
  "Audit Log": "#E8A44A",
};

const inboundDots = {
  Deposits: "#5B8DEF",
  "x402 Challenges": "#5B8DEF",
};

// ─── Shared Components ────────────────────────────────────────────────────────

function Sidebar({ items, activeTab, onTabChange, dotMap }) {
  return (
    <>
      {/* Desktop sidebar */}
      <div
        className="hidden md:block py-4"
        style={{ width: "200px", flexShrink: 0, borderRight: "1px solid var(--landing-border)" }}
      >
        {items.map((label) => {
          const isActive = label === activeTab;
          const dotColor = dotMap[label];
          return (
            <button
              key={label}
              type="button"
              onClick={() => onTabChange(label)}
              className="w-full flex items-center gap-2 mx-2 py-[7px] px-2.5 rounded-md cursor-pointer transition-colors text-left"
              style={{
                background: isActive ? "var(--landing-border)" : "transparent",
                width: "calc(100% - 16px)",
              }}
            >
              {dotColor ? (
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: dotColor }} />
              ) : (
                <span className="w-1.5 h-1.5 flex-shrink-0" />
              )}
              <span
                style={{
                  fontSize: "13px",
                  fontFamily: "Inter, sans-serif",
                  color: isActive ? "var(--landing-text-primary)" : "var(--landing-text-muted)",
                }}
              >
                {label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Mobile horizontal tab bar */}
      <div
        className="md:hidden overflow-x-auto"
        style={{ borderBottom: "1px solid var(--landing-border)" }}
      >
        <div className="flex px-3 py-2" style={{ gap: "4px", minWidth: "max-content" }}>
          {items.map((label) => {
            const isActive = label === activeTab;
            const dotColor = dotMap[label];
            return (
              <button
                key={label}
                type="button"
                onClick={() => onTabChange(label)}
                className="flex items-center gap-1.5 py-1.5 px-3 rounded-md whitespace-nowrap transition-colors"
                style={{
                  background: isActive ? "var(--landing-border)" : "transparent",
                }}
              >
                {dotColor ? (
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: dotColor }} />
                ) : (
                  <span className="w-1.5 h-1.5 flex-shrink-0" />
                )}
                <span
                  style={{
                    fontSize: "12px",
                    fontFamily: "Inter, sans-serif",
                    color: isActive ? "var(--landing-text-primary)" : "var(--landing-text-muted)",
                  }}
                >
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}

function TitleBar({ title }) {
  return (
    <div
      className="flex items-center justify-center py-3 relative"
      style={{ borderBottom: "1px solid var(--landing-border)" }}
    >
      <div className="absolute left-4 flex gap-1.5">
        <span className="w-3 h-3 rounded-md" style={{ backgroundColor: "var(--landing-border-hover)" }} />
        <span className="w-3 h-3 rounded-md" style={{ backgroundColor: "var(--landing-border-hover)" }} />
        <span className="w-3 h-3 rounded-md" style={{ backgroundColor: "var(--landing-border-hover)" }} />
      </div>
      <span
        style={{
          fontSize: "12px",
          fontFamily: "'JetBrains Mono', monospace",
          color: "var(--landing-text-muted)",
        }}
      >
        {title}
      </span>
    </div>
  );
}

function DataTable({ viewData }) {
  const { title, columns, rows, renderRow } = viewData;
  return (
    <div className="flex-1 p-6 min-w-0">
      <div className="flex items-center justify-between mb-6">
        <span
          style={{
            fontSize: "14px",
            fontFamily: "Inter, sans-serif",
            fontWeight: 500,
            color: "var(--landing-text-primary)",
          }}
        >
          {title}
        </span>
        <span
          className="rounded px-2.5 py-1"
          style={{
            fontSize: "11px",
            fontFamily: "'JetBrains Mono', monospace",
            color: "var(--landing-text-muted)",
            backgroundColor: "var(--landing-border)",
          }}
        >
          LAST 24H
        </span>
      </div>

      <div className="overflow-x-auto">
        <div style={{ minWidth: "560px" }}>
          <div
            className="flex items-center py-2.5 px-3"
            style={{
              fontSize: "11px",
              fontFamily: "Inter, sans-serif",
              color: "var(--landing-text-muted)",
              borderBottom: "1px solid var(--landing-border)",
            }}
          >
            {columns.map((col, i) => (
              <span
                key={i}
                style={{
                  ...(col.flex ? { flex: 1 } : { width: col.width, flexShrink: 0 }),
                  ...(col.align === "right" ? { textAlign: "right" } : {}),
                }}
              >
                {col.label}
              </span>
            ))}
          </div>

          {rows.map((row, i) => renderRow(row, i))}
        </div>
      </div>
    </div>
  );
}

// ─── Outbound Sub-component ───────────────────────────────────────────────────

const outboundTabs = ["Transactions", "Agents", "Policies", "Wallets", "Audit Log"];

function OutboundDashboard() {
  const [activeTab, setActiveTab] = useState("Transactions");

  return (
    <div
      className="w-full rounded-[14px] overflow-hidden"
      style={{
        maxWidth: "1152px",
        background: "var(--landing-surface)",
        border: "1px solid var(--landing-border)",
      }}
    >
      <TitleBar title={`sardis dashboard: ${activeTab.toLowerCase()}`} />
      <div className="flex flex-col md:flex-row">
        <Sidebar
          items={outboundTabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          dotMap={outboundDots}
        />
        <DataTable viewData={outboundData[activeTab]} />
      </div>
    </div>
  );
}

// ─── Inbound Sub-component ────────────────────────────────────────────────────

const inboundTabs = ["Transactions", "Deposits", "Payment Requests", "Invoices", "x402 Challenges"];

function InboundDashboard() {
  const [activeTab, setActiveTab] = useState("Deposits");

  return (
    <div
      className="w-full rounded-[14px] overflow-hidden"
      style={{
        maxWidth: "1152px",
        background: "var(--landing-surface)",
        border: "1px solid var(--landing-border)",
      }}
    >
      <TitleBar title={`sardis dashboard: ${activeTab.toLowerCase()}`} />
      <div className="flex flex-col md:flex-row">
        <Sidebar
          items={inboundTabs}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          dotMap={inboundDots}
        />
        <DataTable viewData={inboundData[activeTab]} />
      </div>
    </div>
  );
}

// ─── Main Export ──────────────────────────────────────────────────────────────

export default function DashboardMockup() {
  return (
    <div style={{ background: "var(--landing-bg)" }}>
      {/* Section 1: Outbound Transactions */}
      <div className="flex flex-col items-center w-full max-w-[1440px] mx-auto pt-[60px] md:pt-[100px] gap-8 px-5 md:px-12 xl:px-20">
        <div className="flex flex-col items-center gap-3">
          <span
            className="uppercase tracking-widest"
            style={{
              fontSize: "11px",
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--landing-blue)",
            }}
          >
            SEE EVERY TRANSACTION IN REAL TIME
          </span>
          <h2
            className="text-center"
            style={{
              fontSize: "clamp(28px, 4vw, 36px)",
              lineHeight: "clamp(34px, 5vw, 42px)",
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              color: "var(--landing-text-primary)",
            }}
          >
            Your agents pay. You watch.
          </h2>
        </div>

        <OutboundDashboard />
      </div>

      {/* Section 2: Inbound Deposits */}
      <div className="flex flex-col items-center w-full max-w-[1440px] mx-auto pt-[60px] md:pt-[100px] gap-8 px-5 md:px-12 xl:px-20 pb-[60px] md:pb-[100px]">
        <div className="flex flex-col items-center gap-3">
          <span
            className="uppercase tracking-widest"
            style={{
              fontSize: "11px",
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--landing-blue)",
            }}
          >
            INBOUND PAYMENTS
          </span>
          <h2
            className="text-center"
            style={{
              fontSize: "clamp(28px, 4vw, 36px)",
              lineHeight: "clamp(34px, 5vw, 42px)",
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              color: "var(--landing-text-primary)",
            }}
          >
            They can get paid too.
          </h2>
          <p
            className="text-center"
            style={{
              fontSize: "16px",
              lineHeight: "26px",
              fontFamily: "Inter, sans-serif",
              fontWeight: 300,
              color: "var(--landing-text-tertiary)",
              maxWidth: "520px",
            }}
          >
            Generate payment requests, track deposits in real time, and auto-reconcile incoming funds on Base.
          </p>
        </div>

        <InboundDashboard />
      </div>
    </div>
  );
}
