use anchor_lang::prelude::*;
use crate::state::AgentWallet;
use crate::errors::SardisError;

#[derive(Accounts)]
pub struct FreezeWallet<'info> {
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

pub fn freeze_handler(ctx: Context<FreezeWallet>) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    wallet.paused = 1;
    msg!("Wallet frozen: {}", ctx.accounts.wallet.key());
    Ok(())
}

pub fn unfreeze_handler(ctx: Context<FreezeWallet>) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    require!(wallet.is_paused(), SardisError::WalletNotPaused);
    wallet.paused = 0;
    msg!("Wallet unfrozen: {}", ctx.accounts.wallet.key());
    Ok(())
}
