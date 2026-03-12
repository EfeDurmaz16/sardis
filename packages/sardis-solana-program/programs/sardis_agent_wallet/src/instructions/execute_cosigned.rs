use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, TokenAccount, Mint, TransferChecked};
use crate::state::*;
use crate::errors::SardisError;
use crate::instructions::execute_transfer::TransferExecuted;

#[derive(Accounts)]
pub struct ExecuteCosignedTransfer<'info> {
    /// Agent MPC signer.
    pub owner: Signer<'info>,

    /// Co-signer (Sardis elevated approval key).
    pub co_signer: Signer<'info>,

    /// AgentWallet PDA.
    #[account(
        mut,
        seeds = [b"sardis_wallet", owner.key().as_ref()],
        bump,
        constraint = {
            let w = wallet.load()?;
            w.owner == owner.key() && w.co_signer == co_signer.key()
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

    /// Destination token account.
    #[account(mut)]
    pub destination: Account<'info, TokenAccount>,

    /// Token mint.
    pub mint: Account<'info, Mint>,

    pub token_program: Program<'info, Token>,
}

pub fn handler(ctx: Context<ExecuteCosignedTransfer>, amount: u64) -> Result<()> {
    let registry = ctx.accounts.merchant_registry.load()?;
    let token_list = ctx.accounts.token_allowlist.load()?;
    let recipient = ctx.accounts.destination.owner;
    let mint_key = ctx.accounts.mint.key();
    let now = Clock::get()?.unix_timestamp;
    let wallet_key = ctx.accounts.wallet.key();

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

    // 5. Elevated per-transaction limit
    require!(
        amount <= wallet.cosign_limit_per_tx,
        SardisError::PerTxLimitExceeded
    );

    // 6. Reset expired time windows
    wallet.reset_expired_windows(now);

    // 7. Elevated daily limit
    require!(
        wallet.daily_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.cosign_daily_limit,
        SardisError::CosignDailyLimitExceeded
    );

    // 8-9. Weekly + Monthly limits (same as standard)
    require!(
        wallet.weekly_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.weekly_limit,
        SardisError::WeeklyLimitExceeded
    );
    require!(
        wallet.monthly_spent.checked_add(amount).unwrap_or(u64::MAX) <= wallet.monthly_limit,
        SardisError::MonthlyLimitExceeded
    );

    // 10. Total lifetime limit
    require!(
        wallet.spent_total.checked_add(amount).unwrap_or(u64::MAX) <= wallet.limit_total,
        SardisError::TotalLimitExceeded
    );

    let bump = wallet.bump;
    let owner_key = wallet.owner;

    drop(wallet);
    drop(registry);
    drop(token_list);

    // 11. CPI: SPL TransferChecked
    let seeds: &[&[u8]] = &[
        b"sardis_wallet",
        owner_key.as_ref(),
        &[bump],
    ];
    let signer_seeds = &[seeds];

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

    // 12. Update spend tracking
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
