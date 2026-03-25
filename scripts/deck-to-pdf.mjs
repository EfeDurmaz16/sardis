#!/usr/bin/env node
/**
 * Convert pitch-deck.html to PDF using Puppeteer.
 *
 * Usage: node scripts/deck-to-pdf.mjs [input.html] [output.pdf]
 */

import puppeteer from 'puppeteer';
import { resolve } from 'path';
import { existsSync } from 'fs';

const input = process.argv[2] || 'pitch-deck.html';
const output = process.argv[3] || 'sardis-pitch-deck.pdf';

const inputPath = resolve(input);
if (!existsSync(inputPath)) {
  console.error(`File not found: ${inputPath}`);
  process.exit(1);
}

console.log(`Converting ${input} → ${output}`);

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();

await page.setViewport({ width: 1280, height: 720 });
await page.goto(`file://${inputPath}`, { waitUntil: 'networkidle0', timeout: 30000 });

// Wait for fonts to load
await page.evaluate(() => document.fonts.ready);
await new Promise(r => setTimeout(r, 1000));

await page.pdf({
  path: output,
  width: '1280px',
  height: '720px',
  printBackground: true,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
  preferCSSPageSize: true,
});

await browser.close();
console.log(`Done → ${output}`);
