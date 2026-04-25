// @ts-check
import { defineConfig } from "astro/config";

export default defineConfig({
  prefetch: {
    // Prefetch every internal link on viewport by default — fast SPA-like feel
    // with Astro's View Transitions.
    prefetchAll: true,
    defaultStrategy: "viewport",
  },
  vite: {
    build: {
      cssMinify: "esbuild",
    },
  },
});
