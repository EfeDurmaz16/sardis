/**
 * Rollup configuration for browser bundle
 *
 * Creates optimized browser-specific builds of the Sardis SDK.
 */

import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import replace from '@rollup/plugin-replace';
import terser from '@rollup/plugin-terser';
import json from '@rollup/plugin-json';

const production = process.env.NODE_ENV === 'production';
const includeMinifiedBundles = process.env.SARDIS_BUILD_MINIFIED === '1';

const outputs = [
  {
    file: 'dist/browser/index.js',
    format: 'esm',
    sourcemap: true,
    exports: 'named',
  },
  {
    file: 'dist/browser/sardis.umd.js',
    format: 'umd',
    name: 'Sardis',
    sourcemap: true,
    globals: {
      axios: 'axios',
    },
  },
];

if (includeMinifiedBundles) {
  outputs.push(
    {
      file: 'dist/browser/index.min.js',
      format: 'esm',
      sourcemap: true,
      exports: 'named',
      plugins: [terser({
        compress: {
          drop_console: production,
          drop_debugger: production,
        },
        mangle: {
          keep_classnames: true,
          keep_fnames: true,
        },
      })],
    },
    {
      file: 'dist/browser/sardis.umd.min.js',
      format: 'umd',
      name: 'Sardis',
      sourcemap: true,
      globals: {
        axios: 'axios',
      },
      plugins: [terser({
        compress: {
          drop_console: production,
          drop_debugger: production,
        },
        mangle: {
          keep_classnames: true,
          keep_fnames: true,
        },
      })],
    }
  );
}

/** @type {import('rollup').RollupOptions} */
export default {
  input: 'src/index.ts',
  output: outputs,
  external: ['axios'],
  plugins: [
    replace({
      preventAssignment: true,
      values: {
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
        'process.env.SARDIS_WALLET_ID': 'undefined',
        'process.env.SARDIS_AGENT_ID': 'undefined',
      },
    }),
    json(),
    resolve({
      browser: true,
      preferBuiltins: false,
    }),
    commonjs(),
    typescript({
      tsconfig: './tsconfig.browser.json',
      declaration: false,
      declarationMap: false,
    }),
  ],
  onwarn(warning, warn) {
    // Suppress certain warnings
    if (warning.code === 'CIRCULAR_DEPENDENCY') return;
    if (warning.code === 'THIS_IS_UNDEFINED') return;
    warn(warning);
  },
};
