use anchor_lang::prelude::*;

/// Maximum merchant entries per wallet.
pub const MAX_MERCHANTS: usize = 32;

/// Rule type for a merchant entry.
pub const RULE_ALLOW: u8 = 0;
pub const RULE_DENY: u8 = 1;

/// Single merchant entry in the registry.
#[zero_copy]
#[repr(C)]
pub struct MerchantEntry {
    /// Merchant wallet address.
    pub address: Pubkey,
    /// 0 = Allow, 1 = Deny.
    pub rule_type: u8,
    /// Whether this slot is active.
    pub active: u8,
    /// Padding for alignment.
    pub _padding: [u8; 6],
    /// Per-transaction cap for this merchant (0 = no cap).
    pub max_per_tx: u64,
}

/// MerchantRegistry PDA account — zero_copy for heap allocation.
/// Seeds: [b"merchants", wallet.key().as_ref()]
#[account(zero_copy)]
#[repr(C)]
pub struct MerchantRegistry {
    /// The AgentWallet this registry belongs to.
    pub wallet: Pubkey,
    /// Number of active entries.
    pub count: u8,
    /// Padding.
    pub _padding: [u8; 7],
    /// Merchant entries.
    pub entries: [MerchantEntry; MAX_MERCHANTS],
}

impl MerchantRegistry {
    pub const SIZE: usize = 8 + std::mem::size_of::<MerchantRegistry>();

    /// Find a merchant by address. Returns slot index if found.
    pub fn find(&self, address: &Pubkey) -> Option<usize> {
        self.entries.iter().position(|e| e.active != 0 && e.address == *address)
    }

    /// Find first inactive slot. Returns slot index if available.
    pub fn find_free_slot(&self) -> Option<usize> {
        self.entries.iter().position(|e| e.active == 0)
    }
}
