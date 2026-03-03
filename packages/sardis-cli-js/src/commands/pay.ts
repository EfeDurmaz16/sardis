/**
 * sardis pay - Execute a payment
 */

import type { Command } from 'commander';
import { loadConfig, isSandbox } from '../config.js';
import { SardisAPI, APIError } from '../api.js';
import { printHeader, printKeyValue, printError, printSuccess, printSandboxBanner, brand, spinner } from '../output.js';

export function registerPayCommand(program: Command): void {
  program
    .command('pay')
    .description('Execute a payment')
    .requiredOption('--vendor <name>', 'Merchant or service to pay')
    .requiredOption('--amount <number>', 'Payment amount in USD', parseFloat)
    .option('--token <token>', 'Token to use (USDC, USDT, EURC)', 'USDC')
    .option('--chain <chain>', 'Chain to use')
    .option('--purpose <text>', 'Payment purpose/description')
    .option('--from <wallet-id>', 'Source wallet ID')
    .action(async (opts: {
      vendor: string;
      amount: number;
      token: string;
      chain?: string;
      purpose?: string;
      from?: string;
    }) => {
      const config = loadConfig();

      if (isSandbox(config)) {
        printSandboxBanner();
        const spin = spinner('Processing payment...').start();
        await new Promise((r) => setTimeout(r, 800));
        spin.stop();

        printSuccess('Payment executed successfully');
        console.log();
        printKeyValue([
          ['Vendor', opts.vendor],
          ['Amount', `${opts.amount.toFixed(2)} ${opts.token}`],
          ['Chain', opts.chain || config.default_chain],
          ['Ledger TX', brand.info('ltx_sim_' + Date.now().toString(36))],
          ['Chain TX', brand.info('0x' + 'a'.repeat(8) + '...' + 'f'.repeat(8))],
          ['Status', brand.success('confirmed')],
        ]);
        if (opts.purpose) {
          console.log(`  ${brand.dim('Purpose'.padEnd(14))}${opts.purpose}`);
        }
        console.log();
        return;
      }

      const walletId = opts.from || config.wallet_id;
      if (!walletId) {
        printError('No wallet ID specified. Use --from or set SARDIS_WALLET_ID.');
        process.exitCode = 1;
        return;
      }

      const api = new SardisAPI(config);
      const spin = spinner('Processing payment...').start();

      try {
        const mandate = {
          mandate_id: `cli_payment_${Date.now()}`,
          issuer: 'cli_user',
          subject: walletId,
          destination: opts.vendor,
          amount_minor: Math.round(opts.amount * 100),
          token: opts.token,
          chain: opts.chain || config.default_chain,
          expires_at: Math.floor(Date.now() / 1000) + 300,
          ...(opts.purpose ? { purpose: opts.purpose } : {}),
        };

        const result = await api.post<Record<string, unknown>>('/api/v2/mandates/execute', { mandate });
        spin.stop();

        printSuccess('Payment executed successfully');
        console.log();
        printKeyValue([
          ['Vendor', opts.vendor],
          ['Amount', `${opts.amount.toFixed(2)} ${opts.token}`],
          ['Chain', String(result['chain'] || opts.chain || config.default_chain)],
          ['Ledger TX', brand.info(String(result['ledger_tx_id'] || 'N/A'))],
          ['Chain TX', brand.info(String(result['chain_tx_hash'] || 'N/A'))],
          ['Status', brand.success('confirmed')],
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
