use anchor_lang::prelude::*;

/// Trust levels mirroring Python TrustLevel enum.
/// 0=LOW, 1=MEDIUM, 2=HIGH, 3=UNLIMITED
pub const TRUST_LOW: u8 = 0;
pub const TRUST_MEDIUM: u8 = 1;
pub const TRUST_HIGH: u8 = 2;
pub const TRUST_UNLIMITED: u8 = 3;

/// Time window durations in seconds.
pub const SECONDS_PER_DAY: i64 = 86_400;
pub const SECONDS_PER_WEEK: i64 = 604_800;
pub const SECONDS_PER_MONTH: i64 = 2_592_000; // 30 days

/// AgentWallet PDA account — zero_copy for heap allocation.
/// Seeds: [b"sardis_wallet", owner.key().as_ref()]
#[account(zero_copy)]
#[repr(C)]
pub struct AgentWallet {
    /// Agent MPC signer (Turnkey ed25519) — can execute transfers.
    pub owner: Pubkey,
    /// Sardis platform key — manages policy, freeze, merchant/token lists.
    pub authority: Pubkey,
    /// Optional co-signer for elevated limits. Pubkey::default() if unset.
    pub co_signer: Pubkey,

    /// Trust level: 0=LOW, 1=MEDIUM, 2=HIGH, 3=UNLIMITED.
    pub trust_level: u8,
    /// PDA bump seed.
    pub bump: u8,
    /// Emergency stop — blocks all transfers when true.
    pub paused: u8,
    /// When true, only merchants in the MerchantRegistry with Allow rule can receive.
    pub use_allowlist: u8,
    /// When true, only tokens in the TokenAllowlist can be transferred.
    pub enforce_token_allowlist: u8,

    /// Padding for alignment.
    pub _padding: [u8; 3],

    /// Per-transaction cap in token minor units (e.g. 6 decimals for USDC).
    pub limit_per_tx: u64,
    /// Lifetime spending cap.
    pub limit_total: u64,
    /// Lifetime cumulative spend.
    pub spent_total: u64,

    /// Daily rolling window.
    pub daily_limit: u64,
    pub daily_spent: u64,
    pub daily_reset_ts: i64,

    /// Weekly rolling window.
    pub weekly_limit: u64,
    pub weekly_spent: u64,
    pub weekly_reset_ts: i64,

    /// Monthly rolling window.
    pub monthly_limit: u64,
    pub monthly_spent: u64,
    pub monthly_reset_ts: i64,

    /// Co-signed per-transaction limit (typically 10x of limit_per_tx).
    pub cosign_limit_per_tx: u64,
    /// Co-signed daily limit (typically 10x of daily_limit).
    pub cosign_daily_limit: u64,

    /// Reserved for future fields without reallocation.
    pub _reserved: [u8; 64],
}

impl AgentWallet {
    /// Account space: 8 (discriminator) + size_of::<AgentWallet>().
    pub const SIZE: usize = 8 + std::mem::size_of::<AgentWallet>();

    pub fn is_paused(&self) -> bool {
        self.paused != 0
    }

    pub fn is_allowlist_mode(&self) -> bool {
        self.use_allowlist != 0
    }

    pub fn is_token_enforced(&self) -> bool {
        self.enforce_token_allowlist != 0
    }

    /// Reset any expired time windows based on current clock.
    pub fn reset_expired_windows(&mut self, now: i64) {
        if now >= self.daily_reset_ts + SECONDS_PER_DAY {
            self.daily_spent = 0;
            self.daily_reset_ts = now;
        }
        if now >= self.weekly_reset_ts + SECONDS_PER_WEEK {
            self.weekly_spent = 0;
            self.weekly_reset_ts = now;
        }
        if now >= self.monthly_reset_ts + SECONDS_PER_MONTH {
            self.monthly_spent = 0;
            self.monthly_reset_ts = now;
        }
    }

    /// Record a successful spend against all tracking counters.
    pub fn record_spend(&mut self, amount: u64) {
        self.spent_total = self.spent_total.saturating_add(amount);
        self.daily_spent = self.daily_spent.saturating_add(amount);
        self.weekly_spent = self.weekly_spent.saturating_add(amount);
        self.monthly_spent = self.monthly_spent.saturating_add(amount);
    }
}
