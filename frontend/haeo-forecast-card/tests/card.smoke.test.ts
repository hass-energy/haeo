import { describe, expect, it } from "vitest";

import "../src/card";

interface HaeoCardElement extends HTMLElement {
  setConfig: (config: { type: "custom:haeo-forecast-card"; entities?: string[] }) => void;
  hass: unknown;
}

describe("haeo-forecast-card smoke", () => {
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
            output_type: "power",
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
});
