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
  const values = Object.values(states);
  const wanted = [];
  const categories = {
    power: 0,
    price: 0,
    state_of_charge: 0,
    shadow_price: 0,
  };

  for (const state of values) {
    const attrs = state?.attributes ?? {};
    if (!Array.isArray(attrs.forecast) || attrs.forecast.length < 2) {
      continue;
    }
    const outputType = String(attrs.output_type ?? "");
    if (outputType in categories) {
      if (outputType === "power" && categories.power < 4) {
        categories.power += 1;
        wanted.push(state.entity_id);
      } else if (outputType === "price" && categories.price < 3) {
        categories.price += 1;
        wanted.push(state.entity_id);
      } else if (outputType === "state_of_charge" && categories.state_of_charge < 2) {
        categories.state_of_charge += 1;
        wanted.push(state.entity_id);
      } else if (outputType === "shadow_price" && categories.shadow_price < 2) {
        categories.shadow_price += 1;
        wanted.push(state.entity_id);
      }
    }
  }

  return wanted;
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
