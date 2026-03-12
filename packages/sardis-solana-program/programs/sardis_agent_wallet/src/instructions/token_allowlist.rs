use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::SardisError;

#[derive(Accounts)]
pub struct ManageToken<'info> {
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

    /// TokenAllowlist PDA.
    #[account(
        mut,
        seeds = [b"tokens", wallet.key().as_ref()],
        bump,
        constraint = {
            let t = token_list.load()?;
            t.wallet == wallet.key()
        } @ SardisError::TokenNotFound,
    )]
    pub token_list: AccountLoader<'info, TokenAllowlist>,
}

pub fn add_token_handler(ctx: Context<ManageToken>, mint: Pubkey) -> Result<()> {
    let mut list = ctx.accounts.token_list.load_mut()?;

    require!(!list.contains(&mint), SardisError::TokenAlreadyListed);
    require!((list.count as usize) < MAX_TOKENS, SardisError::TokenListFull);

    let idx = list.count as usize;
    list.mints[idx] = mint;
    list.count += 1;

    msg!("Token added: {}", mint);
    Ok(())
}

pub fn remove_token_handler(ctx: Context<ManageToken>, mint: Pubkey) -> Result<()> {
    let mut list = ctx.accounts.token_list.load_mut()?;

    let idx = list.find(&mint).ok_or(SardisError::TokenNotFound)?;

    // Swap-remove: move last element to removed slot, decrement count
    let last = (list.count - 1) as usize;
    if idx != last {
        list.mints[idx] = list.mints[last];
    }
    list.mints[last] = Pubkey::default();
    list.count -= 1;

    msg!("Token removed: {}", mint);
    Ok(())
}

#[derive(Accounts)]
pub struct SetTokenEnforcement<'info> {
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

pub fn set_token_enforced_handler(ctx: Context<SetTokenEnforcement>, enforced: bool) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    wallet.enforce_token_allowlist = if enforced { 1 } else { 0 };
    msg!("Token allowlist enforcement: {}", enforced);
    Ok(())
}
