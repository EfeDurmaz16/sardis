interface ErrorViewProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorView({ message, onRetry }: ErrorViewProps) {
  return (
    <div className="flex flex-col items-center py-6">
      {/* Error icon */}
      <div className="w-14 h-14 rounded-full bg-[#FEE2E2] flex items-center justify-center mb-4">
        <svg className="w-7 h-7 text-[var(--checkout-error)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>

      <h2
        className="text-lg font-semibold mb-1"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Payment Failed
      </h2>
      <p className="text-sm text-[var(--checkout-muted)] mb-6">
        Something went wrong with your payment
      </p>

      {/* Error detail */}
      <div className="w-full px-4 py-3 bg-[#FEF2F2] border border-[#FECACA] rounded-lg mb-6">
        <p
          className="text-xs text-[var(--checkout-error)]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {message}
        </p>
      </div>

      <button
        onClick={onRetry}
        className="w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}
