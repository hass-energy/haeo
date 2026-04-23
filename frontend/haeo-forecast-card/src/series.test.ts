import { describe, expect, it } from "vitest";

import { normalizeSeries } from "./series";
import { loadScenarioHassState } from "./fixtures/scenarioOutputs";

describe("normalizeSeries", () => {
  it("builds typed arrays and inferred lane metadata", () => {
    const hass = {
      states: {
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: {
            forecast: [
              { time: "2026-03-14T01:00:00Z", value: 2.4 },
              { time: "2026-03-14T00:00:00Z", value: 1.2 },
            ],
            output_type: "power",
            output_name: "import_power",
            direction: "-",
            element_name: "Grid",
            unit_of_measurement: "kW",
          },
        },
      },
    };

    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });
    expect(output).toHaveLength(1);
    const first = output[0];
    expect(first).toBeDefined();
    if (!first) {
      return;
    }
    expect(first.lane).toBe("power");
    expect(first.sourceRole).toBe("output");
    expect(first.fieldName).toBe(null);
    expect(first.drawType).toBe("step");
    expect(first.times[0]).toBeLessThan(first.times[1] ?? Number.POSITIVE_INFINITY);
    expect(first.values[0]).toBe(1.2);
    expect(first.values[1]).toBe(2.4);
  });

  it("filters invalid rows and non-forecast entities", () => {
    const hass = {
      states: {
        "sensor.invalid": {
          entity_id: "sensor.invalid",
          attributes: {
            forecast: [{ time: "bad", value: "x" }],
          },
        },
        "sensor.no_forecast": {
          entity_id: "sensor.no_forecast",
          attributes: {},
        },
      },
    };

    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });
    expect(output).toHaveLength(0);
  });

  it("ingests scenario outputs emitted by HAEO integration", () => {
    const hass = loadScenarioHassState("scenario1");
    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });

    expect(output.length).toBeGreaterThanOrEqual(15);
    expect(output.some((series) => series.lane === "power")).toBe(true);
    expect(output.some((series) => series.lane === "price")).toBe(true);
    expect(output.some((series) => series.lane === "soc")).toBe(true);
    expect(output.some((series) => series.outputType === "power_flow")).toBe(false);
    expect(output.some((series) => series.outputName.includes("inverter_max_power"))).toBe(false);
    expect(output.some((series) => series.entityId === "number.battery_max_discharge_power")).toBe(false);
    expect(output.some((series) => series.outputName.endsWith("_power_active"))).toBe(false);
    expect(output.some((series) => series.sourceRole === "forecast")).toBe(true);
    expect(output.some((series) => series.sourceRole === "limit")).toBe(true);
    expect(output.every((series) => series.times.length === series.values.length)).toBe(true);
  });
});
