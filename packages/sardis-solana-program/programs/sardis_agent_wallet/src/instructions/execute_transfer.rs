use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Mint, TransferChecked};
use crate::state::*;
use crate::errors::SardisError;

#[event]
pub struct TransferExecuted {
    pub wallet: Pubkey,
    pub owner: Pubkey,
    pub recipient: Pubkey,
    pub mint: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[derive(Accounts)]
pub struct ExecuteTransfer<'info> {
    /// Agent MPC signer — must be the wallet owner.
    pub owner: Signer<'info>,

    /// AgentWallet PDA — policy state (zero_copy).
    #[account(
        mut,
        seeds = [b"sardis_wallet", owner.key().as_ref()],
        bump,
        constraint = {
            let w = wallet.load()?;
            w.owner == owner.key()
        } @ SardisError::CosignerRequired,
    )]
    pub wallet: AccountLoader<'info, AgentWallet>,

    /// MerchantRegistry for merchant rule checks.
    #[account(
        seeds = [b"merchants", wallet.key().as_ref()],
        bump,
    )]
    pub merchant_registry: AccountLoader<'info, MerchantRegistry>,

    /// TokenAllowlist for token restriction checks.
    #[account(
        seeds = [b"tokens", wallet.key().as_ref()],
        bump,
    )]
    pub token_allowlist: AccountLoader<'info, TokenAllowlist>,

    /// Source token account (owned by wallet PDA).
    #[account(mut)]
    pub source: Account<'info, TokenAccount>,

    /// Destination token account (merchant/recipient).
    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    /// Token mint (for TransferChecked).
    pub mint: Account<'info, Mint>,

    pub token_program: Program<'info, Token>,
}

pub fn handler(ctx: Context<ExecuteTransfer>, amount: u64) -> Result<()> {
    let registry = ctx.accounts.merchant_registry.load()?;
    let token_list = ctx.accounts.token_allowlist.load()?;
    let recipient = ctx.accounts.destination.owner;
    let mint_key = ctx.accounts.mint.key();
    let now = Clock::get()?.unix_timestamp;
    let wallet_key = ctx.accounts.wallet.key();

    // Load wallet mutably for policy checks and spend tracking
    let mut wallet = ctx.accounts.wallet.load_mut()?;

    // 1. Wallet must not be paused
    require!(!wallet.is_paused(), SardisError::WalletPaused);

    // 2. Amount must be positive
    require!(amount > 0, SardisError::AmountMustBePositive);

    // 3. Token allowlist check
    if wallet.is_token_enforced() {
        require!(token_list.contains(&mint_key), SardisError::TokenNotAllowed);
    }

    // 4. Merchant deny check + allowlist check
    if let Some(idx) = registry.find(&recipient) {
        let entry = &registry.entries[idx];
        require!(entry.rule_type != RULE_DENY, SardisError::MerchantDenied);
        if entry.max_per_tx > 0 {
            require!(amount <= entry.max_per_tx, SardisError::MerchantCapExceeded);
        }
    } else if wallet.is_allowlist_mode() {
        return Err(SardisError::MerchantNotAllowed.into());
    }

    // 5. Per-transaction limit
    require!(amount <= wallet.limit_per_tx, SardisError::PerTxLimitExceeded);

    // 6. Reset expired time windows
    wallet.reset_expired_windows(now);

    // 7. Daily limit
    require!(
        wallet.daily_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.daily_limit,
        SardisError::DailyLimitExceeded
    );

    // 8. Weekly limit
    require!(
        wallet.weekly_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.weekly_limit,
        SardisError::WeeklyLimitExceeded
    );

    // 9. Monthly limit
    require!(
        wallet.monthly_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.monthly_limit,
        SardisError::MonthlyLimitExceeded
    );

    // 10. Total lifetime limit
    require!(
        wallet.spent_total.checked_add(amount).unwrap_or(u64::MAX) <= wallet.limit_total,
        SardisError::TotalLimitExceeded
    );

    // Get bump and owner for PDA signing before dropping the mutable borrow
    let bump = wallet.bump;
    let owner_key = wallet.owner;

    // 11. CPI: SPL TransferChecked — PDA signs as token authority
    let seeds: &[&[u8]] = &[
        b"sardis_wallet",
        owner_key.as_ref(),
        &[bump],
    ];
    let signer_seeds = &[seeds];

    // Drop the mutable borrow before CPI
    // We need to record spend after CPI, so save pre-CPI state
    drop(wallet);
    drop(registry);
    drop(token_list);

    token::transfer_checked(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            TransferChecked {
                from: ctx.accounts.source.to_account_info(),
                to: ctx.accounts.destination.to_account_info(),
                authority: ctx.accounts.wallet.to_account_info(),
                mint: ctx.accounts.mint.to_account_info(),
            },
            signer_seeds,
        ),
        amount,
        ctx.accounts.mint.decimals,
    )?;

    // 12. Update spend tracking — reload wallet
    let mut wallet = ctx.accounts.wallet.load_mut()?;
    wallet.record_spend(amount);

    // 13. Emit event
    emit!(TransferExecuted {
        wallet: wallet_key,
        owner: owner_key,
        recipient,
        mint: mint_key,
        amount,
        timestamp: now,
    });

    Ok(())
}
