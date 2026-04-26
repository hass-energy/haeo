import { describe, expect, it } from "vitest";

import { tooltipSection, tooltipDisplayLabel, buildTooltipRows } from "./tooltip-helpers";
import type { ForecastSeries } from "./types";

function makeSeries(overrides: Partial<ForecastSeries> & { key: string }): ForecastSeries {
  return {
    entityId: "sensor.test",
    label: "Test",
    elementName: "Test",
    elementType: "grid",
    outputName: "import_power",
    outputType: "power",
    direction: "-",
    sourceRole: "output",
    configMode: null,
    fixed: false,
    priority: null,
    lane: "power",
    drawType: "step",
    unit: "kW",
    color: "#000",
    times: new Float64Array([100, 200, 300]),
    values: new Float64Array([1, 2, 3]),
    ...overrides,
  };
}

describe("tooltipSection", () => {
  it("returns price for price lane", () => {
    expect(tooltipSection(makeSeries({ key: "a", lane: "price", outputType: "price" }))).toBe("price");
  });

  it("returns soc for soc lane", () => {
    expect(tooltipSection(makeSeries({ key: "a", lane: "soc", outputType: "state_of_charge" }))).toBe("soc");
  });

  it("returns consumed for consumption utilization", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "-", outputType: "power" }))).toBe("consumed");
  });

  it("returns produced for production utilization", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "+", outputType: "power" }))).toBe("produced");
  });

  it("returns available for production potential (config input)", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "+", outputType: "power", sourceRole: "forecast" }))).toBe(
      "available"
    );
  });

  it("returns possible for consumption potential (power_limit)", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "-", outputType: "power", sourceRole: "limit" }))).toBe(
      "possible"
    );
  });
});

describe("tooltipDisplayLabel", () => {
  it("returns plain label for price series", () => {
    const s = makeSeries({ key: "a", lane: "price", outputName: "import_price", label: "Grid" });
    expect(tooltipDisplayLabel(s, "price", false)).toBe("Grid");
  });

  it("returns name without qualifier for non-directional price", () => {
    const s = makeSeries({ key: "a", lane: "price", outputName: "spot_price", label: "Grid" });
    expect(tooltipDisplayLabel(s, "price", false)).toBe("Grid");
  });

  it("returns plain label for power series", () => {
    const s = makeSeries({ key: "a", label: "Solar", outputName: "power" });
    expect(tooltipDisplayLabel(s, "produced", false)).toBe("Solar");
  });

  it("uses en-dash and output name for duplicate labels", () => {
    const s = makeSeries({ key: "a", label: "Grid", outputName: "import_power" });
    expect(tooltipDisplayLabel(s, "consumed", true)).toBe("Grid \u2013 import power");
  });
});

describe("buildTooltipRows", () => {
  it("builds rows sorted by lane then magnitude", () => {
    const produced = makeSeries({
      key: "solar:power",
      direction: "+",
      outputType: "power",
      label: "Solar",
      values: new Float64Array([3, 2, 1]),
    });
    const consumed = makeSeries({
      key: "grid:import_power",
      direction: "-",
      outputType: "power",
      label: "Grid",
      values: new Float64Array([1, 2, 3]),
    });
    const indices = new Map([
      ["solar:power", 0],
      ["grid:import_power", 0],
    ]);
    const rows = buildTooltipRows([produced, consumed], indices, (_series, value) => value);
    expect(rows.length).toBe(2);
    // Produced comes first
    expect(rows[0]?.lane).toBe("produced");
    expect(rows[1]?.lane).toBe("consumed");
  });
});
