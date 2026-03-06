import { defineConfig } from "vite";
import path from "path";

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(__dirname, "src/embed/sardis-checkout.ts"),
      name: "SardisCheckout",
      formats: ["iife"],
      fileName: () => "sardis-checkout.js",
    },
    outDir: "dist/embed",
    emptyOutDir: true,
  },
});
