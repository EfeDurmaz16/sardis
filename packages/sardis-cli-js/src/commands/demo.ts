/**
 * sardis demo - Guided walkthrough
 */

import type { Command } from 'commander';
import chalk from 'chalk';
import { printHeader, printSuccess, printKeyValue, printTable, brand, spinner } from '../output.js';

async function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function runPaymentDemo(): Promise<void> {
  printHeader('Payment Demo');
  console.log(brand.dim('  Simulating a payment flow...\n'));

  // Step 1: Policy check
  const spin1 = spinner('Checking spending policy...').start();
  await sleep(500);
  spin1.succeed('Policy check passed');

  // Step 2: Execute payment
  const spin2 = spinner('Executing payment to OpenAI...').start();
  await sleep(800);
  spin2.succeed('Payment executed');

  console.log();
  printKeyValue([
    ['Vendor', 'OpenAI'],
    ['Amount', brand.success('50.00 USDC')],
    ['Chain', 'Base'],
    ['Ledger TX', brand.info('ltx_demo_' + Date.now().toString(36))],
    ['Chain TX', brand.info('0xdemo...' + 'abc123')],
    ['Status', chalk.green('confirmed')],
  ]);
  console.log();
}

async function runCardDemo(): Promise<void> {
  printHeader('Virtual Card Demo');
  console.log(brand.dim('  Simulating virtual card operations...\n'));

  // Step 1: Issue card
  const spin1 = spinner('Issuing virtual card...').start();
  await sleep(600);
  spin1.succeed('Card issued');

  console.log();
  printKeyValue([
    ['Card ID', brand.info('card_demo_001')],
    ['Number', brand.dim('4242 **** **** 7890')],
    ['Limit', '$500.00/month'],
    ['Status', chalk.green('active')],
  ]);
  console.log();

  // Step 2: List cards
  const spin2 = spinner('Fetching card list...').start();
  await sleep(400);
  spin2.succeed('Cards loaded');

  console.log();
  printTable(
    ['Card ID', 'Agent', 'Limit', 'Spent', 'Status'],
    [
      ['card_demo_001', 'agent_abc', '$500.00', '$0.00', chalk.green('active')],
    ],
  );
  console.log();
}

async function runFullDemo(): Promise<void> {
  printHeader('Full Sardis Demo');
  console.log(brand.dim('  Walking through the complete Sardis workflow...\n'));

  // Step 1: Create agent
  const spin1 = spinner('Creating agent...').start();
  await sleep(500);
  spin1.succeed('Agent created: demo-agent');

  // Step 2: Create wallet
  const spin2 = spinner('Creating wallet...').start();
  await sleep(500);
  spin2.succeed('Wallet created: wal_demo_001');

  // Step 3: Set policy
  const spin3 = spinner('Setting spending policy...').start();
  await sleep(400);
  spin3.succeed('Policy set: max $500/tx, $5000 total');

  // Step 4: Execute payment
  const spin4 = spinner('Executing payment to OpenAI ($50 USDC)...').start();
  await sleep(800);
  spin4.succeed('Payment confirmed on Base');

  // Step 5: Issue card
  const spin5 = spinner('Issuing virtual card...').start();
  await sleep(600);
  spin5.succeed('Card issued: 4242 **** **** 7890');

  // Step 6: Spending summary
  const spin6 = spinner('Loading spending summary...').start();
  await sleep(400);
  spin6.succeed('Summary loaded');

  console.log();
  console.log(brand.bold('  Demo complete! Here\'s what happened:'));
  console.log();
  console.log('  1. Created an AI agent with a non-custodial MPC wallet');
  console.log('  2. Applied a natural language spending policy');
  console.log('  3. Executed a USDC payment on Base (policy-checked)');
  console.log('  4. Issued a virtual card with spending limits');
  console.log('  5. Generated a spending analytics report');
  console.log();
  console.log(brand.dim('  Get started: https://sardis.sh/docs'));
  console.log();
}

export function registerDemoCommand(program: Command): void {
  program
    .command('demo')
    .description('Run a guided demo walkthrough')
    .option('--scenario <type>', 'Demo scenario: payment, card, full', 'full')
    .action(async (opts: { scenario: string }) => {
      switch (opts.scenario) {
        case 'payment':
          await runPaymentDemo();
          break;
        case 'card':
          await runCardDemo();
          break;
        case 'full':
        default:
          await runFullDemo();
          break;
      }
    });
}
