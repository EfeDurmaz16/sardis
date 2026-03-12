use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::SardisError;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct UpdatePolicyParams {
    pub trust_level: Option<u8>,
    pub limit_per_tx: Option<u64>,
    pub limit_total: Option<u64>,
    pub daily_limit: Option<u64>,
    pub weekly_limit: Option<u64>,
    pub monthly_limit: Option<u64>,
    pub cosign_limit_per_tx: Option<u64>,
    pub cosign_daily_limit: Option<u64>,
    pub co_signer: Option<Pubkey>,
}

#[derive(Accounts)]
pub struct UpdatePolicy<'info> {
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

pub fn handler(ctx: Context<UpdatePolicy>, params: UpdatePolicyParams) -> Result<()> {
    let mut wallet = ctx.accounts.wallet.load_mut()?;

    if let Some(trust_level) = params.trust_level {
        require!(trust_level <= TRUST_UNLIMITED, SardisError::InvalidTrustLevel);
        wallet.trust_level = trust_level;
    }
    if let Some(v) = params.limit_per_tx { wallet.limit_per_tx = v; }
    if let Some(v) = params.limit_total { wallet.limit_total = v; }
    if let Some(v) = params.daily_limit { wallet.daily_limit = v; }
    if let Some(v) = params.weekly_limit { wallet.weekly_limit = v; }
    if let Some(v) = params.monthly_limit { wallet.monthly_limit = v; }
    if let Some(v) = params.cosign_limit_per_tx { wallet.cosign_limit_per_tx = v; }
    if let Some(v) = params.cosign_daily_limit { wallet.cosign_daily_limit = v; }
    if let Some(co_signer) = params.co_signer { wallet.co_signer = co_signer; }

    msg!("Policy updated for wallet: {}", ctx.accounts.wallet.key());

    Ok(())
}
