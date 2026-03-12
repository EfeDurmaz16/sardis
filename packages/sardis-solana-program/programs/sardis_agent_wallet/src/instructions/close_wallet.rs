use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::SardisError;

#[derive(Accounts)]
pub struct CloseWallet<'info> {
    /// Sardis platform authority — receives reclaimed rent.
    #[account(mut)]
    pub authority: Signer<'info>,

    /// Owner pubkey used as PDA seed.
    /// CHECK: Only used for PDA derivation, not as signer.
    pub owner: UncheckedAccount<'info>,

    /// AgentWallet PDA — will be closed.
    #[account(
        mut,
        seeds = [b"sardis_wallet", owner.key().as_ref()],
        bump,
        constraint = {
            let w = wallet.load()?;
            w.authority == authority.key()
        } @ SardisError::InvalidTrustLevel,
        close = authority,
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,

    /// MerchantRegistry PDA — will be closed.
    #[account(
        mut,
        seeds = [b"merchants", wallet.key().as_ref()],
        bump,
        constraint = {
            let r = merchant_registry.load()?;
            r.wallet == wallet.key()
        } @ SardisError::MerchantNotFound,
        close = authority,
    )]
    pub merchant_registry: AccountLoader<'info, MerchantRegistry>,

    /// TokenAllowlist PDA — will be closed.
    #[account(
        mut,
        seeds = [b"tokens", wallet.key().as_ref()],
        bump,
        constraint = {
            let t = token_list.load()?;
            t.wallet == wallet.key()
        } @ SardisError::TokenNotFound,
        close = authority,
    )]
    pub token_list: AccountLoader<'info, TokenAllowlist>,
}

pub fn handler(ctx: Context<CloseWallet>) -> Result<()> {
    msg!(
        "Wallet closed: owner={}, rent reclaimed by {}",
        ctx.accounts.owner.key(),
        ctx.accounts.authority.key()
    );
    Ok(())
}
