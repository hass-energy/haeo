// @vitest-environment jsdom

import { describe, expect, it } from "vitest";

import "../src/card";

describe("haeo-forecast-card smoke", () => {
  it("defines the custom element and accepts config", () => {
    const element = document.createElement("haeo-forecast-card");
    element.setConfig({
      type: "custom:haeo-forecast-card" as const,
      entities: ["sensor.haeo_grid_import_power"],
    });
    document.body.appendChild(element);

    expect(customElements.get("haeo-forecast-card")).toBeDefined();
    expect(element).toBeInstanceOf(HTMLElement);
  });

  it("renders svg when forecast data is provided", async () => {
    const element = document.createElement("haeo-forecast-card");
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
    await element.updateComplete;

    const svg = element.shadowRoot?.querySelector("svg");
    expect(svg).toBeTruthy();
  });
});
