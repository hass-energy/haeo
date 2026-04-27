/**
 * Render HAEO forecast card as SVG from scenario outputs.
 *
 * Usage: node export-scenario-svg.mjs <outputs.json> <output.svg>
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { pathToFileURL } from "node:url";
let JSDOM;
try {
  ({ JSDOM } = await import("jsdom"));
} catch {
  console.error("Missing jsdom — run: npm --prefix frontend/haeo-forecast-card ci");
  process.exit(1);
}

const rootDir = resolve(import.meta.dirname, "..");
const workspaceRoot = resolve(rootDir, "..", "..");
const bundlePath = resolve(workspaceRoot, "custom_components", "haeo", "www", "haeo-forecast-card.min.js");

const CARD_WIDTH = 1200;
const CARD_HEIGHT = 500;

function pickEntities(states) {
  const preferred = [
    "sensor.grid_import_power",
    "sensor.grid_export_power",
    "sensor.solar_power",
    "number.solar_forecast",
    "sensor.load_power",
    "sensor.constant_load_power",
    "sensor.battery_charge_power",
    "sensor.battery_discharge_power",
    "number.grid_import_price",
    "number.grid_export_price",
    "sensor.battery_state_of_charge",
  ];

  const selected = preferred.filter((entityId) => {
    const state = states[entityId];
    const forecast = state?.attributes?.forecast;
    return Array.isArray(forecast) && forecast.length > 1;
  });

  if (selected.length > 0) return selected;

  return Object.values(states)
    .filter((state) => {
      const forecast = state?.attributes?.forecast;
      return Array.isArray(forecast) && forecast.length > 1;
    })
    .map((state) => state.entity_id);
}

function setupDom() {
  const dom = new JSDOM("<!doctype html><html><body></body></html>", {
    url: "http://localhost/",
    pretendToBeVisual: true,
  });
  const { window } = dom;

  globalThis.window = window;
  globalThis.document = window.document;
  globalThis.customElements = window.customElements;
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 16);
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
  globalThis.IntersectionObserver = class {
    observe() {}
    disconnect() {}
  };
  globalThis.ResizeObserver = class {
    constructor(callback) {
      this._callback = callback;
    }
    observe(target) {
      setTimeout(
        () =>
          this._callback([
            {
              target,
              contentRect: { width: CARD_WIDTH, height: CARD_HEIGHT, x: 0, y: 0, top: 0, left: 0 },
            },
          ]),
        10
      );
    }
    disconnect() {}
  };

  return window;
}

async function renderCard(window, states, entities) {
  await import(pathToFileURL(bundlePath).href);

  const element = window.document.createElement("haeo-forecast-card");
  element.getBoundingClientRect = () => ({
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: CARD_WIDTH,
    bottom: CARD_HEIGHT,
  });

  element.setConfig({
    type: "custom:haeo-forecast-card",
    entities,
    height: CARD_HEIGHT,
    animation_mode: "off",
  });
  element.hass = { states };
  window.document.body.appendChild(element);

  await new Promise((r) => setTimeout(r, 500));

  // Find the main chart SVG (contains plotViewport or large content)
  const svgs = element.shadowRoot?.querySelectorAll("svg") ?? [];
  for (const svg of svgs) {
    if (
      svg.querySelector(".plotViewport") ||
      (svg.innerHTML.length > 1000 && !svg.getAttribute("viewBox")?.startsWith("0 0 24"))
    ) {
      return { svg, style: element.shadowRoot?.querySelector("style")?.textContent ?? "" };
    }
  }
  return null;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node export-scenario-svg.mjs <outputs.json> <output.svg>");
    process.exit(1);
  }

  const [outputsPath, svgPath] = args;
  const states = JSON.parse(await readFile(resolve(outputsPath), "utf-8"));
  const entities = pickEntities(states);

  if (entities.length === 0) {
    console.error("No entities with forecast data found");
    process.exit(1);
  }

  const window = setupDom();
  const result = await renderCard(window, states, entities);

  if (!result) {
    console.error("Unable to render forecast card chart SVG");
    process.exit(1);
  }

  const { svg, style } = result;
  const content = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${CARD_WIDTH} ${CARD_HEIGHT}" width="${CARD_WIDTH}" height="${CARD_HEIGHT}">`,
    `<style>${style}</style>`,
    svg.innerHTML,
    "</svg>",
    "",
  ].join("\n");

  await mkdir(dirname(resolve(svgPath)), { recursive: true });
  await writeFile(resolve(svgPath), content, "utf-8");
  process.stdout.write(`wrote ${resolve(svgPath)}\n`);
}

await main();
