use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::SardisError;

#[derive(Accounts)]
pub struct ManageMerchant<'info> {
    /// Sardis platform authority.
    pub authority: Signer<'info>,

    /// AgentWallet PDA — for authority check.
    #[account(
        constraint = {
            let w = wallet.load()?;
            w.authority == authority.key()
        } @ SardisError::InvalidTrustLevel,
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,

    /// MerchantRegistry PDA.
    #[account(
        mut,
        seeds = [b"merchants", wallet.key().as_ref()],
        bump,
        constraint = {
            let r = merchant_registry.load()?;
            r.wallet == wallet.key()
        } @ SardisError::MerchantNotFound,
    )]
    pub merchant_registry: AccountLoader<'info, MerchantRegistry>,
}

pub fn add_merchant_handler(
    ctx: Context<ManageMerchant>,
    address: Pubkey,
    rule_type: u8,
    max_per_tx: u64,
) -> Result<()> {
    let mut registry = ctx.accounts.merchant_registry.load_mut()?;

    require!(registry.find(&address).is_none(), SardisError::MerchantAlreadyListed);

    let slot = registry.find_free_slot().ok_or(SardisError::MerchantRegistryFull)?;

    registry.entries[slot] = MerchantEntry {
        address,
        rule_type,
        active: 1,
        _padding: [0u8; 6],
        max_per_tx,
    };
    registry.count = registry.count.saturating_add(1);

    msg!("Merchant added: {} (rule={})", address, rule_type);
    Ok(())
}

pub fn remove_merchant_handler(ctx: Context<ManageMerchant>, address: Pubkey) -> Result<()> {
    let mut registry = ctx.accounts.merchant_registry.load_mut()?;

    let slot = registry.find(&address).ok_or(SardisError::MerchantNotFound)?;

    registry.entries[slot] = MerchantEntry {
        address: Pubkey::default(),
        rule_type: 0,
        active: 0,
        _padding: [0u8; 6],
        max_per_tx: 0,
    };
    registry.count = registry.count.saturating_sub(1);

    msg!("Merchant removed: {}", address);
    Ok(())
}

#[derive(Accounts)]
pub struct SetAllowlistMode<'info> {
    /// Sardis platform authority.
    pub authority: Signer<'info>,

    /// AgentWallet PDA.
    #[account(
        mut,
        constraint = {
            let w = wallet.load()?;
            w.authority == authority.key()
        } @ SardisError::InvalidTrustLevel,
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,
}

pub fn set_allowlist_mode_handler(ctx: Context<SetAllowlistMode>, enabled: bool) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    wallet.use_allowlist = if enabled { 1 } else { 0 };
    msg!("Merchant allowlist mode: {}", enabled);
    Ok(())
}
