/**
 * sardis status - Show config and auth status
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { loadConfig, getConfigPath, isSandbox } from '../config.js';
import { brand, printKeyValue, printHeader } from '../output.js';
import { CLI_VERSION } from '../version.js';

export function registerStatusCommand(program: Command): void {
  program
    .command('status')
    .description('Show configuration and authentication status')
    .action(() => {
      const config = loadConfig();
      const sandbox = isSandbox(config);

      printHeader('Sardis CLI Status');

      printKeyValue([
        ['Version', CLI_VERSION],
        ['Config', getConfigPath()],
        ['API URL', config.api_base_url],
        ['Mode', sandbox ? chalk.yellow('sandbox') : chalk.green('live')],
        ['Auth', config.api_key ? chalk.green('authenticated') : chalk.yellow('not configured')],
        ['Chain', config.default_chain],
        ['Token', config.default_token],
      ]);

      if (config.agent_id) {
        console.log();
        printKeyValue([
          ['Agent ID', config.agent_id],
          ['Wallet ID', config.wallet_id || brand.dim('not set')],
        ]);
      }

      if (sandbox) {
        console.log(brand.warn('\n  Run `sardis login` to connect your API key'));
      }

      console.log();
    });
}
