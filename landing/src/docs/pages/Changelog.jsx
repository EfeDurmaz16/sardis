import { cn } from '@/lib/utils';

const releases = [
  {
    version: '0.9.3',
    date: '2026-02-25',
    tag: 'latest',
    changes: [
      {
        type: 'added',
        items: [
          'Investor-facing competitive positioning brief updated for deterministic policy + approval + audit-trail narrative',
          'Landing hero now highlights PAN-lane quorum, ASA fail-closed posture, and wallet-aware A2A trust routing',
          'Dashboard runtime posture cards added for checkout controls, ASA behavior, and multi-agent trust visibility',
        ]
      },
      {
        type: 'improved',
        items: [
          'MCP tool count references aligned to current verified audit baseline (52 tools)',
          'Enterprise and main landing framework-integration copy updated for evidence consistency',
          'Approvals page copy aligned with 4-eyes reviewer enforcement posture',
        ]
      },
    ]
  },
  {
    version: '0.9.2',
    date: '2026-02-25',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Secure checkout approval quorum controls with configurable global/PAN-specific minimum approvals',
          'Secure checkout distinct reviewer (4-eyes) validation for high-risk PAN execution lane',
          'Lithic ASA runtime security policy endpoint: GET /api/v2/cards/asa/security-policy',
          'A2A wallet-aware peer directory fields and trusted broadcast target list in trust discovery API',
          'New ASA hardening tests in sardis-cards package and expanded payment hardening gate coverage',
        ]
      },
      {
        type: 'security',
        items: [
          'Production-default fail-closed behavior for ASA card lookup errors',
          'Production-default fail-closed behavior for ASA subscription matcher errors',
          'Checkout PAN approvals now enforce quorum and can enforce distinct reviewers via runtime policy',
        ]
      },
      {
        type: 'improved',
        items: [
          'Payment hardening pre-prod guide updated with checkout quorum, ASA fail-closed, and wallet-aware A2A directory checks',
          'Runtime security policy visibility expanded across checkout, ASA, and A2A control-plane surfaces',
        ]
      },
    ]
  },
  {
    version: '0.9.1',
    date: '2026-02-25',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'A2A trust repository with admin relation upsert/delete and production fail-closed migration posture',
          'A2A trusted peer discovery API with trusted/untrusted filtering and deterministic trust table hashing',
          'A2A trust mutation audit feed with compliance proof links for verifiable evidence export',
          'A2A runtime security-policy endpoint exposing signature, trust-table, and approval guardrail posture',
          'Approval quorum controls for trust relation mutations with distinct reviewer requirements',
        ]
      },
      {
        type: 'security',
        items: [
          'Trust relation mutations now require approved 4-eyes tokens with org/action/metadata binding checks',
          'Goal-drift review/block thresholds added to on-chain payment execution with deterministic deny path',
          'Payment hardening release gate expanded for trust, quorum, and goal-drift controls',
        ]
      },
      {
        type: 'improved',
        items: [
          'Landing and roadmap documentation aligned with zero-trust control plane rollout',
          'Operational controls clarified for approval escalation and auditable mutation history',
        ]
      },
    ]
  },
  {
    version: '0.9.0',
    date: '2026-02-20',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Stripe Treasury provider: financial accounts, balances, outbound payments, Treasury-to-Issuing fund transfers, and webhook handling',
          'Stripe Issuing provider: virtual card lifecycle (create/update/freeze/terminate), spending limits, real-time authorization webhooks, and CardProvider ABC implementation',
          'Coinbase Onramp provider: 0% fee USDC on-ramp with session-based checkout flow and smart RampRouter with automatic provider selection',
          'Sub-ledger fiat account manager: per-agent fiat balance tracking, deposits, withdrawals, card funding/settlement, and Treasury reconciliation',
          'End-to-end FiatPaymentOrchestrator: card payments, fiat deposits, withdrawals, and crypto-to-card flows with automatic rollback on failure',
          'Stripe webhook router: unified ingestion endpoint for Treasury and Issuing events with signature verification and event-type routing',
          'Ledger batch and audit migration (021): ledger_batches, ledger_batch_entries, and ledger_audit_snapshots tables with 7 indexes',
          'OpenClaw skill package (sardis-openclaw): SKILL.md manifest for agent framework integration with payment, policy, and card tools',
          'sardis-openai package: OpenAI function-calling tools with strict JSON schema mode for payment, balance, and policy operations',
          'Gemini function declarations (sardis-adk): Google ADK adapter with FunctionDeclaration format for all Sardis payment tools',
          'MCP fiat tools: 5 new tools (fiat_deposit, fiat_withdraw, fiat_card_payment, fiat_balance, fiat_crypto_to_card) added to sardis-mcp-server',
          'ChatGPT Actions OpenAPI spec: /openapi-actions.yaml with 8 endpoints for GPT plugin and Actions integration',
        ]
      },
      {
        type: 'improved',
        items: [
          'RampRouter now supports multi-provider fallback chains with smart routing (USDC → Coinbase, others → Bridge)',
          'sardis-core __init__.py exports updated with all new fiat module types (StripeTreasuryProvider, SubLedgerManager, FiatPaymentOrchestrator, etc.)',
          'SubLedgerTxType enum extended with CARD_SETTLEMENT for distinct card settlement tracking',
        ]
      },
      {
        type: 'security',
        items: [
          'Stripe webhook signature verification (HMAC-SHA256) enforced on all Treasury and Issuing event ingestion',
          'FiatPaymentOrchestrator implements automatic rollback: failed card funding reverses sub-ledger withdrawal, failed off-ramp refunds sub-ledger debit',
        ]
      },
    ]
  },
  {
    version: '0.8.10',
    date: '2026-02-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Canonical cross-rail ledger state machine: fiat ACH + fiat card + stablecoin tx/userop normalized into a single journey model',
          'Migration 019: canonical_ledger_journeys, canonical_ledger_events, reconciliation_breaks, manual_review_queue',
          'Operator reconciliation APIs: journeys, drift, return-code views, manual-review resolve, audit evidence export',
          'Dashboard reconciliation view with drift/returns/manual-review operations and JSON evidence export',
          'Reconciliation load/chaos tests and release checks for canonical state handling',
        ]
      },
      {
        type: 'improved',
        items: [
          'Out-of-order and duplicate event handling now preserves terminal states with exactly-once provider event dedupe',
          'Scheduler guard adds stale-processing review automation for unresolved payment journeys',
        ]
      },
      {
        type: 'security',
        items: [
          'Replay-protected webhook ingestion now feeds canonical reconciliation audit records across rails',
          'High-risk ACH return code R29 now auto-queues critical manual review in operator workflow',
        ]
      },
    ]
  },
  {
    version: '0.8.9',
    date: '2026-02-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Fiat-first treasury API surface: account sync, financial account listing, external bank linking, micro-deposit verification, ACH fund/withdraw, payment status, balances',
          'Treasury data model + migration 018: financial accounts, external bank accounts, ACH payments/events, balance snapshots, reservations, webhook event store',
          'Lithic treasury adapter for financial accounts, ACH payments, and sandbox simulation helpers',
          'Python SDK and TypeScript SDK treasury resources with typed request/response models',
          'MCP treasury tool expansion for USD-first ACH operational flows',
        ]
      },
      {
        type: 'improved',
        items: [
          'Cards funding route now defaults to fiat_first with stablecoin fallback behind explicit configuration',
          'Landing/docs updated with USD-first launch posture and real /api/v2/treasury endpoint references',
        ]
      },
      {
        type: 'security',
        items: [
          'Replay-protected Lithic payment webhook ingestion with mandatory signature verification in production',
          'ACH return-code controls: R02/R03/R29 auto-pause, R01/R09 retry orchestration, plus org velocity and daily cap enforcement',
        ]
      },
    ]
  },
  {
    version: '0.8.8',
    date: '2026-02-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'ERC-4337 contracts: SardisSmartAccount, SardisSmartAccountFactory, SardisVerifyingPaymaster',
          'Base-first deploy script: DeployERC4337BaseSepolia.s.sol plus deployment artifact template',
          'Wallet model/API/SDK/MCP parity for account_type=mpc_v1|erc4337_v2',
          'Wallet transfer response metadata: execution_path and user_op_hash',
          'Fail-closed ERC-4337 runtime path with Pimlico bundler/paymaster configuration gates',
          'Wallet upgrade endpoint: POST /api/v2/wallets/{id}/upgrade-smart-account',
          'DB migration 017 for ERC-4337 wallet metadata fields',
        ]
      },
      {
        type: 'improved',
        items: [
          'Docs truth alignment for non-custodial language: stablecoin live-MPC posture vs fiat partner rails',
          'Roadmap and FAQ updated to reflect Base Sepolia preview lane for gasless wallets',
        ]
      },
      {
        type: 'security',
        items: [
          'ERC-4337 wallets now fail closed when bundler/paymaster config is missing',
          'Chain allowlist gate for ERC-4337 execution to prevent accidental unsupported-chain routing',
        ]
      },
    ]
  },
  {
    version: '0.8.7',
    date: '2026-02-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'ERC-4337 gasless smart wallet architecture design (paymaster + bundler + Pimlico)',
          'PostgreSQL persistence for card services: conversions, wallet mappings, offramp transactions',
          'PostgreSQL persistence for ledger engine with NUMERIC(38,18) full-precision entries',
          'Alembic migration 015: 5 new tables (card_conversions, card_wallet_mappings, offramp_transactions, processed_webhook_events, ledger_entries_v2)',
          'Time-based spending policies documentation page with timezone handling and DST support',
          'Merchant category codes (MCC) documentation page with 18 categories and allowlist/blocklist modes',
          'Combined limit strategy documentation with per-merchant overrides and recommended profiles',
          'Landing page: gasless smart wallets section with 4-step flow and competitive positioning',
          'Stablecoin-only token allowlist design (on-chain EVM enforcement)',
          'Recurring payments engine: subscription registry, pre-billing processor, owner notifications',
          'Subscription-aware ASA handler: known recurring charges auto-approve via merchant+amount matching',
          'Alembic migration 016: subscriptions, billing_events, subscription_notifications tables',
        ]
      },
      {
        type: 'security',
        items: [
          'Onramper webhook verification now enforces timestamp validation with a 5-minute replay window',
          'Webhook signature verification accepts canonical signed payloads and legacy signatures with required timestamp headers',
        ]
      },
      {
        type: 'improved',
        items: [
          'Launch documentation and release materials synchronized for MCP tool count, package counts, and quickstart parity',
          'llms.txt expanded with time-based policies, MCC codes, combined limits, and smart wallet sections',
        ]
      },
    ]
  },
  {
    version: '0.8.6',
    date: '2026-02-13',
    tag: '',
    changes: [
      {
        type: 'improved',
        items: [
          'SardisClient convenience wrapper added to reduce SDK onboarding friction',
          'Landing/docs claims synchronized around package count (19), chain count (5), and validated MCP tool registry',
          'README and launch materials updated with validated link/badge checks',
          'Landing production deployment completed and aliased to www.sardis.sh',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Python SDK version constant aligned with package metadata (0.3.3 parity)',
          'Release-readiness script now degrades gracefully when optional design-partner checklist file is absent',
          'Launch documentation now records URL/badge validation outcomes and npm curl 403 caveat',
        ]
      },
    ]
  },
  {
    version: '0.8.5',
    date: '2026-02-11',
    tag: '',
    changes: [
      {
        type: 'security',
        items: [
          'Travel Rule (FATF R.16) compliance module for cross-border transfers exceeding $3,000',
          'Lithic ASA real-time authorization handler with MCC blocking and velocity checks',
          'Expanded high-risk MCC blocklist: gambling (7800-7802), cash advances (6010-6011), stored value (6540), wire transfers (4829), escorts (7273)',
          'Replaced placeholder country list with 16 real OFAC/FATF high-risk country codes (KP, IR, SY, CU, etc.)',
          'Expanded disposable email domain detection from 6 to 40 providers',
          'Co-sign threshold limits added to SardisAgentWallet.sol smart contract',
          'Factory owner secured with OpenZeppelin TimelockController (48-hour delay)',
          'Gas fee now included in policy evaluation (total cost = amount + estimated gas)',
          'Velocity checks at policy layer: per-transaction, daily, weekly, and monthly limits',
        ]
      },
      {
        type: 'added',
        items: [
          'PostgreSQL persistence for spending policy state (replaces in-memory)',
          'PostgreSQL persistence for SAR storage, identity registry, and ledger engine',
          'Redis-backed velocity monitoring with atomic increment/check operations',
          'KYB (Know Your Business) verification via Persona for organizational onboarding',
          'Centralized price oracle for gas cost estimation across all supported chains',
          'Per-organization rate limiting with configurable tier overrides',
          'Async PostgreSQL support for ledger receipts and reconciliation',
        ]
      },
      {
        type: 'improved',
        items: [
          'Refactored API main.py into focused modules (1392 to 683 lines: lifespan, health, OpenAPI, card adapter)',
          'Consolidated duplicate Turnkey MPC clients into single canonical client with correct P-256 stamp format',
          'Resolved dual-SDK confusion with unified sardis package as single entry point',
        ]
      },
    ]
  },
  {
    version: '0.8.4',
    date: '2026-02-08',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Published all 15 Python packages to PyPI (sardis meta-package + sardis-sdk, sardis-core, sardis-protocol, sardis-chain, sardis-ledger, sardis-compliance, sardis-api, sardis-wallet, sardis-cards, sardis-cli, sardis-checkout, sardis-ramp, sardis-ucp, sardis-a2a)',
          'Published all 4 npm packages (@sardis/sdk, @sardis/mcp-server, @sardis/ai-sdk, @sardis/ramp)',
          'SDK installation section on landing page with early access messaging and package links',
          'Vercel SPA routing fix for /docs and all sub-routes',
          'Human-in-the-Loop approval queue — payments above policy threshold pause for human sign-off before execution',
          'Goal drift detection — intent scope vs. payment destination mismatch blocking with configurable drift score threshold',
          'Public staging API deployed to GCP Cloud Run with Neon Postgres + Upstash Redis',
          'Admin dashboard deployed to Vercel at app.sardis.sh with live API integration',
          'API key bootstrap script for staging environments',
        ]
      },
      {
        type: 'security',
        items: [
          'Comprehensive security audit: 54 fixes across 8 batches covering auth, crypto, input validation, SQL injection, rate limiting, CORS, webhook signatures, AI prompt injection, and JWT',
          'JWT authentication migrated from custom HMAC to PyJWT with proper claim validation',
          'Identity registry now fail-closed in production and staging environments',
          'Anonymous access restricted to loopback addresses only',
        ]
      },
      {
        type: 'improved',
        items: [
          'TypeScript strict mode fixes for MCP server rate limiter and onramper quote sorting',
          '.gitignore updated to exclude Foundry build artifacts (contracts/out/, contracts/cache/)',
          'All 649 Python tests and 91 Solidity tests passing after security hardening',
        ]
      },
    ]
  },
  {
    version: '0.8.3',
    date: '2026-02-08',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Cloud Run staging deployment automation script with health checks and post-deploy bootstrap instructions',
          'AWS App Runner staging deployment automation script (ECR build/push + service create/update)',
          'Unified deployment env templates for GCP and AWS staging',
          'Cloud deployment + frontend integration runbook for /demo live mode',
        ]
      },
      {
        type: 'improved',
        items: [
          'Demo live-mode auth UX now shows explicit server-side password setup guidance',
          'Demo transaction history now persists across browser refreshes (local storage)',
          'Deployment docs now map directly to repo scripts and required env vars',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Landing-local Vercel config simplified to avoid route/header config conflicts in local `vercel dev` sessions',
          'Roadmap/docs alignment updated with current staging hardening milestones',
        ]
      },
    ]
  },
  {
    version: '0.8.2',
    date: '2026-02-06',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'JS bootstrap preflight script (`bootstrap:js`) with DNS/registry checks before install',
          'Optional live-chain conformance gate (`check:live-chain`) for Turnkey + testnet verification',
          'Release scripts for strict/degraded readiness flows in constrained local environments',
        ]
      },
      {
        type: 'improved',
        items: [
          'Protocol conformance lane now isolates root and UCP package scopes to avoid pytest import collisions',
          'Conformance report generator now supports fallback parsing when pytest JSON plugin is unavailable',
          'Start-to-end release runbook updated for reproducible MCP + SDK validation workflow',
        ]
      },
      {
        type: 'fixed',
        items: [
          'False skip/noise in protocol conformance by excluding integration/e2e test trees from the conformance marker lane',
          'Fragile pass/fail parsing in Python readiness script replaced with summary-based extraction',
        ]
      },
    ]
  },
  {
    version: '0.8.1',
    date: '2026-02-06',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Protocol source map with canonical AP2/TAP/UCP/x402 references and test mappings',
          'AP2 PaymentMandate visibility signals: ai_agent_presence and transaction_modality',
          'TAP linked-object signature-base helper for agenticConsumer and agenticPaymentContainer',
          'New negative tests for TAP algorithm validation and linked-object signature checks',
        ]
      },
      {
        type: 'improved',
        items: [
          'AP2 verifier now enforces explicit agent-presence and modality semantics',
          'TAP header validation now enforces message signature algorithm allowlist',
          'Start-to-end engineering flow documentation now includes protocol source governance',
        ]
      },
      {
        type: 'security',
        items: [
          'Fail-closed behavior for invalid TAP algorithms in headers and signed objects',
          'Stronger protocol-level guardrails before payment execution',
        ]
      },
    ]
  },
  {
    version: '0.8.0',
    date: '2026-02-03',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Human Approval Workflows - Full create/approve/deny/expire/cancel lifecycle',
          'ApprovalRepository with PostgreSQL persistence',
          'ApprovalService with business logic and webhook notifications',
          'Approvals API router with REST endpoints (/api/v2/approvals)',
          'Background Job Scheduler - APScheduler integration with FastAPI lifespan',
          'Scheduled jobs: approval expiration, hold cleanup, spending limit reset',
          'Alembic database migration framework with 6 versioned migrations',
          'Wallet freeze/unfreeze capability with transaction blocking',
          'Velocity limit checks for off-ramp (daily/weekly/monthly)',
          'MCC (Merchant Category Code) lookup service',
          'EIP-2771 meta-transaction support for gasless transactions',
          'Batch transfer API endpoint',
          'SAR (Suspicious Activity Report) generation',
        ]
      },
      {
        type: 'improved',
        items: [
          'Prometheus metrics endpoint for monitoring',
          'Sentry integration for error tracking',
          'Structured logging with correlation IDs',
          'CI/CD deployment workflow with staging/production gates',
          'GitHub Actions: mypy type checking, 70% coverage enforcement',
          'Dependabot configuration for automated security updates',
        ]
      },
      {
        type: 'fixed',
        items: [
          'npm audit vulnerabilities across all packages',
          'Updated hono to latest secure version',
          'Updated esbuild to fix CVE vulnerabilities',
          'SDK tests updated for new RetryConfig API',
          'Deprecated regex parameter replaced with pattern in routers',
        ]
      },
      {
        type: 'security',
        items: [
          'HMAC webhook verification for card routes',
          'Feature flags for card API routes',
          'Health monitoring workflow for E2E card lifecycle',
        ]
      },
    ]
  },
  {
    version: '0.7.0',
    date: '2026-02-02',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Invoices API - Full CRUD endpoints for merchant invoice management',
          'Fireblocks MPC signer - Institutional-grade vault account creation and transaction signing',
          'PostgreSQL-backed mandate store - Mandates now persist across restarts',
          'PostgreSQL-backed checkout sessions - Checkout state no longer in-memory',
          'PostgreSQL-backed KYC verification storage with DB lookup fallback',
          'ABI revert reason decoding - Human-readable Solidity error messages',
          'Dashboard invoices page wired to real API (replaces mock data)',
        ]
      },
      {
        type: 'improved',
        items: [
          'Auth context wired into all API routes (agents, webhooks, marketplace)',
          'Webhook secret rotation now persisted to database',
          'sardis-ai-sdk resolved as pnpm workspace dependency',
          'ChainId, TokenConfig, GasConfig exports fixed in sardis-chain',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Critical NameError: turnkey_client referenced before assignment in main.py',
          'Database schema idempotency: consolidated ALTER TABLE into CREATE TABLE',
          'Hardcoded secret removed from .env.example',
          'Solidity contract file permissions (600 → 644)',
          'Python 3.13 compatibility: pinned asyncpg>=0.30 and fastapi>=0.115',
        ]
      },
      {
        type: 'security',
        items: [
          'API routes now enforce authentication via require_api_key dependency',
          'Marketplace endpoints require X-Agent-Id header instead of hardcoded demo values',
        ]
      },
    ]
  },
  {
    version: '0.6.0',
    date: '2026-01-27',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Fiat Rails - Bank on-ramp and off-ramp support via Bridge and Onramper',
          'Virtual Cards - Lithic integration for instant card issuance',
          'Unified Balance introduced (later updated to quote-based cross-rail conversion, no fixed 1:1 assumption)',
          'KYC/AML Integration - Persona verification and Elliptic sanctions screening',
          'sardis-ramp-js package for JavaScript/TypeScript fiat operations',
          'sardis-cards package for virtual card management',
          '8 new MCP fiat tools (sardis_fund_wallet, sardis_withdraw_to_bank, etc.)',
          'Bank account linking and verification',
        ]
      },
      {
        type: 'improved',
        items: [
          'MCP Server expanded to 40+ tools with fiat and card support',
          'TypeScript SDK v0.2.0 with fiat.fund(), fiat.withdraw(), cards.create()',
          'Python SDK with full fiat rails and unified balance support',
          'Policy Engine now validates across crypto, fiat, and card transactions',
          'Documentation updated with fiat rails guides',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Wallet balance now shows unified USDC + USD total',
          'Rate limiter now tracks spend across all payment rails',
          'KYC status properly cached to reduce API calls',
        ]
      },
    ]
  },
  {
    version: '0.5.0',
    date: '2026-01-24',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'UCP (Universal Commerce Protocol) - Standardized checkout flows for AI agents',
          'A2A (Agent-to-Agent) protocol - Multi-agent communication and discovery',
          'sardis-ucp package with checkout, order, and fulfillment capabilities',
          'sardis-a2a package with agent cards and message handling',
          'MCP Server expanded from 4 to 36+ tools',
          'AP2 mandate adapter for UCP-AP2 interoperability',
          'Agent discovery service with TTL caching',
          'TAP (Trust Anchor Protocol) identity verification',
        ]
      },
      {
        type: 'improved',
        items: [
          'TypeScript SDK now includes UCP, A2A, and Agents resources',
          'Python SDK with full UCP and A2A support',
          'MCP Server modularized into tool categories',
          'Policy engine with natural language support',
          'Documentation updated with protocol guides',
        ]
      },
      {
        type: 'fixed',
        items: [
          'SDK method naming standardized (get() instead of getById())',
          'MCP policy configuration now uses environment variables',
          'Rate limiter persistence with Redis support',
        ]
      },
    ]
  },
  {
    version: '0.4.0',
    date: '2026-01-23',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Demo agent showcasing policy-enforced autonomous payments',
          'Real on-chain ERC20 balance queries in wallet API',
          'pnpm workspace configuration for monorepo',
          'Database health check in API server',
        ]
      },
      {
        type: 'fixed',
        items: [
          'TypeScript SDK build error from duplicate exports in openai.ts',
          'MCP Server wallet endpoints now use correct /api/v2 prefix',
          'Python SDK Wallet model alias mismatch with API',
          'Demo agent now uses correct wallet creation API',
        ]
      },
      {
        type: 'improved',
        items: [
          'Wallet balance endpoint now queries real chain via ChainExecutor',
          'MCP Server no longer requires unused SDK dependency',
          'API health endpoint returns proper component status',
        ]
      },
    ]
  },
  {
    version: '0.3.0',
    date: '2026-01-20',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Real API integration in MCP server (no more mock data)',
          'LangChain.js integration for TypeScript SDK',
          'OpenAI function calling integration for both SDKs',
          'Environment variable configuration for MCP server',
          'Comprehensive FAQ, Blog, and Changelog documentation pages',
        ]
      },
      {
        type: 'improved',
        items: [
          'Vercel AI SDK integration with proper mandate signing',
          'Python SDK LangChain tool with async execution',
          'LlamaIndex integration with full payment flow',
          'Error handling with policy violation detection',
        ]
      },
      {
        type: 'fixed',
        items: [
          'MCP server now connects to real Sardis API',
          'Python SDK properly handles async event loops',
          'TypeScript SDK exports all integration modules',
        ]
      },
    ]
  },
  {
    version: '0.2.0',
    date: '2026-01-02',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Python SDK with LangChain and LlamaIndex integrations',
          'TypeScript SDK with Vercel AI integration',
          'MCP server for Claude Desktop integration',
          'Policy engine with vendor allowlists',
          'Spending limits (per-transaction and daily)',
        ]
      },
      {
        type: 'improved',
        items: [
          'Documentation with Lydian Protocol design system',
          'API response types for better TypeScript support',
        ]
      },
    ]
  },
  {
    version: '0.1.0',
    date: '2025-12-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Initial release of Sardis SDK',
          'MPC wallet integration via Turnkey',
          'Basic mandate execution pipeline',
          'USDC support on Base Sepolia testnet',
          'Ledger with Merkle tree audit anchoring',
          'Health and status endpoints',
        ]
      },
    ]
  },
];

