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
  // When the merchant didn't set a logo, fall back to the Sardis
  // brand mark rather than a letter avatar. Keeps the checkout UI
  // feeling professional for demo sessions and unbranded merchants
  // while real merchant logos still win when set.
  const displayLogoUrl = logoUrl || "/sardis-logo.svg";
  return (
    <div className="flex flex-col items-center text-center mb-8">
      <div className="w-12 h-12 rounded-full border border-[var(--checkout-border)] bg-white flex items-center justify-center mb-3 overflow-hidden">
        <img
          src={displayLogoUrl}
          alt={merchantName}
          className="w-8 h-8 object-contain text-[var(--checkout-fg)]"
        />
      </div>
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
