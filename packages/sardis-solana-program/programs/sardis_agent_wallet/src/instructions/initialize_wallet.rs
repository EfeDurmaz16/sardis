use anchor_lang::prelude::*;
use crate::state::*;

#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct InitializeWalletParams {
    pub trust_level: u8,
    pub limit_per_tx: u64,
    pub limit_total: u64,
    pub daily_limit: u64,
    pub weekly_limit: u64,
    pub monthly_limit: u64,
    pub cosign_limit_per_tx: u64,
    pub cosign_daily_limit: u64,
    pub co_signer: Pubkey,
}

/// Step 1: Create the AgentWallet PDA.
/// Call initialize_registries immediately after in the same transaction.
#[derive(Accounts)]
pub struct InitializeWallet<'info> {
    /// The agent owner whose wallet is being created.
    /// CHECK: This is just a pubkey used as PDA seed — not a signer.
    pub owner: UncheckedAccount<'info>,

    /// Sardis platform authority — must sign and pay rent.
    #[account(mut)]
    pub authority: Signer<'info>,

    /// AgentWallet PDA (zero_copy).
    #[account(
        init,
        payer = authority,
        space = AgentWallet::SIZE,
        seeds = [b"sardis_wallet", owner.key().as_ref()],
        bump
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<InitializeWallet>, params: InitializeWalletParams) -> Result<()> {
    require!(
        params.trust_level <= TRUST_UNLIMITED,
        crate::errors::SardisError::InvalidTrustLevel
    );

    let mut wallet = ctx.accounts.wallet.load_init()?;
    let now = Clock::get()?.unix_timestamp;

    wallet.owner = ctx.accounts.owner.key();
    wallet.authority = ctx.accounts.authority.key();
    wallet.co_signer = params.co_signer;
    wallet.trust_level = params.trust_level;
    wallet.bump = ctx.bumps.wallet;
    wallet.paused = 0;
    wallet.use_allowlist = 0;
    wallet.enforce_token_allowlist = 0;
    wallet._padding = [0u8; 3];
    wallet.limit_per_tx = params.limit_per_tx;
    wallet.limit_total = params.limit_total;
    wallet.spent_total = 0;
    wallet.daily_limit = params.daily_limit;
    wallet.daily_spent = 0;
    wallet.daily_reset_ts = now;
    wallet.weekly_limit = params.weekly_limit;
    wallet.weekly_spent = 0;
    wallet.weekly_reset_ts = now;
    wallet.monthly_limit = params.monthly_limit;
    wallet.monthly_spent = 0;
    wallet.monthly_reset_ts = now;
    wallet.cosign_limit_per_tx = params.cosign_limit_per_tx;
    wallet.cosign_daily_limit = params.cosign_daily_limit;
    wallet._reserved = [0u8; 64];

    msg!(
        "Sardis wallet initialized: owner={}, trust_level={}",
        wallet.owner,
        wallet.trust_level
    );

    Ok(())
}

/// Step 2: Create MerchantRegistry and TokenAllowlist PDAs for an existing wallet.
#[derive(Accounts)]
pub struct InitializeRegistries<'info> {
    /// Sardis platform authority — must sign and pay rent.
    #[account(mut)]
    pub authority: Signer<'info>,

    /// AgentWallet PDA — must already exist.
    #[account(
        constraint = {
            let w = wallet.load()?;
            w.authority == authority.key()
        } @ crate::errors::SardisError::InvalidTrustLevel,
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,

    /// MerchantRegistry PDA.
    #[account(
        init,
        payer = authority,
        space = MerchantRegistry::SIZE,
        seeds = [b"merchants", wallet.key().as_ref()],
        bump
    )]
    pub merchant_registry: AccountLoader<'info, MerchantRegistry>,

    /// TokenAllowlist PDA.
    #[account(
        init,
        payer = authority,
        space = TokenAllowlist::SIZE,
        seeds = [b"tokens", wallet.key().as_ref()],
        bump
    )]
    pub token_allowlist: AccountLoader<'info, TokenAllowlist>,

    pub system_program: Program<'info, System>,
}

pub fn handler_registries(ctx: Context<InitializeRegistries>) -> Result<()> {
    let wallet_key = ctx.accounts.wallet.key();

    let mut registry = ctx.accounts.merchant_registry.load_init()?;
    registry.wallet = wallet_key;
    registry.count = 0;
    registry._padding = [0u8; 7];

    let mut token_list = ctx.accounts.token_allowlist.load_init()?;
    token_list.wallet = wallet_key;
    token_list.count = 0;
    token_list._padding = [0u8; 7];

    msg!("Registries initialized for wallet: {}", wallet_key);

    Ok(())
}
