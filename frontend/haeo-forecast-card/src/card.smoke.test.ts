import { afterEach, describe, expect, it, vi } from "vitest";

import "./card";

interface HaeoCardElement extends HTMLElement {
  setConfig: (config: { type: "custom:haeo-forecast-card"; entities?: string[] }) => void;
  hass: unknown;
  getCardSize: () => number;
  getGridOptions: () => {
    rows: number;
    min_rows: number;
    columns: "full";
  };
  getCardWidth: () => number;
}

describe("haeo-forecast-card smoke", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defines the custom element and accepts config", () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig({
      type: "custom:haeo-forecast-card" as const,
      entities: ["sensor.haeo_grid_import_power"],
    });
    document.body.appendChild(element);

    expect(customElements.get("haeo-forecast-card")).toBeDefined();
    expect(element).toBeInstanceOf(HTMLElement);
  });

  it("renders svg when forecast data is provided", async () => {
    const element = document.createElement("haeo-forecast-card") as HaeoCardElement;
    element.setConfig({
      type: "custom:haeo-forecast-card" as const,
      entities: ["sensor.haeo_grid_import_power"],
    });
    element.hass = {
      states: {
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: {
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            element_name: "Grid",
            unit_of_measurement: "kW",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
              { time: "2026-03-14T00:10:00Z", value: 1.5 },
            ],
          },
        },
      },
    };
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });

    const svg = element.shadowRoot?.querySelector("svg");
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
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });
    expect(element.shadowRoot?.textContent).toContain("No forecast data found");
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
    element.setConfig({
      type: "custom:haeo-forecast-card",
    });
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });

    const chartContainer = element.shadowRoot?.querySelector(".chartContainer");
    expect(chartContainer).toBeTruthy();
    expect(element.getCardSize()).toBe(14);
    expect(element.getGridOptions()).toEqual({ rows: 11, min_rows: 10, columns: "full" });

    const callback = observerCallbacks[0];
    expect(callback).toBeTruthy();
    if (!callback) {
      return;
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

    element.remove();
    globalThis.ResizeObserver = OriginalResizeObserver;
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
    element.setConfig({
      type: "custom:haeo-forecast-card",
    });
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });

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
});
