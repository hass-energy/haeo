import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { JSDOM } from "jsdom";

const rootDir = resolve(import.meta.dirname, "..");
const workspaceRoot = resolve(rootDir, "..", "..");
const bundlePath = resolve(workspaceRoot, "custom_components", "haeo", "www", "haeo-forecast-card.min.js");
const outputDir = resolve(rootDir, "previews");
const scenarioPath = resolve(workspaceRoot, "tests", "scenarios", "scenario4", "outputs.json");
const outputSvg = resolve(outputDir, "card-preview.svg");

function pickEntities(states) {
  const preferred = [
    "sensor.grid_import_power",
    "sensor.grid_export_power",
    "sensor.solar_power",
    "number.solar_forecast",
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
  if (selected.length > 0) {
    return selected;
  }
  return Object.values(states)
    .filter((state) => {
      const forecast = state?.attributes?.forecast;
      return Array.isArray(forecast) && forecast.length > 1;
    })
    .map((state) => state.entity_id);
}

async function main() {
  await mkdir(outputDir, { recursive: true });

  const outputsFile = await readFile(scenarioPath, "utf-8");
  const states = JSON.parse(outputsFile);
  const entities = pickEntities(states);

  const dom = new JSDOM("<!doctype html><html><body></body></html>", {
    url: "http://localhost/",
    pretendToBeVisual: true,
  });
  const { window } = dom;

  globalThis.window = window;
  globalThis.document = window.document;
  globalThis.customElements = window.customElements;
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(Date.now()), 16);
  globalThis.cancelAnimationFrame = (id) => clearTimeout(id);

  await import(pathToFileURL(bundlePath).href);

  const element = window.document.createElement("haeo-forecast-card");
  element.setConfig({
    type: "custom:haeo-forecast-card",
    title: "HAEO card preview",
    entities,
    height: 420,
    animation_mode: "off",
  });
  element.hass = { states };
  window.document.body.appendChild(element);

  await new Promise((resolvePromise) => setTimeout(resolvePromise, 50));

  const svg = element.shadowRoot?.querySelector("svg");
  const style = element.shadowRoot?.querySelector("style")?.textContent ?? "";
  if (!svg) {
    throw new Error("Unable to render forecast card SVG");
  }

  const content = `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="${svg.getAttribute("viewBox") ?? "0 0 1200 420"}">\n<style>${style}</style>\n${svg.innerHTML}\n</svg>\n`;
  await writeFile(outputSvg, content, "utf-8");
  process.stdout.write(`wrote ${outputSvg}\n`);
}

await main();
