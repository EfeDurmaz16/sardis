use anchor_lang::prelude::*;
use crate::state::AgentWallet;
use crate::errors::SardisError;

#[derive(Accounts)]
pub struct UpdateAuthority<'info> {
    /// Current Sardis platform authority.
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

pub fn handler(ctx: Context<UpdateAuthority>, new_authority: Pubkey) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    let old = wallet.authority;
    wallet.authority = new_authority;
    msg!("Authority transferred: {} -> {}", old, new_authority);
    Ok(())
}
