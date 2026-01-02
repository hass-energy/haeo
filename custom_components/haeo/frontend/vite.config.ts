import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: "/haeo_static/",
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "dist",
    // Generate source maps for debugging
    sourcemap: true,
    rollupOptions: {
      output: {
        // Keep consistent filenames for caching
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name].[ext]",
      },
    },
  },
  server: {
    // Proxy API requests to Home Assistant during development
    proxy: {
      "/api": {
        target: "http://localhost:8123",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
