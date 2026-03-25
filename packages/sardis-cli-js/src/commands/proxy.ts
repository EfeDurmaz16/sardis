/**
 * sardis proxy — MPP proxy management commands
 *
 * sardis proxy init    — Scaffold proxy config for a new API
 * sardis proxy deploy  — Deploy proxy to Cloudflare Workers
 */

import type { Command } from 'commander';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import {
  printHeader,
  printKeyValue,
  printSuccess,
  printError,
  printInfo,
  brand,
} from '../output.js';

function prompt(question: string, defaultVal?: string): Promise<string> {
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  const suffix = defaultVal ? ` (${defaultVal})` : '';
  return new Promise((resolve) => {
    rl.question(`  ${question}${suffix}: `, (answer) => {
      rl.close();
      resolve(answer.trim() || defaultVal || '');
    });
  });
}

export function registerProxyCommand(program: Command): void {
  const proxy = program
    .command('proxy')
    .description('Manage MPP payment-gating proxies');

  // ── sardis proxy init ─────────────────────────────────────────────
  proxy
    .command('init')
    .description('Scaffold an MPP proxy configuration for a new API')
    .option('--dir <path>', 'Output directory', '.')
    .option('--origin <url>', 'Origin API URL')
    .action(async (opts: { dir: string; origin?: string }) => {
      printHeader('Sardis MPP Proxy Setup');
      console.log(
        brand.dim(
          '  Make your API earn money from AI agents in minutes\n',
        ),
      );

      const origin =
        opts.origin || (await prompt('Origin API URL', 'https://api.example.com'));
      const price = await prompt('Default price per request (USD)', '0.01');
      const recipient = await prompt('Recipient wallet address (0x...)', '');
      const name = await prompt('Worker name', 'my-paid-api');

      const dir = opts.dir;
      const srcDir = join(dir, 'src');

      if (!existsSync(srcDir)) {
        mkdirSync(srcDir, { recursive: true });
      }

      // Generate wrangler.toml
      const wranglerToml = `#:schema node_modules/wrangler/config-schema.json
name = "${name}"
main = "src/index.ts"
compatibility_date = "2025-04-01"

[vars]
ORIGIN_URL = "${origin}"
PROTECTED_ROUTES = '[{"path":"/*","priceUsd":"${price}","description":"API request"}]'

# Set secrets via: wrangler secret put <NAME>
# Required: MPP_SECRET_KEY, PAY_TO, SARDIS_API_KEY

[observability]
enabled = true
`;

      // Generate minimal index.ts that re-exports sardis proxy
      const indexTs = `/**
 * ${name} — MPP payment-gated API proxy
 *
 * Powered by @sardis/mpp-proxy
 * Docs: https://sardis.sh/docs/mpp-proxy
 */

// Re-export the Sardis MPP Proxy worker.
// All configuration comes from wrangler.toml and Worker secrets.
export { default } from '@sardis/mpp-proxy';
`;

      // Generate package.json
      const packageJson = {
        name,
        version: '0.1.0',
        private: true,
        type: 'module',
        scripts: {
          dev: 'wrangler dev',
          deploy: 'wrangler deploy --minify',
          'setup-secrets': [
            'echo "Setting up Worker secrets..."',
            'wrangler secret put MPP_SECRET_KEY',
            'wrangler secret put PAY_TO',
            'wrangler secret put SARDIS_API_KEY',
          ].join(' && '),
        },
        dependencies: {
          '@sardis/mpp-proxy': '^0.1.0',
        },
        devDependencies: {
          wrangler: '^3.99.0',
          '@cloudflare/workers-types': '^4.20241230.0',
          typescript: '^5.5.0',
        },
      };

      // Generate tsconfig.json
      const tsconfig = {
        compilerOptions: {
          target: 'ES2022',
          module: 'ES2022',
          moduleResolution: 'bundler',
          lib: ['ES2022'],
          types: ['@cloudflare/workers-types'],
          strict: true,
          skipLibCheck: true,
          outDir: 'dist',
          rootDir: 'src',
        },
        include: ['src/**/*.ts'],
        exclude: ['node_modules', 'dist'],
      };

      // Write files
      writeFileSync(join(dir, 'wrangler.toml'), wranglerToml);
      writeFileSync(join(dir, 'package.json'), JSON.stringify(packageJson, null, 2) + '\n');
      writeFileSync(join(dir, 'tsconfig.json'), JSON.stringify(tsconfig, null, 2) + '\n');
      writeFileSync(join(srcDir, 'index.ts'), indexTs);

      console.log();
      printSuccess('Proxy scaffolded successfully');
      console.log();
      printKeyValue([
        ['Origin', origin],
        ['Price', `$${price} per request`],
        ['Recipient', recipient || '(set via wrangler secret put PAY_TO)'],
        ['Directory', dir],
      ]);

      console.log();
      console.log(brand.dim('  Next steps:'));
      console.log(brand.dim('    1. cd ' + dir));
      console.log(brand.dim('    2. npm install'));
      console.log(brand.dim('    3. wrangler secret put MPP_SECRET_KEY'));
      console.log(brand.dim('    4. wrangler secret put PAY_TO'));
      console.log(brand.dim('    5. wrangler secret put SARDIS_API_KEY'));
      console.log(brand.dim('    6. npm run deploy'));
      console.log();
      printInfo(
        '  Docs: https://sardis.sh/docs/mpp-proxy',
      );
      console.log();
    });

  // ── sardis proxy deploy ───────────────────────────────────────────
  proxy
    .command('deploy')
    .description('Deploy MPP proxy to Cloudflare Workers')
    .option('--dir <path>', 'Project directory', '.')
    .option('--dry-run', 'Show what would be deployed without deploying')
    .action(async (opts: { dir: string; dryRun?: boolean }) => {
      printHeader('Deploy MPP Proxy');

      const wranglerPath = join(opts.dir, 'wrangler.toml');
      if (!existsSync(wranglerPath)) {
        printError(
          'No wrangler.toml found. Run `sardis proxy init` first.',
        );
        process.exitCode = 1;
        return;
      }

      if (opts.dryRun) {
        console.log(brand.dim('  [dry-run] Would deploy with:'));
        console.log(brand.dim(`    wrangler deploy --minify --config ${wranglerPath}`));
        console.log();
        printInfo(
          '  Remove --dry-run to deploy for real.',
        );
        return;
      }

      console.log(brand.dim('  Deploying to Cloudflare Workers...\n'));
      console.log(brand.dim('  Run the following command:'));
      console.log();
      console.log(
        `  ${brand.bold('npx wrangler deploy --minify')}`,
      );
      console.log();
      console.log(
        brand.dim(
          '  Ensure you have set the required secrets:',
        ),
      );
      console.log(brand.dim('    wrangler secret put MPP_SECRET_KEY'));
      console.log(brand.dim('    wrangler secret put PAY_TO'));
      console.log(brand.dim('    wrangler secret put SARDIS_API_KEY'));
      console.log();
    });
}
