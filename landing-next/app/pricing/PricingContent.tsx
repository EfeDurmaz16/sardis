"use client";

import { useState } from "react";

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="rounded-xl overflow-hidden transition-colors"
      style={{
        background: "#0A0B0D",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
        aria-expanded={open}
      >
        <span
          className="text-sm font-medium"
          style={{ fontFamily: "'Inter', sans-serif", color: "#E0E0E0" }}
        >
          {q}
        </span>
        <span
          className="shrink-0 transition-transform duration-200"
          style={{
            transform: open ? "rotate(45deg)" : "rotate(0deg)",
            color: "#505460",
          }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path
              d="M10 4v12M4 10h12"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </span>
      </button>

      {open && (
        <div
          className="px-6 pb-5 text-sm leading-relaxed"
          style={{ fontFamily: "'Inter', sans-serif", color: "#808080" }}
        >
          {a}
        </div>
      )}
    </div>
  );
}

export default function PricingContent({
  faqs,
}: {
  faqs: { q: string; a: string }[];
}) {
  return (
    <div className="flex flex-col gap-3">
      {faqs.map((faq) => (
        <FAQItem key={faq.q} q={faq.q} a={faq.a} />
      ))}
    </div>
  );
}
