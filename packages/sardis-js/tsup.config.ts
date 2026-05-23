import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'core/index': 'src/core/index.ts',
    'cards/index': 'src/cards/index.ts',
    'ledger/index': 'src/ledger/index.ts',
    'chain/index': 'src/chain/index.ts',
    'ucp/index': 'src/ucp/index.ts',
    'protocol/index': 'src/protocol/index.ts',
    'compliance/index': 'src/compliance/index.ts',
    'guardrails/index': 'src/guardrails/index.ts',
    'checkout/index': 'src/checkout/index.ts',
    'wallet/index': 'src/wallet/index.ts',
    'ramp/index': 'src/ramp/index.ts',
    'ai-sdk/index': 'src/ai-sdk/index.ts',
    'langchain/index': 'src/langchain/index.ts',
    'mastra/index': 'src/mastra/index.ts',
    'webhooks/index': 'src/webhooks/index.ts',
    'shims/node': 'src/shims/node.ts',
    'shims/web': 'src/shims/web.ts',
  },
  format: ['esm', 'cjs'],
  dts: true,
  sourcemap: true,
  clean: true,
  splitting: false,
  treeshake: true,
  target: 'node18',
  outExtension({ format }) {
    return { js: format === 'cjs' ? '.cjs' : '.js' };
  },
});
