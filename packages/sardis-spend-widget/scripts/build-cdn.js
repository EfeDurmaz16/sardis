/**
 * CDN build script — outputs a self-contained UMD bundle with React included.
 *
 * Usage:
 *   node scripts/build-cdn.js
 *
 * Output:
 *   dist/widget.js  — drop-in <script> tag for non-React sites
 *
 * Embed:
 *   <script src="https://sardis.sh/widget.js"></script>
 *   <sardis-spend-widget agent-id="agt_..." api-key="sk_..."></sardis-spend-widget>
 */

import { build } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

await build({
  root,
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": '"production"',
  },
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: path.resolve(root, "src/cdn-entry.tsx"),
      name: "SardisSpendWidget",
      formats: ["umd"],
      fileName: () => "widget.js",
    },
    rollupOptions: {
      external: [],
    },
    minify: "terser",
  },
});

console.log("CDN bundle built: dist/widget.js");
