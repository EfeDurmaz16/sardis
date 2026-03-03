/**
 * sardis init - Interactive setup wizard
 */

import type { Command } from 'commander';
import { createInterface } from 'node:readline';
import { saveConfig } from '../config.js';
import { printSuccess, printHeader, brand } from '../output.js';

function prompt(question: string, defaultVal?: string): Promise<string> {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const suffix = defaultVal ? ` (${defaultVal})` : '';
  return new Promise((resolve) => {
    rl.question(`  ${question}${suffix}: `, (answer) => {
      rl.close();
      resolve(answer.trim() || defaultVal || '');
    });
  });
}

export function registerInitCommand(program: Command): void {
  program
    .command('init')
    .description('Interactive setup wizard')
    .option('--chain <chain>', 'Default chain')
    .option('--mode <mode>', 'Mode: live or sandbox')
    .action(async (opts: { chain?: string; mode?: string }) => {
      printHeader('Sardis CLI Setup');
      console.log(brand.dim('  Configure your Sardis CLI environment\n'));

      const apiKey = await prompt('API Key (sk_...)', '');
      const chain = opts.chain || await prompt('Default chain', 'base');
      const token = await prompt('Default token', 'USDC');
      const mode = (opts.mode || await prompt('Mode (live/sandbox)', apiKey ? 'live' : 'sandbox')) as 'live' | 'sandbox';

      saveConfig({
        api_key: apiKey,
        default_chain: chain,
        default_token: token,
        mode,
      });

      console.log();
      printSuccess('Configuration saved to ~/.sardis/config.json');
      console.log();
      console.log(brand.dim('  Next steps:'));
      console.log(brand.dim('    sardis status     - Verify configuration'));
      console.log(brand.dim('    sardis demo       - Run a guided walkthrough'));
      console.log(brand.dim('    sardis pay        - Make your first payment'));
      console.log();
    });
}
