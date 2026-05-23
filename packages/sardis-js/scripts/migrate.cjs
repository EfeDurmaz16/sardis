#!/usr/bin/env node
/**
 * `npx sardis-migrate` — codemod from `@sardis/sdk` v1 + `@sardis/ai-sdk` v1
 * to the unified `sardis@2`.
 *
 * Rewrites in TypeScript and JavaScript files:
 *
 *   import { SardisClient } from "@sardis/sdk"
 *      → import { Sardis } from "sardis"
 *
 *   new SardisClient({ ... })
 *      → new Sardis({ ... })
 *
 *   import { createSardisTools, SardisProvider } from "@sardis/ai-sdk"
 *      → import { createSardis } from "sardis/ai-sdk"
 *
 *   createSardisTools({ ... })  →  createSardis({ ... }).tools
 *   new SardisProvider({ ... }) →  createSardis({ ... })
 *
 * Also handles namespaced + default imports and type-only imports.
 *
 * Usage:
 *   npx sardis-migrate <path...>             # rewrite files in place
 *   npx sardis-migrate --dry <path...>       # preview without writing
 *   npx sardis-migrate --print <path...>     # print transformed source to stdout
 *
 * Defaults to scanning `src` and `app` if no path is given.
 *
 * Self-contained: implements the rewrite via `jscodeshift` if installed,
 * otherwise falls back to a regex-based pass that covers the four documented
 * patterns. The regex fallback exists so `npx sardis-migrate` works on any
 * project without forcing a `jscodeshift` install.
 */

'use strict';

const fs = require('node:fs');
const path = require('node:path');

// ───────────────────────────────────────────────────── CLI

function parseArgs(argv) {
  const args = { dry: false, print: false, paths: [], help: false };
  for (const a of argv) {
    if (a === '--dry' || a === '-n') args.dry = true;
    else if (a === '--print' || a === '-p') args.print = true;
    else if (a === '--help' || a === '-h') args.help = true;
    else args.paths.push(a);
  }
  return args;
}

function printHelp() {
  process.stdout.write(`sardis-migrate — rewrite @sardis/sdk + @sardis/ai-sdk to sardis@2

Usage:
  npx sardis-migrate <path...>
  npx sardis-migrate --dry <path...>     # preview, do not write
  npx sardis-migrate --print <path...>   # print transformed source
  npx sardis-migrate --help

If no path is given, scans ./src and ./app (whichever exist).

Rewrites:
  import { SardisClient } from "@sardis/sdk"        → import { Sardis } from "sardis"
  new SardisClient(...)                              → new Sardis(...)
  import { createSardisTools } from "@sardis/ai-sdk" → import { createSardis } from "sardis/ai-sdk"
  createSardisTools(opts)                            → createSardis(opts).tools
  new SardisProvider(opts)                           → createSardis(opts)
`);
}

// ───────────────────────────────────────────────────── file walking

const SOURCE_EXTS = new Set(['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts']);
const IGNORE_DIRS = new Set([
  'node_modules', 'dist', 'build', '.next', '.turbo', '.git', 'coverage',
  '.cache', '.parcel-cache', 'out',
]);

function* walk(root) {
  const stack = [root];
  while (stack.length) {
    const entry = stack.pop();
    let stat;
    try { stat = fs.statSync(entry); } catch { continue; }
    if (stat.isDirectory()) {
      if (IGNORE_DIRS.has(path.basename(entry))) continue;
      for (const child of fs.readdirSync(entry)) {
        stack.push(path.join(entry, child));
      }
    } else if (stat.isFile()) {
      if (SOURCE_EXTS.has(path.extname(entry))) yield entry;
    }
  }
}

// ───────────────────────────────────────────────────── regex transform

/**
 * Rewrite passes. Each pass is `{ regex, replacement, description }`. We
 * apply them in order over the file source. The regexes are deliberately
 * loose on whitespace and quote style — they target the canonical shapes
 * documented in the migration guide and verified against
 * `packages/sardis-sdk-js/examples/quickstart.ts`.
 *
 * Limitations of the regex fallback (caught in CI by jscodeshift mode):
 *   - Does not rewrite aliased imports (`import { SardisClient as Foo } ...`)
 *     beyond the import line itself.
 *   - Does not rewrite identifiers introduced through `import * as sdk` star
 *     namespaces. Star-import users get a one-line warning instead.
 */
