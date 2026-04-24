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
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            element_type: "grid",
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

    expect(output.length).toBeGreaterThanOrEqual(13);
    expect(output.some((series) => series.lane === "power")).toBe(true);
    expect(output.some((series) => series.lane === "price")).toBe(true);
    expect(output.some((series) => series.lane === "soc")).toBe(true);
    expect(output.some((series) => series.outputName.includes("inverter_max_power"))).toBe(false);
    expect(output.some((series) => series.outputName.endsWith("_power_active"))).toBe(false);
    expect(output.some((series) => series.sourceRole === "forecast")).toBe(true);
    expect(output.some((series) => series.sourceRole === "limit")).toBe(true);
    expect(output.every((series) => series.times.length === series.values.length)).toBe(true);
  });

  it("coerces numeric and string attribute values", () => {
    const hass = {
      states: {
        "sensor.coerce": {
          entity_id: "sensor.coerce",
          attributes: {
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: "1.5" },
              { time: "2026-03-14T01:00:00Z", value: 2 },
            ],
            field_type: "power",
            output_name: "power",
            direction: "-",
            element_type: "load",
            element_name: "Load",
            unit_of_measurement: "kW",
            priority: "3",
          },
        },
      },
    };
    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });
    expect(output).toHaveLength(1);
    const first = output[0]!;
    expect(first.values[0]).toBe(1.5);
    expect(first.values[1]).toBe(2);
    expect(first.priority).toBe(3);
  });

  it("handles state_of_charge output type as line draw", () => {
    const hass = {
      states: {
        "sensor.soc": {
          entity_id: "sensor.soc",
          attributes: {
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 50 },
              { time: "2026-03-14T01:00:00Z", value: 60 },
            ],
            field_type: "state_of_charge",
            output_name: "state_of_charge",
            element_type: "battery",
            element_name: "Battery",
            unit_of_measurement: "%",
          },
        },
      },
    };
    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });
    expect(output).toHaveLength(1);
    expect(output[0]!.drawType).toBe("line");
    expect(output[0]!.lane).toBe("soc");
  });

  it("uses friendly_name as label when present", () => {
    const hass = {
      states: {
        "sensor.power": {
          entity_id: "sensor.power",
          attributes: {
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1 },
              { time: "2026-03-14T01:00:00Z", value: 2 },
            ],
            field_type: "power",
            output_name: "power",
            direction: "-",
            element_type: "load",
            element_name: "Test Load",
            unit_of_measurement: "kW",
            friendly_name: "My Custom Name",
          },
        },
      },
    };
    const output = normalizeSeries(hass, { type: "custom:haeo-forecast-card" });
    expect(output).toHaveLength(1);
    expect(output[0]!.label).toBe("My Custom Name");
  });

  it("returns empty for null hass", () => {
    expect(normalizeSeries(null, { type: "custom:haeo-forecast-card" })).toHaveLength(0);
  });
});
