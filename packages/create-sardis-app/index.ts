#!/usr/bin/env node
/**
 * create-sardis-app — scaffold a minimal AI agent that uses Sardis as a money tool.
 *
 * The generated project demonstrates the four things an agent needs to spend
 * safely, with ZERO money at risk until you provide a live key + funded wallet:
 *
 *   1. get a wallet               (sardis SDK — `wallets.create`)
 *   2. set a budget / policy      (sardis SDK — `policies.apply`, natural language)
 *   3. a guarded spend            (sardis/ai-sdk provider — `sardis_check_policy` then `sardis_pay`)
 *   4. see the guard decide       (@sardis/reference — pure, offline simulator: ALLOW + DENY)
 *
 * Single-file, zero runtime dependency scaffolder: it only reads `node:fs` /
 * `node:path` / `node:process` and writes an in-source template map. Built to
 * `dist/index.js` so the published `bin` is plain Node (`npm create sardis-app`).
 */

import { mkdirSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import process from 'node:process';

const SARDIS_VERSION = '^2.0.0-rc.0';
const REFERENCE_VERSION = '^0.1.0';
const AI_VERSION = '^4.0.0';
const AI_SDK_OPENAI_VERSION = '^1.0.0';
const ZOD_VERSION = '^3.24.0';
const TYPESCRIPT_VERSION = '^5.4.0';
const TSX_VERSION = '^4.19.0';
const TYPES_NODE_VERSION = '^20.11.0';

interface ParsedArgs {
  projectName: string;
  help: boolean;
}

function parseArgs(argv: string[]): ParsedArgs {
  const args = argv.slice(2);
  let projectName = '';
  let help = false;
  for (const a of args) {
    if (a === '--help' || a === '-h') {
      help = true;
    } else if (a.startsWith('-')) {
      // Unknown flag — ignore rather than crash (agent-friendly).
      continue;
    } else if (!projectName) {
      projectName = a;
    }
  }
  return { projectName: projectName || 'my-sardis-agent', help };
}

function printHelp(): void {
  process.stdout.write(
    [
      'create-sardis-app — scaffold an AI agent that uses Sardis as a money tool',
      '',
      'Usage:',
      '  npm create sardis-app@latest [project-name]',
      '  npx create-sardis-app [project-name]',
      '',
      'Arguments:',
      '  project-name   Directory to create (default: my-sardis-agent)',
      '',
      'Flags:',
      '  -h, --help     Show this help',
      '',
      'What it scaffolds:',
      '  A minimal agent that gets a wallet, sets a budget, runs a guarded',
      '  spend, and shows the spend guard decide (ALLOW + DENY) fully offline.',
      '',
    ].join('\n') + '\n',
  );
}

/**
 * The generated project's file map (relative path -> contents).
 *
 * Imports point only at SHIPPING specifiers: `sardis`, `sardis/ai-sdk`,
 * `@sardis/reference`. No Aspendos / YULA / Fides / AGIT / memory-layer
 * content. The guard demo (`src/guard.ts`) is pure + offline and needs no key.
 */
function buildTemplate(projectName: string): Record<string, string> {
  const pkg = {
    name: projectName,
    version: '0.1.0',
    private: true,
    type: 'module',
    scripts: {
      setup: 'tsx src/setup.ts',
      guard: 'tsx src/guard.ts',
      agent: 'tsx src/agent.ts',
      dev: 'tsx src/agent.ts',
      typecheck: 'tsc --noEmit',
    },
    dependencies: {
      sardis: SARDIS_VERSION,
      '@sardis/reference': REFERENCE_VERSION,
      ai: AI_VERSION,
      '@ai-sdk/openai': AI_SDK_OPENAI_VERSION,
      zod: ZOD_VERSION,
    },
    devDependencies: {
      '@types/node': TYPES_NODE_VERSION,
      tsx: TSX_VERSION,
      typescript: TYPESCRIPT_VERSION,
    },
    engines: { node: '>=18.0.0' },
  };

  const tsconfig = {
    compilerOptions: {
      target: 'ES2022',
      module: 'ESNext',
      moduleResolution: 'bundler',
      lib: ['ES2022'],
      types: ['node'],
      strict: true,
      esModuleInterop: true,
      skipLibCheck: true,
      forceConsistentCasingInFileNames: true,
      noEmit: true,
    },
    include: ['src'],
  };

  return {
    'package.json': JSON.stringify(pkg, null, 2) + '\n',
    'tsconfig.json': JSON.stringify(tsconfig, null, 2) + '\n',

    '.env.example': [
      '# Sardis API key. Use a SANDBOX/TEST key (sk_test_...) to start.',
      '# No funds move until this is a LIVE key against a funded wallet.',
      'SARDIS_API_KEY=sk_test_replace_me',
      '',
      '# Optional: override the API base URL (defaults to the Sardis production API).',
      '# SARDIS_BASE_URL=https://api.sardis.sh',
      '',
      '# Filled in for you by `npm run setup` — the agent spends FROM this wallet.',
      'SARDIS_WALLET_ID=',
      '',
      '# Needed only for the LLM-driven agent loop (src/agent.ts).',
      'OPENAI_API_KEY=',
      '',
    ].join('\n'),

    '.gitignore': ['node_modules', 'dist', '.env', '*.log', ''].join('\n'),

    'src/setup.ts': SETUP_TS,
    'src/guard.ts': GUARD_TS,
    'src/agent.ts': AGENT_TS,
    'README.md': readme(projectName),
  };
}

const SETUP_TS = `/**
 * One-time setup: give the agent a wallet and a budget.
 *
 * Run once with \`npm run setup\`. It prints SARDIS_WALLET_ID — paste that into
 * your .env so the agent (src/agent.ts) knows which wallet to spend from.
 *
 * No money moves here: creating a wallet and applying a spending policy are
 * authority operations, not transfers.
 */
import { Sardis } from 'sardis';

const apiKey = process.env.SARDIS_API_KEY;
if (!apiKey) {
  console.error('Set SARDIS_API_KEY in .env first (copy .env.example to .env).');
  process.exit(1);
}

const sardis = new Sardis({
  apiKey,
  ...(process.env.SARDIS_BASE_URL ? { baseURL: process.env.SARDIS_BASE_URL } : {}),
});

const agentId = 'demo-agent';

async function main() {
  // 1) Give the agent a wallet (non-custodial; Sardis never holds your keys).
  const wallet = await sardis.wallets.create({ agent_id: agentId });

  // 2) Set a budget in plain English. Sardis parses + enforces it on every spend.
  await sardis.policies.apply(
    'Allow up to $50 per transaction and $200 per day, USDC only. Block gambling.',
    agentId,
  );

  console.log('Wallet created. Add this line to your .env:');
  console.log('');
  console.log('SARDIS_WALLET_ID=' + wallet.wallet_id);
  console.log('');
  console.log('Budget applied: max $50/tx, $200/day, USDC only, no gambling.');
  console.log('Next: npm run guard   (see the guard decide, offline)');
  console.log('      npm run agent    (run the guarded-spend agent)');
}

main().catch((err) => {
  console.error('Setup failed:', err);
  process.exit(1);
});
`;

const GUARD_TS = `/**
 * See the guard decide — fully offline, deterministic, ZERO money at risk.
 *
 * This is the open-core spend-decision engine from \`@sardis/reference\`: the
 * same check order the production backend uses, but pure (no network, no key,
 * no funds). It answers the only question that matters before a payment:
 * "is this agent allowed to spend this?"
 *
 * Run with \`npm run guard\`. No API key required.
 */
import { simulateSpend, money, zero, type SpendingPolicy } from '@sardis/reference';

// A budget equivalent to the one src/setup.ts applies: $50/tx, USDC only,
// gambling blocked. (Amounts are integer minor units — cents — never floats.)
const policy: SpendingPolicy = {
  policyId: 'demo-policy',
  agentId: 'demo-agent',
  trustLevel: 'high',
  limitPerTx: money(5000n, 'USD'), // $50.00
  limitTotal: money(20000n, 'USD'), // $200.00
  spentTotal: zero('USD'),
  merchantRules: [],
  allowedScopes: ['all'],
  blockedMerchantCategories: ['gambling'],
  allowedChains: [],
  allowedTokens: ['USDC'],
  allowedDestinations: [],
  blockedDestinations: [],
};

// ALLOW: $5.00 to a normal merchant — inside every limit.
const allowed = simulateSpend(policy, {
  amount: money(500n, 'USD'),
  merchantId: 'merchant_demo',
});
console.log('Spend $5.00 at merchant_demo  ->', allowed.outcome, '(' + allowed.reason + ')');

// DENY: $120.00 — over the $50 per-transaction limit.
const tooBig = simulateSpend(policy, {
  amount: money(12000n, 'USD'),
  merchantId: 'merchant_demo',
});
console.log('Spend $120.00 at merchant_demo ->', tooBig.outcome, '(' + tooBig.reason + ')');

// DENY: a blocked category, even for a tiny amount. Categories are enforced
// by MCC (merchant category code) — 7995 is Betting/Casino Gambling.
const blocked = simulateSpend(policy, {
  amount: money(100n, 'USD'),
  merchantId: 'casino_x',
  mccCode: '7995',
});
console.log('Spend $1.00 at a casino        ->', blocked.outcome, '(' + blocked.reason + ')');

console.log('');
console.log('This decision is what runs before any real transfer. No funds moved.');
`;

const AGENT_TS = `/**
 * The guarded-spend agent.
 *
 * Uses the Sardis Vercel AI SDK provider: it exposes \`sardis_check_policy\`,
 * \`sardis_pay\`, \`sardis_get_balance\` (and holds) as model tools, and ships a
 * system prompt that requires the model to CHECK POLICY before paying. The
 * Sardis backend fail-closes — so even a misbehaving model cannot overspend.
 *
 * Needs SARDIS_API_KEY + SARDIS_WALLET_ID (from \`npm run setup\`) + OPENAI_API_KEY.
 * Run with \`npm run agent\`. No funds move on a sandbox/test key.
 */
import { createSardis } from 'sardis/ai-sdk';
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';

const apiKey = process.env.SARDIS_API_KEY;
const walletId = process.env.SARDIS_WALLET_ID;
if (!apiKey || !walletId) {
  console.error('Set SARDIS_API_KEY and SARDIS_WALLET_ID in .env (run \\'npm run setup\\' first).');
  process.exit(1);
}

const sardis = createSardis({
  apiKey,
  walletId,
  ...(process.env.SARDIS_BASE_URL ? { baseURL: process.env.SARDIS_BASE_URL } : {}),
  onTransaction: (e) =>
    console.log(\`[sardis] \${e.type} \${e.success ? 'ok' : 'fail'} \${e.durationMs}ms\`),
});

async function main() {
  const res = await generateText({
    model: openai('gpt-4o'),
    tools: sardis.tools,
    system: sardis.systemPrompt,
    prompt: 'Check the policy, then pay $5.00 USDC to merchant_demo for API credits.',
    maxSteps: 5,
  });
  console.log(res.text);
}

main().catch((err) => {
  console.error('Agent failed:', err);
  process.exit(1);
});
`;

function readme(projectName: string): string {
  return `# ${projectName}

A minimal AI agent that uses **Sardis as a money tool** — your agent gets a
wallet, a budget, and a guard that decides whether it may spend.

Built with [\`create-sardis-app\`](https://www.npmjs.com/package/create-sardis-app).

## What's here

| File | What it shows |
| --- | --- |
| \`src/setup.ts\` | Give the agent a wallet + set a budget in plain English. |
| \`src/guard.ts\` | The spend guard deciding **ALLOW + DENY**, fully offline (no key, no funds). |
| \`src/agent.ts\` | A guarded-spend agent loop (Vercel AI SDK + Sardis tools). |

## No money at risk by default

\`src/guard.ts\` is pure and offline — it runs the open-core decision engine from
\`@sardis/reference\` with **zero** network, key, or funds. The live paths
(\`setup\`, \`agent\`) only move real money once you swap the sandbox key for a
**live** key against a **funded** wallet.

## Run it

\`\`\`bash
npm install
cp .env.example .env        # then add your SARDIS_API_KEY

npm run guard               # see the guard decide — no key needed
npm run setup               # create a wallet + budget, prints SARDIS_WALLET_ID
# paste SARDIS_WALLET_ID into .env, add OPENAI_API_KEY, then:
npm run agent               # run the guarded-spend agent
\`\`\`

## How the guard works

Every spend passes the same ordered checks the production backend uses
(amount → scope → category → per-tx limit → total → windows → merchant rules →
execution context). \`src/guard.ts\` mirrors that decision in pure TypeScript so
you can reason about *why* a spend is allowed or denied before any transfer.

## Links

- Docs: https://sardis.sh/docs
- SDK: https://www.npmjs.com/package/sardis
`;
}

function main(): void {
  const { projectName, help } = parseArgs(process.argv);
  if (help) {
    printHelp();
    return;
  }

  const dir = resolve(process.cwd(), projectName);

  if (existsSync(dir) && readdirSync(dir).length > 0) {
    process.stderr.write(
      `Refusing to scaffold: ${dir} already exists and is not empty.\n`,
    );
    process.exit(1);
  }

  process.stdout.write(`Creating ${projectName}...\n`);

  const template = buildTemplate(projectName);
  for (const [file, content] of Object.entries(template)) {
    const filePath = join(dir, file);
    mkdirSync(dirname(filePath), { recursive: true });
    writeFileSync(filePath, content);
    process.stdout.write(`  + ${file}\n`);
  }

  process.stdout.write(
    [
      '',
      'Done. Your agent now has a wallet, a budget, and a guard.',
      '',
      'Next steps:',
      `  cd ${projectName}`,
      '  npm install',
      '  cp .env.example .env      # add your SARDIS_API_KEY',
      '  npm run guard             # see the guard decide (no key needed)',
      '  npm run setup             # create a wallet + budget',
      '  npm run agent             # run the guarded-spend agent',
      '',
      'No funds move until you use a live key against a funded wallet.',
      'Docs: https://sardis.sh/docs',
      '',
    ].join('\n'),
  );
}

// Run only when invoked as the CLI bin — never on import (so tests can call
// buildTemplate/parseArgs without scaffolding into the test's cwd).
const invokedDirectly =
  typeof process.argv[1] === 'string' &&
  /create-sardis-app[\\/](dist[\\/])?index\.(js|mjs|cjs|ts)$/.test(process.argv[1]);
if (invokedDirectly) {
  main();
}

// Exported for tests (template materialisation without spawning a process).
export { buildTemplate, parseArgs, main };
