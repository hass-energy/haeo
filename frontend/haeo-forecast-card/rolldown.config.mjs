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

const browserTreeshake = {
  // Shake unused exports from dependencies, but keep side-effect imports in app code.
  moduleSideEffects: (id, external) => {
    if (id.endsWith(".css")) {
      return true;
    }
    return !external;
  },
};

// Each card is built as its own independent bundle and registered as its own
// Home Assistant Lovelace resource, so a stale or missing copy of one card can
// never break registration of the other.
//
// Within a card bundle, the registered entry is a tiny element that calls
// `customElements.define` immediately, with no heavy imports. The heavy
// rendering controller (preact, MobX, ELK) is split into a lazily-imported
// chunk so element registration never waits on it to download or evaluate.
// Chunk filenames are stable (no content hash) and prefixed per card to avoid
// collisions and repo churn.
export default defineConfig([
  {
    input: resolve(rootDir, "src/index.ts"),
    platform: "browser",
    plugins: [cssTextPlugin()],
    treeshake: browserTreeshake,
    output: {
      dir: outDir,
      format: "esm",
      entryFileNames: "haeo-forecast-card.min.js",
      chunkFileNames: "haeo-forecast-card.[name].js",
      sourcemap: false,
      minify: true,
      codeSplitting: true,
    },
  },
  {
    input: resolve(rootDir, "src/topology-entry.ts"),
    platform: "browser",
    plugins: [cssTextPlugin()],
    treeshake: browserTreeshake,
    output: {
      dir: outDir,
      format: "esm",
      entryFileNames: "haeo-topology-card.min.js",
      chunkFileNames: "haeo-topology-card.[name].js",
      sourcemap: false,
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
