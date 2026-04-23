import { describe, expect, it } from "vitest";

import {
  tooltipSection,
  tooltipDisplayLabel,
  buildTooltipRows,
  buildTooltipTotals,
} from "../src/tooltip-helpers";
import type { ForecastSeries } from "../src/types";

function makeSeries(overrides: Partial<ForecastSeries> & { key: string }): ForecastSeries {
  return {
    entityId: "sensor.test",
    label: "Test",
    elementName: "Test",
    elementType: "grid",
    outputName: "import_power",
    outputType: "power",
    direction: "-",
    configMode: null,
    fieldName: null,
    sourceRole: "output",
    plotStream: null,
    plotPriority: null,
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
  it("returns Price for price lane", () => {
    expect(tooltipSection(makeSeries({ key: "a", lane: "price", outputType: "price" }))).toBe("Price");
  });

  it("returns State of charge for soc lane", () => {
    expect(tooltipSection(makeSeries({ key: "a", lane: "soc", outputType: "soc" }))).toBe("State of charge");
  });

  it("returns Consumed for consumption utilization", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "-", outputType: "power" }))).toBe("Consumed");
  });

  it("returns Produced for production utilization", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "+", outputType: "power" }))).toBe("Produced");
  });

  it("returns Available for production potential (config input)", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "+", outputType: "power", configMode: "forecast" }))).toBe("Available");
  });

  it("returns Possible for consumption potential (power_limit)", () => {
    expect(tooltipSection(makeSeries({ key: "a", direction: "-", outputType: "power_limit" }))).toBe("Possible");
  });
});

describe("tooltipDisplayLabel", () => {
  it("adds import/export qualifier for price series", () => {
    const s = makeSeries({ key: "a", lane: "price", outputName: "import_price", label: "Grid" });
    expect(tooltipDisplayLabel(s, "Price", false)).toBe("Grid (import)");
  });

  it("returns name without qualifier for non-directional price", () => {
    const s = makeSeries({ key: "a", lane: "price", outputName: "spot_price", label: "Grid" });
    expect(tooltipDisplayLabel(s, "Price", false)).toBe("Grid");
  });

  it("adds section suffix for power series without direction in name", () => {
    const s = makeSeries({ key: "a", label: "Solar", outputName: "power" });
    expect(tooltipDisplayLabel(s, "Produced", false)).toBe("Solar (produced)");
  });

  it("uses output name for duplicate labels", () => {
    const s = makeSeries({ key: "a", label: "Grid", outputName: "import_power" });
    expect(tooltipDisplayLabel(s, "Consumed", true)).toBe("Grid (import power)");
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
    const rows = buildTooltipRows(
      [produced, consumed],
      indices,
      "opposed",
      new Map(),
      (_series, value) => value,
    );
    expect(rows.length).toBe(2);
    // Produced comes first
    expect(rows[0]?.lane).toBe("Produced");
    expect(rows[1]?.lane).toBe("Consumed");
  });
});

describe("buildTooltipTotals", () => {
  it("sums power series by section", () => {
    const a = makeSeries({
      key: "a",
      direction: "+",
      outputType: "power",
      values: new Float64Array([3, 0, 0]),
    });
    const b = makeSeries({
      key: "b",
      direction: "+",
      outputType: "power",
      values: new Float64Array([2, 0, 0]),
    });
    const indices = new Map([
      ["a", 0],
      ["b", 0],
    ]);
    const totals = buildTooltipTotals([a, b], indices, (_s, v) => v);
    expect(totals.length).toBe(1);
    expect(totals[0]?.value).toBe(5);
  });

  it("excludes near-zero totals", () => {
    const a = makeSeries({
      key: "a",
      direction: "+",
      outputType: "power",
      values: new Float64Array([0, 0, 0]),
    });
    const indices = new Map([["a", 0]]);
    const totals = buildTooltipTotals([a], indices, (_s, v) => v);
    expect(totals.length).toBe(0);
  });
});
