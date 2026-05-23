import { defineConfig } from 'tsup'

// Shim package — only `src/index.ts` remains (re-exports from sardis/ai-sdk).
// Old `tools.ts` and `provider.ts` were removed when the shim conversion landed.
export default defineConfig({
  entry: {
    index: 'src/index.ts',
  },
  format: ['esm'],
  dts: true,
  clean: true,
  sourcemap: true,
  minify: false,
  external: ['ai', 'sardis'],
  treeshake: true,
})
