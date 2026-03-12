use anchor_lang::prelude::*;

/// Maximum token entries (USDC, USDT, PYUSD, EURC + headroom).
pub const MAX_TOKENS: usize = 8;

/// TokenAllowlist PDA account — zero_copy for heap allocation.
/// Seeds: [b"tokens", wallet.key().as_ref()]
#[account(zero_copy)]
#[repr(C)]
pub struct TokenAllowlist {
    /// The AgentWallet this list belongs to.
    pub wallet: Pubkey,
    /// Number of active tokens.
    pub count: u8,
    /// Padding.
    pub _padding: [u8; 7],
    /// Token mint addresses. Pubkey::default() = empty slot.
    pub mints: [Pubkey; MAX_TOKENS],
}

impl TokenAllowlist {
    pub const SIZE: usize = 8 + std::mem::size_of::<TokenAllowlist>();

    /// Check if a mint is in the allowlist.
    pub fn contains(&self, mint: &Pubkey) -> bool {
        self.mints.iter().take(self.count as usize).any(|m| m == mint)
    }

    /// Find index of a mint. Returns slot index if found.
    pub fn find(&self, mint: &Pubkey) -> Option<usize> {
        self.mints.iter().take(self.count as usize).position(|m| m == mint)
    }
}
