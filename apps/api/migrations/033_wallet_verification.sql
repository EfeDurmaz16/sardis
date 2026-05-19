-- Store verified payer wallet address on session (for external wallet + onramp auth)
ALTER TABLE merchant_checkout_sessions
  ADD COLUMN IF NOT EXISTS payer_wallet_address TEXT;

-- Allow 'external_wallet' as payment method
ALTER TABLE merchant_checkout_sessions
  DROP CONSTRAINT IF EXISTS merchant_checkout_sessions_payment_method_check;
ALTER TABLE merchant_checkout_sessions
  ADD CONSTRAINT merchant_checkout_sessions_payment_method_check
  CHECK (payment_method IS NULL OR payment_method IN ('wallet', 'fund_and_pay', 'external_wallet'));
