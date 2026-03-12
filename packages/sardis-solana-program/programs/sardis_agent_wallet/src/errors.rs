use anchor_lang::prelude::*;

/// Error codes mapped to Python policy engine reason_codes.
/// Codes 6000-6020 reserved for policy enforcement.
#[error_code]
pub enum SardisError {
    /// 6000 — amount_must_be_positive
    #[msg("Transfer amount must be greater than zero")]
    AmountMustBePositive,

    /// 6001 — per_transaction_limit
    #[msg("Amount exceeds per-transaction limit")]
    PerTxLimitExceeded,

    /// 6002 — total_limit_exceeded
    #[msg("Amount exceeds lifetime spending limit")]
    TotalLimitExceeded,

    /// 6003 — daily_limit_exceeded
    #[msg("Amount exceeds daily spending limit")]
    DailyLimitExceeded,

    /// 6004 — weekly_limit_exceeded
    #[msg("Amount exceeds weekly spending limit")]
    WeeklyLimitExceeded,

    /// 6005 — monthly_limit_exceeded
    #[msg("Amount exceeds monthly spending limit")]
    MonthlyLimitExceeded,

    /// 6006 — merchant_denied
    #[msg("Merchant is on the deny list")]
    MerchantDenied,

    /// 6007 — merchant_not_allowlisted
    #[msg("Merchant is not on the allowlist")]
    MerchantNotAllowed,

    /// 6008 — merchant_cap_exceeded
    #[msg("Amount exceeds per-merchant cap")]
    MerchantCapExceeded,

    /// 6009 — token_not_allowlisted
    #[msg("Token mint is not on the allowlist")]
    TokenNotAllowed,

    /// 6010 — wallet_paused
    #[msg("Wallet is paused (frozen)")]
    WalletPaused,

    /// 6011 — cosigner_required
    #[msg("Co-signer required for this amount")]
    CosignerRequired,

    /// 6012 — cosign_daily_limit_exceeded
    #[msg("Amount exceeds co-signed daily limit")]
    CosignDailyLimitExceeded,

    /// 6013 — merchant_registry_full
    #[msg("Merchant registry is full (max 32 entries)")]
    MerchantRegistryFull,

    /// 6014 — merchant_not_found
    #[msg("Merchant not found in registry")]
    MerchantNotFound,

    /// 6015 — token_list_full
    #[msg("Token allowlist is full (max 8 entries)")]
    TokenListFull,

    /// 6016 — token_not_found
    #[msg("Token not found in allowlist")]
    TokenNotFound,

    /// 6017 — invalid_trust_level
    #[msg("Invalid trust level (must be 0-3)")]
    InvalidTrustLevel,

    /// 6018 — wallet_not_paused
    #[msg("Wallet is not paused")]
    WalletNotPaused,

    /// 6019 — token_already_listed
    #[msg("Token already in allowlist")]
    TokenAlreadyListed,

    /// 6020 — merchant_already_listed
    #[msg("Merchant already in registry")]
    MerchantAlreadyListed,
}
