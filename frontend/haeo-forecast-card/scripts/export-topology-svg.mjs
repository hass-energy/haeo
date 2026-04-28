/**
 * Render HAEO network topology as SVG from serialized topology JSON.
 *
 * Usage: node export-topology-svg.mjs <topology.json> <output.svg>
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";

const rootDir = resolve(import.meta.dirname, "..");
const bundlePath = resolve(rootDir, "dist", "render-topology-svg.mjs");

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node export-topology-svg.mjs <topology.json> <output.svg>");
    process.exit(1);
  }

  const [topologyPath, svgPath] = args;

  let renderTopologySvg;
  try {
    ({ renderTopologySvg } = await import(pathToFileURL(bundlePath).href));
  } catch {
    console.error(`Missing topology bundle — run: npm --prefix frontend/haeo-forecast-card run build`);
    process.exit(1);
  }

  const topology = JSON.parse(await readFile(resolve(topologyPath), "utf-8"));

  const svg = await renderTopologySvg(topology);

  await mkdir(dirname(resolve(svgPath)), { recursive: true });
  await writeFile(resolve(svgPath), svg, "utf-8");
  process.stdout.write(`wrote ${resolve(svgPath)}\n`);
}

await main();
