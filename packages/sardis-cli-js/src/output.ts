/**
 * CLI Output Helpers
 *
 * Chalk colors, table builder, spinner, and key-value printing.
 */

import chalk from 'chalk';
import Table from 'cli-table3';
import ora from 'ora';

// Brand colors
export const brand = {
  primary: chalk.hex('#6366f1'),   // indigo
  success: chalk.green,
  error: chalk.red,
  warn: chalk.yellow,
  info: chalk.cyan,
  dim: chalk.dim,
  bold: chalk.bold,
};

export function printSuccess(msg: string): void {
  console.log(brand.success(`  ${msg}`));
}

export function printError(msg: string): void {
  console.log(brand.error(`Error: ${msg}`));
}

export function printWarn(msg: string): void {
  console.log(brand.warn(msg));
}

export function printInfo(msg: string): void {
  console.log(brand.info(msg));
}

export function printSandboxBanner(): void {
  console.log(brand.warn('\n  [sandbox] No API key configured - showing simulated data'));
  console.log(brand.dim('  Run `sardis login` to connect to your Sardis account\n'));
}

/**
 * Print key-value pairs in a clean format
 */
export function printKeyValue(pairs: Array<[string, string]>): void {
  const maxKeyLen = Math.max(...pairs.map(([k]) => k.length));
  for (const [key, value] of pairs) {
    console.log(`  ${brand.dim(key.padEnd(maxKeyLen + 2))}${value}`);
  }
}

/**
 * Create a formatted table
 */
export function createTable(headers: string[]): Table.Table {
  return new Table({
    head: headers.map((h) => brand.bold(h)),
    style: { head: [], border: [] },
    chars: {
      top: '', 'top-mid': '', 'top-left': '', 'top-right': '',
      bottom: '', 'bottom-mid': '', 'bottom-left': '', 'bottom-right': '',
      left: '  ', 'left-mid': '', mid: '', 'mid-mid': '',
      right: '', 'right-mid': '', middle: '  ',
    },
  });
}

/**
 * Print a table
 */
export function printTable(headers: string[], rows: string[][]): void {
  const table = createTable(headers);
  for (const row of rows) {
    table.push(row);
  }
  console.log(table.toString());
}

/**
 * Create a spinner
 */
export function spinner(text: string) {
  return ora({ text, spinner: 'dots' });
}

/**
 * Print a section header
 */
export function printHeader(title: string): void {
  console.log(`\n  ${brand.bold(title)}\n`);
}
