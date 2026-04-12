import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  root: "frontend",
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
