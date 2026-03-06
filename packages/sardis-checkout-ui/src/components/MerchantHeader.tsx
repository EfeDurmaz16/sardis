interface MerchantHeaderProps {
  merchantName: string;
  logoUrl: string | null;
  amount: string;
  currency: string;
  description: string | null;
}

export default function MerchantHeader({
  merchantName,
  logoUrl,
  amount,
  currency,
  description,
}: MerchantHeaderProps) {
  return (
    <div className="flex flex-col items-center text-center mb-8">
      {logoUrl ? (
        <img
          src={logoUrl}
          alt={merchantName}
          className="w-12 h-12 rounded-full mb-3 object-cover"
        />
      ) : (
        <div className="w-12 h-12 rounded-full bg-[var(--checkout-border)] flex items-center justify-center mb-3">
          <span className="text-lg font-semibold text-[var(--checkout-secondary)]">
            {merchantName.charAt(0).toUpperCase()}
          </span>
        </div>
      )}
      <p className="text-sm text-[var(--checkout-secondary)] mb-1">
        {merchantName}
      </p>
      {description && (
        <p className="text-xs text-[var(--checkout-muted)] mb-3">
          {description}
        </p>
      )}
      <p className="text-4xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
        {amount} <span className="text-lg text-[var(--checkout-muted)]">{currency}</span>
      </p>
    </div>
  );
}
