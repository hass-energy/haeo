import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { build, context } from "esbuild";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const rootDir = resolve(__dirname, "..");
const workspaceRoot = resolve(rootDir, "..", "..");
const outDir = resolve(workspaceRoot, "custom_components", "haeo", "www");
const outFile = resolve(outDir, "haeo-forecast-card.min.js");
const watch = process.argv.includes("--watch");

const shared = {
  absWorkingDir: rootDir,
  entryPoints: [resolve(rootDir, "src", "index.ts")],
  outfile: outFile,
  bundle: true,
  format: "esm",
  target: "es2022",
  sourcemap: true,
  legalComments: "none",
  minify: true,
  loader: { ".css": "text" },
};

const topologyOutFile = resolve(rootDir, "dist", "render-topology-svg.mjs");

await mkdir(outDir, { recursive: true });
await mkdir(resolve(rootDir, "dist"), { recursive: true });

if (watch) {
  const ctx = await context(shared);
  await ctx.watch();
  await ctx.rebuild();
  process.stdout.write(`watching ${outFile}\n`);

  const topoCtx = await context({
    absWorkingDir: rootDir,
    entryPoints: [resolve(rootDir, "src", "topology", "render-svg.ts")],
    outfile: topologyOutFile,
    bundle: true,
    format: "esm",
    target: "node20",
    platform: "node",
    sourcemap: false,
    legalComments: "none",
    minify: false,
  });
  await topoCtx.watch();
  await topoCtx.rebuild();
  process.stdout.write(`watching ${topologyOutFile}\n`);
} else {
  await build(shared);
  process.stdout.write(`built ${outFile}\n`);

  await build({
    absWorkingDir: rootDir,
    entryPoints: [resolve(rootDir, "src", "topology", "render-svg.ts")],
    outfile: topologyOutFile,
    bundle: true,
    format: "esm",
    target: "node20",
    platform: "node",
    sourcemap: false,
    legalComments: "none",
    minify: false,
  });
  process.stdout.write(`built ${topologyOutFile}\n`);
}