const changeTypeConfig = {
  added: {
    label: 'Added',
    color: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500',
    icon: '+',
  },
  improved: {
    label: 'Improved',
    color: 'bg-blue-500/10 border-blue-500/30 text-blue-500',
    icon: '^',
  },
  fixed: {
    label: 'Fixed',
    color: 'bg-amber-500/10 border-amber-500/30 text-amber-500',
    icon: '*',
  },
  deprecated: {
    label: 'Deprecated',
    color: 'bg-red-500/10 border-red-500/30 text-red-500',
    icon: '-',
  },
  security: {
    label: 'Security',
    color: 'bg-purple-500/10 border-purple-500/30 text-purple-500',
    icon: '!',
  },
};

function ReleaseSection({ release }) {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <section className="relative pl-8 pb-14 border-l border-border last:pb-0">
      {/* Timeline dot */}
      <div className={cn(
        "absolute -left-2 w-4 h-4 rounded-full border-2 border-border bg-background",
        release.tag === 'latest' && "border-[var(--sardis-orange)] bg-[var(--sardis-orange)]"
      )} />

      {/* Version header */}
      <div className="mb-5">
        <div className="flex items-center gap-3 mb-2">
          <h3 className="text-xl font-bold font-display">v{release.version}</h3>
          {release.tag && (
            <span className="px-2 py-0.5 text-xs font-mono bg-[var(--sardis-orange)] text-white rounded">
              {release.tag.toUpperCase()}
            </span>
          )}
        </div>
        <p className="text-sm text-muted-foreground font-mono">
          {formatDate(release.date)}
        </p>
      </div>

      {/* Changes */}
      <div className="space-y-5">
        {release.changes.map((group, idx) => {
          const config = changeTypeConfig[group.type];
          return (
            <div key={idx}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 text-xs font-mono border rounded ${config.color}`}>
                  {config.icon} {config.label.toUpperCase()}
                </span>
              </div>
              <ul className="space-y-2">
                {group.items.map((item, itemIdx) => (
                  <li key={itemIdx} className="text-sm text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="text-[var(--sardis-orange)] mt-1">-</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function DocsChangelog() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-10">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            CHANGELOG
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Changelog</h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Release history and version updates for Sardis SDK and API.
        </p>
      </div>

      {/* Version format guide */}
      <div className="not-prose mb-10 p-5 rounded-lg bg-card/50 shadow-sm">
        <p className="text-sm text-muted-foreground font-mono">
          Version format: <span className="text-foreground">MAJOR.MINOR.PATCH</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
          We follow semantic versioning. Breaking changes increment MAJOR,
          new features increment MINOR, and bug fixes increment PATCH.
        </p>
      </div>

      {/* Releases timeline */}
      <div className="not-prose">
        {releases.map((release, idx) => (
          <ReleaseSection key={idx} release={release} />
        ))}
      </div>

      {/* Subscribe section */}
      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-12">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Stay Updated</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Follow our GitHub releases for the latest updates.
        </p>
        <a
          href="https://github.com/EfeDurmaz16/sardis/releases"
          className="inline-flex items-center gap-2 px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
        >
          View on GitHub
        </a>
      </section>
    </article>
  );
}
