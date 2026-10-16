/**
 * Locate a built card bundle entry in the integration's static directory.
 *
 * Entry filenames carry a content hash (`haeo-forecast-card.entry.<hash>.js`), so there
 * is no fixed name left to import. Discover the entry the way the integration does at
 * runtime: list the directory and pick the file marked `.entry.`.
 */
import { readdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const workspaceRoot = resolve(scriptsDir, "..", "..", "..");

export const CARD_OUT_DIR = resolve(workspaceRoot, "custom_components", "haeo", "www");

const BUILD_HINT = "run: npm --prefix frontend/haeo-forecast-card run build";

/**
 * @param {string} cardPrefix Card bundle prefix, e.g. `haeo-forecast-card`.
 * @returns {Promise<string>} Absolute path to that card's entry bundle.
 */
export async function resolveCardEntry(cardPrefix) {
  let names;
  try {
    names = await readdir(CARD_OUT_DIR);
  } catch {
    throw new Error(`No card bundle directory at ${CARD_OUT_DIR} — ${BUILD_HINT}`);
  }
  const entries = names.filter((name) => name.startsWith(`${cardPrefix}.entry.`) && name.endsWith(".js")).sort();
  if (entries.length === 0) {
    throw new Error(`No ${cardPrefix} entry bundle in ${CARD_OUT_DIR} — ${BUILD_HINT}`);
  }
  if (entries.length > 1) {
    throw new Error(`Multiple ${cardPrefix} entry bundles in ${CARD_OUT_DIR}: ${entries.join(", ")} — ${BUILD_HINT}`);
  }
  return resolve(CARD_OUT_DIR, entries[0]);
}
