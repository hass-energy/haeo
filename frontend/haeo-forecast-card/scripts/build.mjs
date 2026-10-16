import { mkdir, readdir, unlink } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { build as rolldownBuild, watch as rolldownWatch } from "rolldown";

import rolldownConfig from "../rolldown.config.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, "..");
const workspaceRoot = resolve(rootDir, "..", "..");
const outDir = resolve(workspaceRoot, "custom_components", "haeo", "www");
const topologyOutFile = resolve(rootDir, "dist", "render-topology-svg.mjs");
const watch = process.argv.includes("--watch");

const CARD_FILE_PREFIXES = ["haeo-forecast-card", "haeo-topology-card"];

async function cleanCardOutputDir() {
  await mkdir(outDir, { recursive: true });
  const entries = await readdir(outDir);
  await Promise.all(
    entries
      .filter((name) => CARD_FILE_PREFIXES.some((prefix) => name.startsWith(prefix)))
      .map((name) => unlink(resolve(outDir, name)))
  );
}

// Card filenames carry a content hash, so list what was actually emitted.
async function builtFiles() {
  const entries = await readdir(outDir);
  const cardFiles = entries
    .filter((name) => CARD_FILE_PREFIXES.some((prefix) => name.startsWith(prefix)))
    .sort()
    .map((name) => resolve(outDir, name));
  return [...cardFiles, topologyOutFile];
}

if (watch) {
  await cleanCardOutputDir();
  const watcher = await rolldownWatch(rolldownConfig);
  watcher.on("event", (event) => {
    if (event.code === "BUNDLE_END") {
      void builtFiles().then((files) => {
        for (const file of files) {
          process.stdout.write(`built ${file}\n`);
        }
      });
    }
    if (event.code === "ERROR") {
      process.stderr.write(`${event.error}\n`);
    }
  });
  process.stdout.write(`watching ${outDir}\n`);
} else {
  await cleanCardOutputDir();
  await rolldownBuild(rolldownConfig);
  for (const file of await builtFiles()) {
    process.stdout.write(`built ${file}\n`);
  }
}
