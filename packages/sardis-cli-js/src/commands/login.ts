/**
 * sardis login / logout - Credential management
 */

import type { Command } from 'commander';
import { createInterface } from 'node:readline';
import { saveConfig, clearCredentials } from '../config.js';
import { printSuccess, printError, printHeader, brand } from '../output.js';

function prompt(question: string): Promise<string> {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

export function registerLoginCommand(program: Command): void {
  program
    .command('login')
    .description('Set API key for authentication')
    .option('--key <api-key>', 'API key (or enter interactively)')
    .action(async (opts: { key?: string }) => {
      let apiKey = opts.key;

      if (!apiKey) {
        printHeader('Sardis Login');
        console.log(brand.dim('  Get your API key at https://sardis.sh/dashboard\n'));
        apiKey = await prompt('  API Key: ');
      }

      if (!apiKey) {
        printError('No API key provided');
        process.exitCode = 1;
        return;
      }

      if (!apiKey.startsWith('sk_')) {
        printError('Invalid API key format (expected sk_...)');
        process.exitCode = 1;
        return;
      }

      saveConfig({ api_key: apiKey, mode: 'live' });
      printSuccess('API key saved successfully');
      console.log(brand.dim('  Run `sardis status` to verify\n'));
    });

  program
    .command('logout')
    .description('Remove stored credentials')
    .action(() => {
      clearCredentials();
      printSuccess('Credentials removed');
      console.log();
    });
}
