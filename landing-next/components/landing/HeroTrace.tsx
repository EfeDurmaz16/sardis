"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const TRACE_STEPS = [
  { label: "sardis.pay()", detail: "Intent received", icon: "\u2192", color: "#3B82F6" },
  { label: "Policy check", detail: "12 rules evaluated", icon: "\u2713", color: "#22C55E" },
  { label: "Route selection", detail: "Tempo \u2192 USDC", icon: "\u2713", color: "#22C55E" },
  { label: "On-chain execute", detail: "tx 0xa3f...c91", icon: "\u2713", color: "#22C55E" },
  { label: "Settlement", detail: "$45.00 settled", icon: "\u2713", color: "#22C55E" },
  { label: "Audit proof", detail: "Merkle anchored", icon: "\u2713", color: "#22C55E" },
];

function TraceStep({
  step,
  index,
  activeIndex,
}: {
  step: (typeof TRACE_STEPS)[number];
  index: number;
  activeIndex: number;
}) {
  const isActive = index <= activeIndex;
  const isCurrent = index === activeIndex;

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: isActive ? 1 : 0.25, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="flex items-center gap-3 py-2"
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 transition-all duration-300"
        style={{
          background: isActive ? `${step.color}15` : "rgba(255,255,255,0.03)",
          border: `1px solid ${isActive ? `${step.color}40` : "rgba(255,255,255,0.06)"}`,
          color: isActive ? step.color : "#505460",
        }}
      >
        {isActive ? step.icon : index + 1}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className="text-[12px] font-medium"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: isActive ? "#E0E0E0" : "#505460",
            }}
          >
            {step.label}
          </span>
          {isCurrent && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: step.color }}
            />
          )}
        </div>
        <span
          className="text-[10px]"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            color: isActive ? "#808080" : "#3F3F4A",
          }}
        >
          {step.detail}
        </span>
      </div>

      {isActive && (
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-[10px] shrink-0"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            color: "#505460",
          }}
        >
          {index === 0 ? "now" : `+${index * 120}ms`}
        </motion.span>
      )}
    </motion.div>
  );
}

export default function HeroTrace() {
  const [activeIndex, setActiveIndex] = useState(-1);
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    setActiveIndex(-1);
    let step = 0;
    const interval = setInterval(() => {
      if (step <= TRACE_STEPS.length - 1) {
        setActiveIndex(step);
        step++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          setCycle((c) => c + 1);
        }, 3000);
      }
    }, 600);

    return () => clearInterval(interval);
  }, [cycle]);

  return (
    <div
      className="w-full max-w-[340px] select-none"
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      <div
        className="rounded-2xl overflow-hidden"
        style={{
          background: "var(--landing-surface, #0A0B0D)",
          border: "1px solid var(--landing-border, rgba(255,255,255,0.08))",
          boxShadow:
            "0 25px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.03) inset",
        }}
      >
        {/* Header */}
        <div className="px-5 pt-4 pb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                background:
                  activeIndex >= TRACE_STEPS.length - 1
                    ? "#22C55E"
                    : "#3B82F6",
              }}
            />
            <span
              className="text-[11px] font-medium uppercase tracking-wider"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                color:
                  activeIndex >= TRACE_STEPS.length - 1
                    ? "#22C55E"
                    : "#808080",
              }}
            >
              {activeIndex >= TRACE_STEPS.length - 1
                ? "Complete"
                : "Processing"}
            </span>
          </div>
          <span
            className="text-[10px]"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "#505460",
            }}
          >
            trace_7f3a
          </span>
        </div>

        {/* Code snippet */}
        <div
          className="mx-5 mb-3 rounded-lg px-3 py-2"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.04)",
          }}
        >
          <pre
            className="text-[11px] leading-relaxed overflow-hidden"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "#A0A0AA",
            }}
          >
            <span style={{ color: "#808080" }}>await</span>{" "}
            <span style={{ color: "#3B82F6" }}>sardis</span>
            <span style={{ color: "#505460" }}>.</span>
            <span style={{ color: "#E0E0E0" }}>pay</span>
            <span style={{ color: "#505460" }}>(</span>
            <span style={{ color: "#22C55E" }}>&quot;openai.com&quot;</span>
            <span style={{ color: "#505460" }}>, </span>
            <span style={{ color: "#C084FC" }}>45.00</span>
            <span style={{ color: "#505460" }}>)</span>
          </pre>
        </div>

        {/* Steps */}
        <div className="px-5 pb-2">
          <AnimatePresence mode="wait">
            <motion.div key={cycle}>
              {TRACE_STEPS.map((step, i) => (
                <TraceStep
                  key={step.label}
                  step={step}
                  index={i}
                  activeIndex={activeIndex}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Bottom status */}
        <div
          className="px-5 py-3 flex items-center justify-between"
          style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}
        >
          <div className="flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M7 1L12 3.5V6.5C12 9.5 9.5 12 7 13C4.5 12 2 9.5 2 6.5V3.5L7 1Z"
                stroke="#22C55E"
                strokeWidth="1.2"
                fill="none"
              />
              <path
                d="M5 7L6.5 8.5L9 5.5"
                stroke="#22C55E"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                color: "#22C55E",
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              Policy enforced
            </span>
          </div>
          <span
            style={{
              color: "#505460",
              fontSize: 10,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            Tempo mainnet
          </span>
        </div>
      </div>
    </div>
  );
}
