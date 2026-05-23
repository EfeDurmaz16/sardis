import { describe, it, expect } from 'vitest';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { transform } = require(path.resolve(here, '../scripts/migrate.cjs')) as {
  transform: (src: string) => { source: string; changes: Array<{ description: string; count: number }> };
};

describe('sardis-migrate codemod', () => {
  it('rewrites `@sardis/sdk` named import + `new SardisClient` (quickstart corpus)', () => {
    const corpus = [
      `import { SardisClient } from '@sardis/sdk';`,
      ``,
      `const sardis = new SardisClient({ apiKey: process.env.SARDIS_API_KEY! });`,
      `await sardis.payments.send({ wallet_id: 'w_1', to: 't_1', amount: '10.00' });`,
    ].join('\n');
    const { source, changes } = transform(corpus);

    expect(source).not.toContain('@sardis/sdk');
    expect(source).toContain(`from 'sardis'`);
    expect(source).not.toContain('new SardisClient(');
    expect(source).toContain('new Sardis(');
    expect(source).toContain(`import { Sardis } from 'sardis';`);

    expect(changes.length).toBeGreaterThan(0);
    expect(changes.find((c) => c.description.includes('@sardis/sdk'))).toBeTruthy();
    expect(changes.find((c) => c.description.includes('new SardisClient'))).toBeTruthy();
  });

  it('rewrites @sardis/ai-sdk → sardis/ai-sdk + createSardisTools → createSardis(...).tools', () => {
    const corpus = [
      `import { createSardisTools } from '@sardis/ai-sdk';`,
      `import { generateText } from 'ai';`,
      `import { openai } from '@ai-sdk/openai';`,
      ``,
      `const tools = createSardisTools({ apiKey: 'sk_test', walletId: 'wallet_abc' });`,
      ``,
      `await generateText({ model: openai('gpt-4o'), tools, prompt: 'pay $20' });`,
    ].join('\n');
    const { source } = transform(corpus);

    expect(source).not.toContain('@sardis/ai-sdk');
    expect(source).toContain(`from 'sardis/ai-sdk'`);
    expect(source).toContain(`import { createSardis } from 'sardis/ai-sdk'`);
    expect(source).toContain(`const tools = createSardis({ apiKey: 'sk_test', walletId: 'wallet_abc' }).tools;`);
  });

  it('rewrites `new SardisProvider(...)` → `createSardis(...)` with new import', () => {
    const corpus = [
      `import { SardisProvider } from '@sardis/ai-sdk';`,
      ``,
      `const sardis = new SardisProvider({ apiKey: 'sk', walletId: 'w_1' });`,
      `await sardis.balance();`,
    ].join('\n');
    const { source } = transform(corpus);

    expect(source).toContain(`import { createSardis } from 'sardis/ai-sdk';`);
    expect(source).toContain(`const sardis = createSardis({ apiKey: 'sk', walletId: 'w_1' });`);
    expect(source).not.toContain('SardisProvider');
  });

  it('handles double-quoted strings + multi-name named imports', () => {
    const corpus = [
      `import { SardisClient, APIError, RateLimitError } from "@sardis/sdk";`,
      `const c = new SardisClient({ apiKey: process.env.K! });`,
      `try { await c.payments.send({ wallet_id: 'w', to: 't', amount: '1.00' }); }`,
      `catch (e) { if (e instanceof APIError) throw e; }`,
    ].join('\n');
    const { source } = transform(corpus);

    expect(source).toContain(`from "sardis"`);
    expect(source).toContain(`import { Sardis, APIError, RateLimitError } from "sardis";`);
    expect(source).toContain(`const c = new Sardis({`);
    expect(source).not.toContain('SardisClient');
  });

  it('is a no-op on already-migrated code', () => {
    const corpus = [
      `import { Sardis } from 'sardis';`,
      `import { createSardis } from 'sardis/ai-sdk';`,
      `const s = new Sardis({ apiKey: 'sk' });`,
      `const ai = createSardis({ apiKey: 'sk', walletId: 'w' });`,
    ].join('\n');
    const { source, changes } = transform(corpus);
    expect(source).toBe(corpus);
    expect(changes).toEqual([]);
  });

  it('rewrites CommonJS require()', () => {
    const corpus = `const { SardisClient } = require("@sardis/sdk");\nconst c = new SardisClient({ apiKey: 'k' });`;
    const { source } = transform(corpus);
    expect(source).toContain(`require("sardis")`);
    expect(source).toContain(`new Sardis({`);
    expect(source).not.toContain('SardisClient');
  });

  it('flags star-imports with a warning instead of rewriting', () => {
    const corpus = `import * as sdk from '@sardis/sdk';\nsdk.SardisClient;`;
    const { changes } = transform(corpus);
    const warning = changes.find((c) => c.description.startsWith('WARNING'));
    expect(warning).toBeTruthy();
  });
});
