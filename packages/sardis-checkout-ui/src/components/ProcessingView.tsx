const steps = [
  { label: "Policy verified", done: true },
  { label: "Submitting transaction", done: false, active: true },
  { label: "Awaiting confirmation", done: false },
];

export default function ProcessingView() {
  return (
    <div className="flex flex-col items-center py-8">
      {/* Spinner */}
      <div className="w-12 h-12 border-2 border-[var(--checkout-border)] border-t-[var(--checkout-blue)] rounded-full animate-spin mb-6" />

      <h2
        className="text-lg font-semibold mb-1"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Processing Payment
      </h2>
      <p className="text-sm text-[var(--checkout-muted)] mb-8">
        This usually takes a few seconds
      </p>

      {/* Steps */}
      <div className="w-full space-y-3">
        {steps.map((step) => (
          <div
            key={step.label}
            className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-[var(--checkout-bg)]"
          >
            {step.done ? (
              <svg className="w-4 h-4 text-[var(--checkout-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            ) : step.active ? (
              <span className="w-4 h-4 border-2 border-[var(--checkout-blue)] border-t-transparent rounded-full animate-spin" />
            ) : (
              <span className="w-4 h-4 rounded-full border-2 border-[var(--checkout-border)]" />
            )}
            <span
              className={`text-sm ${step.done ? "text-[var(--checkout-success)]" : step.active ? "text-[var(--checkout-primary)] font-medium" : "text-[var(--checkout-muted)]"}`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
