/**
 * Generate MDX files from the Sardis OpenAPI spec.
 *
 * Usage:
 *   node scripts/generate-openapi.mjs
 *
 * This reads openapi.json (local copy or fetched from API)
 * and generates MDX pages in content/docs/api/.
 */
import { generateFiles } from 'fumadocs-openapi';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const specPath = resolve('openapi.json');

async function main() {
  // Try local spec first, otherwise create a placeholder
  if (!existsSync(specPath)) {
    console.log('No openapi.json found. Skipping OpenAPI generation.');
    console.log('To generate API docs:');
    console.log('  1. Start the Sardis API server');
    console.log('  2. Fetch the spec: curl https://api.sardis.sh/api/v2/openapi.json -o openapi.json');
    console.log('  3. Re-run: node scripts/generate-openapi.mjs');
    return;
  }

  const spec = JSON.parse(readFileSync(specPath, 'utf-8'));

  await generateFiles({
    input: [spec],
    output: './content/docs/api',
    groupBy: 'tag',
  });

  console.log('OpenAPI docs generated successfully.');
}

main().catch(console.error);
