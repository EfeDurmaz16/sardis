use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use instructions::*;

declare_id!("5shhNxoGDhGe7XotwG5usrZ21K5mZdj3q2oGZC7cYpvN");

#[program]
pub mod sardis_agent_wallet {
    use super::*;

    /// Create a new agent wallet PDA with initial policy parameters.
    /// Call initialize_registries immediately after to create merchant/token accounts.
    pub fn initialize_wallet(
        ctx: Context<InitializeWallet>,
        params: InitializeWalletParams,
    ) -> Result<()> {
        instructions::initialize_wallet::handler(ctx, params)
    }

    /// Create MerchantRegistry and TokenAllowlist PDAs for an existing wallet.
    /// Must be called after initialize_wallet (same transaction is fine).
    pub fn initialize_registries(ctx: Context<InitializeRegistries>) -> Result<()> {
        instructions::initialize_wallet::handler_registries(ctx)
    }

    /// Execute a policy-checked SPL token transfer.
    /// Only the wallet owner (agent MPC key) can call this.
    /// Enforces: pause check, token allowlist, merchant rules,
    /// per-tx/daily/weekly/monthly/total limits — then CPI transfer.
    pub fn execute_transfer(ctx: Context<ExecuteTransfer>, amount: u64) -> Result<()> {
        instructions::execute_transfer::handler(ctx, amount)
    }

    /// Execute a co-signed transfer with elevated limits.
    /// Requires both owner + co_signer signatures.
    /// Uses cosign_limit_per_tx and cosign_daily_limit instead of standard limits.
    pub fn execute_cosigned_transfer(
        ctx: Context<ExecuteCosignedTransfer>,
        amount: u64,
    ) -> Result<()> {
        instructions::execute_cosigned::handler(ctx, amount)
    }

    /// Update wallet policy parameters. Authority-only.
    pub fn update_policy(ctx: Context<UpdatePolicy>, params: UpdatePolicyParams) -> Result<()> {
        instructions::update_policy::handler(ctx, params)
    }

    /// Emergency freeze — blocks all transfers. Authority-only.
    pub fn freeze_wallet(ctx: Context<FreezeWallet>) -> Result<()> {
        instructions::freeze::freeze_handler(ctx)
    }

    /// Unfreeze a previously frozen wallet. Authority-only.
    pub fn unfreeze_wallet(ctx: Context<FreezeWallet>) -> Result<()> {
        instructions::freeze::unfreeze_handler(ctx)
    }

    /// Add a merchant rule (allow/deny + optional cap). Authority-only.
    pub fn add_merchant_rule(
        ctx: Context<ManageMerchant>,
        address: Pubkey,
        rule_type: u8,
        max_per_tx: u64,
    ) -> Result<()> {
        instructions::merchant_rules::add_merchant_handler(ctx, address, rule_type, max_per_tx)
    }

    /// Remove a merchant rule. Authority-only.
    pub fn remove_merchant_rule(ctx: Context<ManageMerchant>, address: Pubkey) -> Result<()> {
        instructions::merchant_rules::remove_merchant_handler(ctx, address)
    }

    /// Toggle merchant allowlist mode. Authority-only.
    pub fn set_allowlist_mode(ctx: Context<SetAllowlistMode>, enabled: bool) -> Result<()> {
        instructions::merchant_rules::set_allowlist_mode_handler(ctx, enabled)
    }

    /// Add a token mint to the allowlist. Authority-only.
    pub fn add_token(ctx: Context<ManageToken>, mint: Pubkey) -> Result<()> {
        instructions::token_allowlist::add_token_handler(ctx, mint)
    }

    /// Remove a token mint from the allowlist. Authority-only.
    pub fn remove_token(ctx: Context<ManageToken>, mint: Pubkey) -> Result<()> {
        instructions::token_allowlist::remove_token_handler(ctx, mint)
    }

    /// Toggle token allowlist enforcement. Authority-only.
    pub fn set_token_allowlist_enforced(
        ctx: Context<SetTokenEnforcement>,
        enforced: bool,
    ) -> Result<()> {
        instructions::token_allowlist::set_token_enforced_handler(ctx, enforced)
    }

    /// Transfer authority to a new key. Authority-only.
    pub fn update_authority(ctx: Context<UpdateAuthority>, new_authority: Pubkey) -> Result<()> {
        instructions::update_authority::handler(ctx, new_authority)
    }

    /// Close wallet and reclaim rent. Authority-only.
    /// Closes AgentWallet, MerchantRegistry, and TokenAllowlist PDAs.
    pub fn close_wallet(ctx: Context<CloseWallet>) -> Result<()> {
        instructions::close_wallet::handler(ctx)
    }
}
