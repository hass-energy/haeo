import { afterEach, describe, expect, it, vi } from "vitest";

import type { HassLike } from "./series";
import { withSingleHubRegistry } from "./fixtures/scenarioOutputs";
import "./card";

interface ForecastCardConstructor {
  getStubConfig: (hass?: HassLike) => { title?: string; hub_entry_id?: string };
}

interface HaeoCardElement extends HTMLElement {
  setConfig: (config: { type: "custom:haeo-forecast-card"; hub_entry_id?: string; entities?: string[] }) => void;
  hass: unknown;
  getCardSize: () => number;
  getGridOptions: () => {
    rows: number;
    min_rows: number;
    columns: "full";
  };
  getCardWidth: () => number;
}

const smokeConfig = {
  type: "custom:haeo-forecast-card" as const,
  hub_entry_id: "hub-alpha",
  entities: ["sensor.haeo_grid_import_power"],
};

/**
 * Wait for the lazily-imported rendering controller to load and flush its
 * synchronous render. The element registers instantly but defers heavy
 * rendering behind a dynamic import, so tests must await that load.
 */
async function waitForController(): Promise<void> {
  await import("./forecast-card-controller");
  await new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

function smokeHass(states: HassLike["states"]): HassLike {
  return withSingleHubRegistry({ states }, "hub-alpha");
}

describe("haeo-forecast-card smoke", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defines the custom element and accepts config", () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig(smokeConfig);
    document.body.appendChild(element);

    expect(customElements.get("haeo-forecast-card")).toBeDefined();
    expect(element).toBeInstanceOf(HTMLElement);
  });

  it("reports fallback sizing before the rendering controller loads", () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    expect(element.getCardSize()).toBe(6);
    expect(element.getGridOptions()).toEqual({ rows: 5, min_rows: 4, columns: "full" });
  });

  it("renders svg when hass is set after connect", async () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    document.body.appendChild(element);
    element.setConfig(smokeConfig);
    await waitForController();
    expect(element.shadowRoot?.querySelector(".chartContainer svg")).toBeFalsy();

    element.hass = smokeHass({
      "sensor.haeo_grid_import_power": {
        entity_id: "sensor.haeo_grid_import_power",
        attributes: {
          field_type: "power",
          output_name: "import_power",
          direction: "-",
          element_name: "Grid",
          element_type: "grid",
          unit_of_measurement: "kW",
          forecast: [
            { time: "2026-03-14T00:00:00Z", value: 1.0 },
            { time: "2026-03-14T00:05:00Z", value: 2.0 },
            { time: "2026-03-14T00:10:00Z", value: 1.5 },
          ],
        },
      },
    });
    await waitForController();

    expect(element.shadowRoot?.querySelector(".chartContainer svg")).toBeTruthy();
    element.remove();
  });

  it("renders svg when forecast data is provided", async () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig(smokeConfig);
    element.hass = smokeHass({
      "sensor.haeo_grid_import_power": {
        entity_id: "sensor.haeo_grid_import_power",
        attributes: {
          field_type: "power",
          output_name: "import_power",
          direction: "-",
          element_name: "Grid",
          element_type: "grid",
          unit_of_measurement: "kW",
          forecast: [
            { time: "2026-03-14T00:00:00Z", value: 1.0 },
            { time: "2026-03-14T00:05:00Z", value: 2.0 },
            { time: "2026-03-14T00:10:00Z", value: 1.5 },
          ],
        },
      },
    });
    document.body.appendChild(element);
    await waitForController();

    const svg = element.shadowRoot?.querySelector(".chartContainer svg");
    expect(svg).toBeTruthy();
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    svg?.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));
    element.remove();
  });

  it("renders empty state when hass data is not set", async () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig({
      type: "custom:haeo-forecast-card",
    });
    document.body.appendChild(element);
    await waitForController();
    expect(element.shadowRoot?.textContent).toContain("Configure a HAEO hub in the card editor");
    element.remove();
  });

  it("sizes the card from full card width when the chart is narrower", async () => {
    const observerCallbacks: ResizeObserverCallback[] = [];
    const OriginalResizeObserver = globalThis.ResizeObserver;
    globalThis.ResizeObserver = class ResizeObserver {
      constructor(callback: ResizeObserverCallback) {
        observerCallbacks.push(callback);
      }
      observe(): void {
        return undefined;
      }
      unobserve(): void {
        return undefined;
      }
      disconnect(): void {
        return undefined;
      }
    };
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.id === "mount") {
        return new DOMRect(0, 0, 520, 0);
      }
      if (this.classList.contains("chartContainer")) {
        return new DOMRect(0, 0, 320, 260);
      }
      return new DOMRect(0, 0, 520, 0);
    });

    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    try {
      element.setConfig(smokeConfig);
      element.hass = smokeHass({
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: {
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            element_name: "Grid",
            element_type: "grid",
            unit_of_measurement: "kW",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
            ],
          },
        },
      });
      document.body.appendChild(element);
      await waitForController();

      const chartContainer = element.shadowRoot?.querySelector(".chartContainer");
      expect(chartContainer).toBeTruthy();
      expect(element.getCardSize()).toBe(14);
      expect(element.getGridOptions()).toEqual({ rows: 11, min_rows: 10, columns: "full" });

      const callback = observerCallbacks[0];
      expect(callback).toBeTruthy();
      if (!callback) {
        throw new Error("Expected ResizeObserver callback");
      }
      callback(
        [
          {
            contentRect: new DOMRect(0, 0, 300, 260),
            target: chartContainer!,
          } as ResizeObserverEntry,
        ],
        {} as ResizeObserver
      );
      expect(element.getCardSize()).toBe(14);
      callback(
        [
          {
            contentRect: new DOMRect(0, 0, 300, 0),
            target: chartContainer!,
          } as ResizeObserverEntry,
        ],
        {} as ResizeObserver
      );
      expect(element.getCardSize()).toBe(14);
    } finally {
      element.remove();
      globalThis.ResizeObserver = OriginalResizeObserver;
    }
  });

  it("uses responsive height when initial chart height is unavailable", async () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.id === "mount") {
        return new DOMRect(0, 0, 520, 0);
      }
      if (this.classList.contains("chartContainer")) {
        return new DOMRect(0, 0, 320, 0);
      }
      return new DOMRect(0, 0, 520, 0);
    });

    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig(smokeConfig);
    document.body.appendChild(element);
    await waitForController();

    expect(element.getCardSize()).toBe(14);
    element.remove();
  });

  it("falls back to the host width before the shadow mount exists", () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    const bounds = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 480, 0));

    expect(element.getCardWidth()).toBe(480);

    bounds.mockReturnValue(new DOMRect(0, 0, 0, 0));
    expect(element.getCardWidth()).toBe(640);
  });

  it("builds stub config with the first discovered hub", () => {
    const ctor = customElements.get("haeo-forecast-card");
    if (ctor === undefined) {
      throw new Error("Expected haeo-forecast-card custom element");
    }
    const cardClass = ctor as unknown as ForecastCardConstructor;
    expect(cardClass.getStubConfig()).toEqual({ title: "HAEO forecast" });
    expect(
      cardClass.getStubConfig({
        states: {},
        entities: {
          "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
        },
        devices: {
          "dev-alpha": { config_entries: ["hub-alpha"] },
        },
      })
    ).toEqual({ title: "HAEO forecast", hub_entry_id: "hub-alpha" });
  });

  it("exposes the shared config form", () => {
    const ctor = customElements.get("haeo-forecast-card");
    if (ctor === undefined) {
      throw new Error("Expected haeo-forecast-card custom element");
    }
    const cardClass = ctor as unknown as ForecastCardConstructor & {
      getConfigForm: () => { schema: Array<{ name: string }> };
    };
    expect(cardClass.getConfigForm().schema.some((field) => field.name === "hub_entry_id")).toBe(true);
  });
});
