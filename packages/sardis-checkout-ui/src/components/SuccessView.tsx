import type { PaymentResult } from "@/lib/types";

interface SuccessViewProps {
  result: PaymentResult;
  successUrl?: string | null;
}

export default function SuccessView({ result, successUrl }: SuccessViewProps) {
  return (
    <div className="flex flex-col items-center py-6">
      {/* Checkmark */}
      <div className="w-14 h-14 rounded-full bg-[#DCFCE7] flex items-center justify-center mb-4">
        <svg className="w-7 h-7 text-[var(--checkout-success)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h2
        className="text-lg font-semibold mb-1"
        style={{ fontFamily: "var(--font-display)" }}
      >
        Payment Successful
      </h2>
      <p className="text-sm text-[var(--checkout-muted)] mb-6">
        {result.amount} {result.currency} sent
      </p>

      {/* Transaction details */}
      <div className="w-full bg-[var(--checkout-bg)] rounded-lg divide-y divide-[var(--checkout-border)]">
        <DetailRow label="Status" value="Confirmed" valueClass="text-[var(--checkout-success)]" />
        <DetailRow label="Amount" value={`${result.amount} ${result.currency}`} />
        {result.tx_hash && (
          <DetailRow
            label="Tx Hash"
            value={
              <a
                href={`https://basescan.org/tx/${result.tx_hash}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--checkout-blue)] hover:underline font-mono text-xs"
              >
                {result.tx_hash.slice(0, 10)}...{result.tx_hash.slice(-8)}
              </a>
            }
          />
        )}
        <DetailRow label="Session" value={result.session_id} mono />
      </div>

      {/* Actions */}
      <div className="w-full mt-6 space-y-2">
        {successUrl && (
          <a
            href={successUrl}
            className="block w-full py-3 px-4 bg-[var(--checkout-blue)] hover:bg-[var(--checkout-blue-hover)] text-white font-medium text-sm rounded-lg transition-colors text-center"
          >
            Return to Merchant
          </a>
        )}
        {result.tx_hash && (
          <a
            href={`https://basescan.org/tx/${result.tx_hash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full py-3 px-4 border border-[var(--checkout-border)] text-[var(--checkout-secondary)] hover:bg-[var(--checkout-bg)] font-medium text-sm rounded-lg transition-colors text-center"
          >
            View on BaseScan
          </a>
        )}
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono,
  valueClass,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <span className="text-xs text-[var(--checkout-muted)] uppercase tracking-wider">
        {label}
      </span>
      <span
        className={`text-sm ${valueClass ?? "text-[var(--checkout-primary)]"} ${mono ? "font-mono text-xs" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}
