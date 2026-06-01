import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "rolldown";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname);
const workspaceRoot = resolve(rootDir, "..", "..");
const outDir = resolve(workspaceRoot, "custom_components", "haeo", "www");
const distDir = resolve(rootDir, "dist");

/** Import `.css` files as string literals (matches the previous esbuild `text` loader). */
function cssTextPlugin() {
  return {
    name: "css-text",
    transform(code, id) {
      if (!id.endsWith(".css")) {
        return null;
      }
      return {
        code: `export default ${JSON.stringify(code)};`,
        moduleType: "js",
      };
    },
  };
}

export default defineConfig([
  {
    input: resolve(rootDir, "src/index.ts"),
    platform: "browser",
    plugins: [cssTextPlugin()],
    treeshake: {
      // Shake unused exports from dependencies, but keep side-effect imports in app code.
      moduleSideEffects: (id, external) => {
        if (id.endsWith(".css")) {
          return true;
        }
        return !external;
      },
    },
    output: {
      dir: outDir,
      format: "esm",
      entryFileNames: "haeo-forecast-card.min.js",
      chunkFileNames: "haeo-forecast-card-[name]-[hash].js",
      sourcemap: true,
      minify: true,
      codeSplitting: true,
    },
  },
  {
    input: resolve(rootDir, "src/topology/render-svg.ts"),
    platform: "node",
    output: {
      dir: distDir,
      format: "esm",
      entryFileNames: "render-topology-svg.mjs",
      sourcemap: false,
      minify: false,
    },
  },
]);
