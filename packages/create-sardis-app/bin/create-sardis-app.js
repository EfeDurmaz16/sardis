#!/usr/bin/env node
/**
 * create-sardis-app — scaffold a Next.js + AI SDK + Sardis app.
 *
 * Usage:
 *   npx create-sardis-app my-app
 *   npx create-sardis-app my-app --pm pnpm
 *
 * Mirrors the create-next-app UX. Copies the local `template/` tree into
 * the target directory, rewrites package name + a couple of placeholders,
 * and prints the next steps.
 */

import { cp, mkdir, readFile, writeFile, readdir, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const TEMPLATE_DIR = resolve(__dirname, '..', 'template');

function parseArgs(argv) {
  const args = { name: null, pm: 'npm', help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--help' || a === '-h') args.help = true;
    else if (a === '--pm') args.pm = argv[++i] ?? 'npm';
    else if (!args.name) args.name = a;
  }
  return args;
}

function printHelp() {
  console.log(`create-sardis-app — Next.js + AI SDK + Sardis scaffolder

Usage:
  npx create-sardis-app <project-name>
  npx create-sardis-app <project-name> --pm pnpm|yarn|npm|bun
  npx create-sardis-app --help

After scaffolding:
  cd <project-name>
  cp .env.example .env.local      # add your SARDIS_API_KEY and SARDIS_WALLET_ID
  <pm> install
  <pm> run dev
`);
}

async function walk(dir) {
  const entries = [];
  for (const name of await readdir(dir)) {
    const full = join(dir, name);
    const s = await stat(full);
    if (s.isDirectory()) entries.push(...(await walk(full)));
    else entries.push(full);
  }
  return entries;
}

async function copyTemplate(srcRoot, dstRoot, replacements) {
  const files = await walk(srcRoot);
  for (const file of files) {
    const rel = relative(srcRoot, file);
    const dst = join(dstRoot, rel);
    await mkdir(dirname(dst), { recursive: true });
    let body = await readFile(file, 'utf8');
    for (const [needle, value] of Object.entries(replacements)) {
      body = body.split(needle).join(value);
    }
    await writeFile(dst, body, 'utf8');
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.name) {
    printHelp();
    process.exit(args.help ? 0 : 1);
  }

  const target = resolve(process.cwd(), args.name);
  if (existsSync(target)) {
    console.error(`Target directory already exists: ${target}`);
    process.exit(1);
  }

  console.log(`Scaffolding ${args.name} → ${target}`);
  await mkdir(target, { recursive: true });
  await copyTemplate(TEMPLATE_DIR, target, {
    '__APP_NAME__': args.name,
  });

  console.log('');
  console.log('Done. Next steps:');
  console.log('');
  console.log(`  cd ${args.name}`);
  console.log('  cp .env.example .env.local');
  console.log('  # Add SARDIS_API_KEY + SARDIS_WALLET_ID + OPENAI_API_KEY to .env.local');
  console.log(`  ${args.pm} install`);
  console.log(`  ${args.pm} run dev`);
  console.log('');
  console.log('Then visit http://localhost:3000 and ask the agent to pay something.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
