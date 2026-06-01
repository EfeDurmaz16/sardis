#!/usr/bin/env node
/**
 * Validate the Sardis OpenClaw skill pack.
 *
 * The skill pack is markdown, not code, so its "test" is a structural lint:
 *   - every skills/<x>/SKILL.md has YAML-ish frontmatter with name/description/
 *     homepage/user-invocable and the SARDIS_API_KEY env gate;
 *   - each skill names at least one real `sardis_*` verb;
 *   - NO Aspendos / YULA / fides / agit / nemo branding leaks (hard rule);
 *   - homepage is sardis.sh, not aspendos.dev.
 *
 * Exits non-zero on any failure so `pnpm test` gates it.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILLS_DIR = join(__dirname, '..', 'skills');

const KNOWN_VERBS = [
  'sardis_give_wallet',
  'sardis_spend',
  'sardis_issue_card',
  'sardis_set_budget',
  'sardis_pay_invoice',
  'sardis_check_balance',
  'sardis_check_policy',
  'sardis_list_transactions',
  'sardis_freeze_card',
];

const FORBIDDEN = [/aspendos/i, /\byula\b/i, /\bfides\b/i, /\bagit\b/i, /\bnemo/i, /aspendos\.dev/i];

const errors = [];

const skillDirs = readdirSync(SKILLS_DIR).filter((d) => statSync(join(SKILLS_DIR, d)).isDirectory());
if (skillDirs.length === 0) errors.push('no skill directories found');

let checked = 0;
for (const dir of skillDirs) {
  const file = join(SKILLS_DIR, dir, 'SKILL.md');
  let text;
  try {
    text = readFileSync(file, 'utf8');
  } catch {
    errors.push(`${dir}: missing SKILL.md`);
    continue;
  }
  checked++;

  if (!/^---\n[\s\S]*?\n---/.test(text)) errors.push(`${dir}: missing frontmatter`);
  for (const key of ['name:', 'description:', 'homepage:', 'user-invocable:']) {
    if (!text.includes(key)) errors.push(`${dir}: frontmatter missing "${key}"`);
  }
  if (!text.includes('SARDIS_API_KEY')) errors.push(`${dir}: missing SARDIS_API_KEY env gate`);
  if (!text.includes('https://sardis.sh')) errors.push(`${dir}: homepage is not sardis.sh`);
  if (!/name:\s*sardis-/.test(text)) errors.push(`${dir}: skill name must be sardis-prefixed`);

  if (!KNOWN_VERBS.some((v) => text.includes(v))) {
    errors.push(`${dir}: references no known sardis_* verb`);
  }
  for (const pat of FORBIDDEN) {
    if (pat.test(text)) errors.push(`${dir}: forbidden branding leak matching ${pat}`);
  }
}

if (errors.length) {
  console.error('Sardis OpenClaw skill-pack validation FAILED:');
  for (const e of errors) console.error('  - ' + e);
  process.exit(1);
}
console.log(`Sardis OpenClaw skill-pack OK: ${checked} skills validated.`);
