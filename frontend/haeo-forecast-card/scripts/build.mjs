import { mkdir, readdir, unlink } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { build as rolldownBuild, watch as rolldownWatch } from "rolldown";

import rolldownConfig from "../rolldown.config.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const workspaceRoot = resolve(rootDir, "..", "..");
const outDir = resolve(workspaceRoot, "custom_components", "haeo", "www");
const outFile = resolve(outDir, "haeo-forecast-card.min.js");
const topologyOutFile = resolve(rootDir, "dist", "render-topology-svg.mjs");
const watch = process.argv.includes("--watch");

async function cleanCardOutputDir() {
  await mkdir(outDir, { recursive: true });
  const entries = await readdir(outDir);
  await Promise.all(
    entries.filter((name) => name.startsWith("haeo-forecast-card")).map((name) => unlink(resolve(outDir, name)))
  );
}

if (watch) {
  await cleanCardOutputDir();
  const watcher = await rolldownWatch(rolldownConfig);
  watcher.on("event", (event) => {
    if (event.code === "BUNDLE_END") {
      process.stdout.write(`built ${outFile}\n`);
      process.stdout.write(`built ${topologyOutFile}\n`);
    }
    if (event.code === "ERROR") {
      process.stderr.write(`${event.error}\n`);
    }
  });
  process.stdout.write(`watching ${outFile}\n`);
  process.stdout.write(`watching ${topologyOutFile}\n`);
} else {
  await cleanCardOutputDir();
  await rolldownBuild(rolldownConfig);
  process.stdout.write(`built ${outFile}\n`);
  process.stdout.write(`built ${topologyOutFile}\n`);
}
