import { describe, it, expect } from 'vitest';
import { buildTemplate, parseArgs } from '../index.js';

const FORBIDDEN_BRANDING = [
  'aspendos',
  'yula',
  '@fides',
  'fides/sdk',
  '@agit',
  'agit/sdk',
  'nemoclaw',
  'memory-layer',
  'memory layer',
];

describe('parseArgs', () => {
  it('defaults the project name', () => {
    expect(parseArgs(['node', 'cli']).projectName).toBe('my-sardis-agent');
  });

  it('takes the first positional as the project name', () => {
    expect(parseArgs(['node', 'cli', 'pay-bot']).projectName).toBe('pay-bot');
  });

  it('detects --help / -h', () => {
    expect(parseArgs(['node', 'cli', '--help']).help).toBe(true);
    expect(parseArgs(['node', 'cli', '-h']).help).toBe(true);
  });

  it('ignores unknown flags without crashing', () => {
    const parsed = parseArgs(['node', 'cli', '--weird', 'real-name']);
    expect(parsed.projectName).toBe('real-name');
    expect(parsed.help).toBe(false);
  });
});

describe('buildTemplate — file set', () => {
  const t = buildTemplate('my-sardis-agent');

  it('emits exactly the expected files', () => {
    expect(Object.keys(t).sort()).toEqual(
      [
        '.env.example',
        '.gitignore',
        'README.md',
        'package.json',
        'src/agent.ts',
        'src/guard.ts',
        'src/setup.ts',
        'tsconfig.json',
      ].sort(),
    );
  });
});

describe('buildTemplate — generated package.json', () => {
  it('is valid JSON and depends on the shipping packages', () => {
    const pkg = JSON.parse(buildTemplate('my-sardis-agent')['package.json']!);
    expect(pkg.name).toBe('my-sardis-agent');
    expect(pkg.type).toBe('module');
    expect(pkg.dependencies.sardis).toBeTruthy();
    expect(pkg.dependencies['@sardis/reference']).toBeTruthy();
    expect(pkg.dependencies.ai).toBeTruthy();
    expect(pkg.dependencies['@ai-sdk/openai']).toBeTruthy();
    // Scripts cover the three demos.
    expect(pkg.scripts.setup).toContain('src/setup.ts');
    expect(pkg.scripts.guard).toContain('src/guard.ts');
    expect(pkg.scripts.agent).toContain('src/agent.ts');
  });

  it('does NOT depend on any foreign / private package', () => {
    const pkg = JSON.parse(buildTemplate('x')['package.json']!);
    const deps = JSON.stringify({ ...pkg.dependencies, ...pkg.devDependencies });
    for (const banned of FORBIDDEN_BRANDING) {
      expect(deps.toLowerCase()).not.toContain(banned);
    }
  });

  it('honors a custom project name', () => {
    const pkg = JSON.parse(buildTemplate('pay-bot')['package.json']!);
    expect(pkg.name).toBe('pay-bot');
  });
});

describe('buildTemplate — generated tsconfig.json', () => {
  it('is valid JSON, strict, ESM/bundler', () => {
    const ts = JSON.parse(buildTemplate('x')['tsconfig.json']!);
    expect(ts.compilerOptions.strict).toBe(true);
    expect(ts.compilerOptions.module).toBe('ESNext');
    expect(ts.compilerOptions.moduleResolution).toBe('bundler');
  });
});

describe('buildTemplate — import specifiers point at shipping packages', () => {
  const t = buildTemplate('x');

  it('setup.ts imports the real `sardis` umbrella client', () => {
    expect(t['src/setup.ts']).toContain("from 'sardis'");
    expect(t['src/setup.ts']).toContain('wallets.create');
    expect(t['src/setup.ts']).toContain('policies.apply');
  });

  it('agent.ts imports the real `sardis/ai-sdk` provider', () => {
    expect(t['src/agent.ts']).toContain("from 'sardis/ai-sdk'");
    expect(t['src/agent.ts']).toContain('createSardis');
    expect(t['src/agent.ts']).toContain('sardis.tools');
    expect(t['src/agent.ts']).toContain('sardis.systemPrompt');
  });

  it('guard.ts imports the real `@sardis/reference` simulator (offline, no key)', () => {
    expect(t['src/guard.ts']).toContain("from '@sardis/reference'");
    expect(t['src/guard.ts']).toContain('simulateSpend');
    // Demonstrates both an allow and at least one deny.
    expect(t['src/guard.ts']).toContain("'USDC'");
    expect(t['src/guard.ts']).toContain('7995'); // gambling MCC → deny
  });
});

describe('buildTemplate — .env.example carries no real secrets', () => {
  const env = buildTemplate('x')['.env.example']!;

  it('declares the needed vars', () => {
    expect(env).toContain('SARDIS_API_KEY=');
    expect(env).toContain('SARDIS_WALLET_ID=');
    expect(env).toContain('OPENAI_API_KEY=');
  });

  it('ships only placeholder / empty values (no live keys)', () => {
    // The only non-empty key value is an obvious placeholder.
    expect(env).toContain('sk_test_replace_me');
    expect(env).not.toMatch(/sk_live_[A-Za-z0-9]/);
    expect(env).not.toMatch(/sk-[A-Za-z0-9]{20,}/); // no real OpenAI key
  });
});

describe('buildTemplate — no foreign branding leaks into any file', () => {
  it('every generated file is clean of Aspendos/YULA/Fides/AGIT/memory strings', () => {
    const t = buildTemplate('my-sardis-agent');
    for (const [file, content] of Object.entries(t)) {
      const lower = content.toLowerCase();
      for (const banned of FORBIDDEN_BRANDING) {
        expect(lower, `${banned} leaked into ${file}`).not.toContain(banned);
      }
    }
  });
});
