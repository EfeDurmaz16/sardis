import { defineConfig } from 'tsup';

export default defineConfig({
  entry: {
    index: 'src/index.ts',
    'adapters/langchain': 'src/adapters/langchain.ts',
    'adapters/vercel-ai': 'src/adapters/vercel-ai.ts',
    'adapters/mcp': 'src/adapters/mcp.ts',
  },
  format: ['esm', 'cjs'],
  dts: true,
  sourcemap: true,
  clean: true,
  splitting: false,
  treeshake: true,
  target: 'node18',
  external: ['sardis', '@langchain/core', 'ai', 'zod'],
  outExtension({ format }) {
    return { js: format === 'cjs' ? '.cjs' : '.js' };
  },
});
