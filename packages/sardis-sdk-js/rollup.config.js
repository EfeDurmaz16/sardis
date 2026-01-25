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

/** @type {import('rollup').RollupOptions} */
export default {
  input: 'src/index.ts',
  output: [
    {
      file: 'dist/browser/index.js',
      format: 'esm',
      sourcemap: true,
      exports: 'named',
    },
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
      file: 'dist/browser/sardis.umd.js',
      format: 'umd',
      name: 'Sardis',
      sourcemap: true,
      globals: {
        axios: 'axios',
      },
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
    },
  ],
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
