/**
 * sardis balance [wallet-id] - Show wallet balance
 */

import type { Command } from 'commander';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printHeader, printKeyValue, printError, printSandboxBanner, brand, spinner } from '../output.js';

export function registerBalanceCommand(program: Command): void {
  program
    .command('balance')
    .description('Show wallet balance')
    .argument('[wallet-id]', 'Wallet ID (uses default if not specified)')
    .action(async (walletId?: string) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        printHeader('Wallet Balance');
        printKeyValue([
          ['Wallet ID', walletId || 'wal_sim_demo01'],
          ['Balance', brand.success('1,250.00 USDC')],
          ['Spent Total', '750.00 USDC'],
          ['Limit/Tx', '500.00'],
          ['Limit Total', '5,000.00'],
          ['Chain', 'Base'],
        ]);
        console.log();
        return;
      }

      const id = walletId || config.wallet_id;
      if (!id) {
        printError('No wallet ID specified. Pass a wallet ID or set SARDIS_WALLET_ID.');
        process.exitCode = 1;
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Fetching balance...').start();

      try {
        const wallet = await api.get<Record<string, unknown>>(`/api/v2/wallets/${id}`);
        spin.stop();

        printHeader('Wallet Balance');
        printKeyValue([
          ['Wallet ID', String(wallet['wallet_id'] || id)],
          ['Balance', brand.success(`${wallet['balance'] || '0.00'} ${wallet['currency'] || 'USDC'}`)],
          ['Spent Total', `${wallet['spent_total'] || '0.00'} ${wallet['currency'] || 'USDC'}`],
          ['Limit/Tx', String(wallet['limit_per_tx'] ?? 'N/A')],
          ['Limit Total', String(wallet['limit_total'] ?? 'N/A')],
        ]);
        console.log();
      } catch (err) {
        spin.stop();
        if (err instanceof APIError) {
          printError(err.message);
        } else {
          throw err;
        }
      }
    });
}