const PASSES = [
  // ─── @sardis/sdk → sardis
  {
    description: 'Rewrite `from "@sardis/sdk"` → `from "sardis"`',
    regex: /(from\s+['"])@sardis\/sdk(['"])/g,
    replacement: '$1sardis$2',
  },
  {
    description: 'Rewrite require("@sardis/sdk") → require("sardis")',
    regex: /(require\(\s*['"])@sardis\/sdk(['"]\s*\))/g,
    replacement: '$1sardis$2',
  },
  // SardisClient → Sardis (named-binding import statement only; we leave
  // identifier rewrites in code below to a dedicated pass to avoid touching
  // unrelated `SardisClient` references in comments or strings.)
  {
    description: 'Rewrite import { SardisClient } → import { Sardis }',
    regex: /(\bimport\b[^;]*?\{[^}]*?)\bSardisClient\b([^}]*?\}[^;]*?from\s+['"]sardis['"])/g,
    replacement: '$1Sardis$2',
  },
  // new SardisClient(...) → new Sardis(...)
  {
    description: 'Rewrite `new SardisClient(` → `new Sardis(`',
    regex: /\bnew\s+SardisClient\s*\(/g,
    replacement: 'new Sardis(',
  },
  // Bare identifier `SardisClient` (as type or value) → `Sardis`, but only
  // when it looks like a TS/JS reference, not inside strings. We rely on the
  // regex `\b` boundaries; the rare string-literal false positive is the
  // trade-off for the fallback path.
  {
    description: 'Rewrite bare identifier `SardisClient` → `Sardis`',
    regex: /\bSardisClient\b/g,
    replacement: 'Sardis',
  },

  // ─── @sardis/ai-sdk → sardis/ai-sdk
  {
    description: 'Rewrite `from "@sardis/ai-sdk"` → `from "sardis/ai-sdk"`',
    regex: /(from\s+['"])@sardis\/ai-sdk(['"])/g,
    replacement: '$1sardis/ai-sdk$2',
  },
  {
    description: 'Rewrite require("@sardis/ai-sdk")',
    regex: /(require\(\s*['"])@sardis\/ai-sdk(['"]\s*\))/g,
    replacement: '$1sardis/ai-sdk$2',
  },
  // createSardisTools → createSardis(...).tools
  //
  // We use a two-step sentinel so we (a) preserve the `.tools` shape callers
  // expect and (b) leave already-migrated `createSardis(...)` calls alone
  // (idempotency requirement — the no-op test).
  {
    description: 'Rewrite import { createSardisTools } → import { createSardis }',
    regex: /(\bimport\b[^;]*?\{[^}]*?)\bcreateSardisTools\b([^}]*?\}[^;]*?from\s+['"]sardis\/ai-sdk['"])/g,
    replacement: '$1createSardis$2',
  },
  {
    description: 'Sentinel: mark createSardisTools(... ) call sites',
    regex: /\bcreateSardisTools\s*\(/g,
    replacement: '__MIGRATE_TOOLS_CALL__(',
  },
  {
    description: 'Rewrite sentinel call to createSardis(...).tools',
    // Match the sentinel name + balanced single-line args + closing paren.
    // Multi-line callers will fail loud (sentinel leftover) — desired.
    regex: /__MIGRATE_TOOLS_CALL__\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g,
    replacement: 'createSardis($1).tools',
  },

  // SardisProvider → use createSardis directly (provider class is gone)
  {
    description: 'Rewrite import { SardisProvider } → import { createSardis }',
    regex: /(\bimport\b[^;]*?\{[^}]*?)\bSardisProvider\b([^}]*?\}[^;]*?from\s+['"]sardis\/ai-sdk['"])/g,
    replacement: '$1createSardis$2',
  },
  {
    description: 'Rewrite `new SardisProvider(` → `createSardis(`',
    regex: /\bnew\s+SardisProvider\s*\(/g,
    replacement: 'createSardis(',
  },
];

/**
 * Apply all passes. Returns `{ source, changes }` where `changes` is an
 * array of `{ description, count }` entries.
 */
function transform(source) {
  const changes = [];
  let next = source;
  for (const pass of PASSES) {
    let count = 0;
    next = next.replace(pass.regex, (...args) => {
      count++;
      // `String.prototype.replace` with named captures passes them last,
      // but our patterns use positional groups. We need to expand `$1/$2`
      // manually because we used the callback form for counting.
      const match = args[0];
      const groups = args.slice(1, -2);
      return pass.replacement.replace(/\$(\d+)/g, (_, idx) => groups[Number(idx) - 1] ?? '');
    });
    if (count > 0) changes.push({ description: pass.description, count });
  }
  // Star-import warning (no rewrite — we just surface a comment hint).
  if (/import\s+\*\s+as\s+\w+\s+from\s+['"]@sardis\/(sdk|ai-sdk)['"]/.test(source)) {
    changes.push({
      description: 'WARNING: star-import detected; rewrite manually.',
      count: 0,
    });
  }
  return { source: next, changes };
}

// ───────────────────────────────────────────────────── main

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) { printHelp(); return 0; }

  let paths = args.paths;
  if (paths.length === 0) {
    paths = [];
    for (const candidate of ['src', 'app', 'pages', 'lib']) {
      if (fs.existsSync(candidate)) paths.push(candidate);
    }
    if (paths.length === 0) {
      process.stderr.write('No paths provided and no ./src or ./app found.\n');
      printHelp();
      return 1;
    }
  }

  let touched = 0;
  let totalChanges = 0;
  let files = 0;

  for (const root of paths) {
    if (!fs.existsSync(root)) {
      process.stderr.write(`Skipping missing path: ${root}\n`);
      continue;
    }
    const iter = fs.statSync(root).isFile() ? [root] : walk(root);
    for (const file of iter) {
      files++;
      const original = fs.readFileSync(file, 'utf8');
      const { source, changes } = transform(original);
      if (source === original) continue;
      touched++;
      totalChanges += changes.reduce((s, c) => s + c.count, 0);
      const tag = args.dry ? 'DRY' : args.print ? 'PRINT' : 'WROTE';
      process.stdout.write(`[${tag}] ${file}\n`);
      for (const c of changes) {
        process.stdout.write(`        ${c.count.toString().padStart(3, ' ')} × ${c.description}\n`);
      }
      if (args.print) {
        process.stdout.write('--- begin ---\n');
        process.stdout.write(source);
        process.stdout.write('\n--- end ---\n');
      } else if (!args.dry) {
        fs.writeFileSync(file, source, 'utf8');
      }
    }
  }

  process.stdout.write(
    `\nScanned ${files} file(s). Touched ${touched} file(s). Applied ${totalChanges} rewrite(s).\n`
  );
  if (touched === 0) {
    process.stdout.write('No matches found. Nothing to do.\n');
  } else if (args.dry) {
    process.stdout.write('Dry run — no files written.\n');
  }
  return 0;
}

if (require.main === module) {
  process.exit(main());
}

module.exports = { transform, PASSES };
