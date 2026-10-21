import { afterEach, describe, expect, it, vi } from "vitest";

import { ForecastCardController } from "./forecast-card-controller";
import type { HassLike } from "./series";
import { withSingleHubRegistry } from "./fixtures/scenarioOutputs";

const smokeConfig = {
  type: "custom:haeo-forecast-card" as const,
  hub_entry_id: "hub-alpha",
  entities: ["sensor.haeo_grid_import_power"],
};

function smokeHass(states: HassLike["states"]): HassLike {
  return withSingleHubRegistry({ states }, "hub-alpha");
}

function forecastState(): HassLike["states"][string] {
  return {
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
  };
}

interface ForecastControllerInternals {
  ensureHostElements: () => void;
  observeCardResize: () => void;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
  renderCard: () => void;
}

function internals(controller: ForecastCardController): ForecastControllerInternals {
  return controller as unknown as ForecastControllerInternals;
}

describe("ForecastCardController", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("attaches shadow DOM and renders when connected", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 0);

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    expect(host.shadowRoot?.querySelector("#mount")).toBeTruthy();
    expect(host.shadowRoot?.querySelector(".chartContainer svg")).toBeTruthy();
  });

  it("ignores null hass updates and still renders", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 1);

    controller.setConfig({ type: "custom:haeo-forecast-card" });
    controller.setHass(null);
    controller.connected();

    expect(host.shadowRoot?.textContent).toContain("Configure a HAEO hub in the card editor");
  });

  it("cleans up pending pointer updates on disconnect", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 2);
    const cancelSpy = vi.spyOn(globalThis, "cancelAnimationFrame");

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    const svg = host.shadowRoot?.querySelector(".chartContainer svg");
    expect(svg).toBeTruthy();
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    controller.disconnected();

    expect(cancelSpy).toHaveBeenCalled();
  });

  it("dispatches ll-update when card size changes", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 3);
    const updates: Event[] = [];
    host.addEventListener("ll-update", (event) => {
      updates.push(event);
    });

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    expect(updates.length).toBeGreaterThan(0);
    const initialCount = updates.length;
    controller.setConfig({ ...smokeConfig, title: "Updated title" });
    expect(updates.length).toBe(initialCount);
  });

  it("reports card width from the mount element", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 4);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.id === "mount") {
        return new DOMRect(0, 0, 512, 0);
      }
      return new DOMRect(0, 0, 0, 0);
    });

    controller.connected();
    expect(controller.getCardWidth()).toBe(512);
    expect(controller.getCardSize()).toBeGreaterThan(0);
    expect(controller.getGridOptions().rows).toBeGreaterThanOrEqual(2);
  });

  it("skips redundant pointer updates inside the animation frame", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 5);

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    const svg = host.shadowRoot?.querySelector(".chartContainer svg");
    expect(svg).toBeTruthy();
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    svg?.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));
    svg?.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));

    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(resolve);
      });
    });

    expect(host.shadowRoot?.querySelector(".chartContainer svg")).toBeTruthy();
  });

  it("ignores duplicate host setup and resize observer edge cases", () => {
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

    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 6);
    const internal = internals(controller);

    internal.observeCardResize();
    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();
    internal.ensureHostElements();

    host.shadowRoot?.querySelector("#mount")?.remove();
    internal.observeCardResize();

    const callback = observerCallbacks.at(-1);
    expect(callback).toBeTruthy();
    callback?.([], {} as ResizeObserver);
    callback?.(
      [
        {
          contentRect: new DOMRect(0, 0, 0, 260),
          target: document.createElement("div"),
        } as unknown as ResizeObserverEntry,
      ],
      {} as ResizeObserver
    );

    globalThis.ResizeObserver = OriginalResizeObserver;
  });

  it("ignores invalid pointer events and redundant pointer updates", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 7);
    const internal = internals(controller);

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    const missingTarget = new PointerEvent("pointermove", { clientX: 1, clientY: 1 });
    Object.defineProperty(missingTarget, "currentTarget", { value: null });
    internal.onPointerMove(missingTarget);

    const svg = host.shadowRoot?.querySelector(".chartContainer svg");
    expect(svg).toBeTruthy();
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    svg?.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, clientX: 200, clientY: 120 }));
    svg?.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));
    svg?.dispatchEvent(new PointerEvent("pointerleave", { bubbles: true }));

    await new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(resolve);
      });
    });
  });

  it("returns early from render when the mount node is missing", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 8);
    const internal = internals(controller);

    controller.connected();
    host.shadowRoot?.querySelector("#mount")?.remove();
    expect(() => internal.renderCard()).not.toThrow();
  });

  it("throws when svg pointer mapping lacks a screen transform", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new ForecastCardController(host, 9);
    const internal = internals(controller);

    controller.setConfig(smokeConfig);
    controller.setHass(smokeHass({ "sensor.haeo_grid_import_power": forecastState() }));
    controller.connected();

    const svg = host.shadowRoot?.querySelector(".chartContainer svg") as SVGSVGElement | null;
    expect(svg).toBeTruthy();
    if (!svg) {
      throw new Error("Expected chart svg");
    }
    vi.spyOn(svg, "getScreenCTM").mockReturnValue(null);
    const event = new PointerEvent("pointermove", { clientX: 200, clientY: 120 });
    Object.defineProperty(event, "currentTarget", { value: svg });
    expect(() => internal.onPointerMove(event)).toThrow("Expected non-null SVG screen CTM for pointer mapping");
  });
});
