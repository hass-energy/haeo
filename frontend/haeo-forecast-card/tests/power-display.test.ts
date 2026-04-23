import { describe, expect, it } from "vitest";

import {
  powerSection,
  powerValueForDisplay,
  emptySectionStacks,
  calculatePowerBounds,
  stepTopStrokePaths,
} from "../src/power-display";
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

describe("powerSection", () => {
  it("returns consumed for consumption utilization", () => {
    const s = makeSeries({ key: "a", direction: "-", outputType: "power" });
    expect(powerSection(s)).toBe("consumed");
  });

  it("returns produced for production utilization", () => {
    const s = makeSeries({ key: "b", direction: "+", outputType: "power" });
    expect(powerSection(s)).toBe("produced");
  });

  it("returns available for production potential (config input)", () => {
    const s = makeSeries({ key: "c", direction: "+", outputType: "power", configMode: "forecast" });
    expect(powerSection(s)).toBe("available");
  });

  it("returns possible for consumption potential (power_limit)", () => {
    const s = makeSeries({ key: "d", direction: "-", outputType: "power_limit" });
    expect(powerSection(s)).toBe("possible");
  });
});

describe("powerValueForDisplay", () => {
  it("returns magnitude in overlay mode", () => {
    const s = makeSeries({ key: "a", direction: "-" });
    expect(powerValueForDisplay(s, -5, "overlay", false)).toBe(5);
    expect(powerValueForDisplay(s, 3, "overlay", false)).toBe(3);
  });

  it("returns raw value for bidirectional series in opposed mode", () => {
    const s = makeSeries({ key: "a", direction: "-" });
    expect(powerValueForDisplay(s, -5, "opposed", true)).toBe(-5);
    expect(powerValueForDisplay(s, 3, "opposed", true)).toBe(3);
  });

  it("returns negative magnitude for consumption in opposed mode", () => {
    const s = makeSeries({ key: "a", direction: "-", outputType: "power" });
    expect(powerValueForDisplay(s, 5, "opposed", false)).toBe(-5);
  });

  it("returns positive magnitude for production in opposed mode", () => {
    const s = makeSeries({ key: "a", direction: "+", outputType: "power" });
    expect(powerValueForDisplay(s, 3, "opposed", false)).toBe(3);
  });
});

describe("emptySectionStacks", () => {
  it("creates zero-filled stacks of the requested length", () => {
    const stacks = emptySectionStacks(3);
    expect(stacks.available.length).toBe(3);
    expect(stacks.produced.length).toBe(3);
    expect(stacks.consumed.length).toBe(3);
    expect(stacks.possible.length).toBe(3);
    expect(stacks.available.every((v) => v === 0)).toBe(true);
  });
});

describe("calculatePowerBounds", () => {
  it("returns default bounds for empty series", () => {
    const bounds = calculatePowerBounds([], "opposed", new Map());
    expect(bounds).toEqual({ min: -1, max: 1 });
  });

  it("calculates stacked bounds from series", () => {
    const a = makeSeries({
      key: "a",
      direction: "+",
      outputType: "power",
      values: new Float64Array([1, 2, 3]),
    });
    const b = makeSeries({
      key: "b",
      direction: "-",
      outputType: "power",
      values: new Float64Array([2, 1, 1]),
    });
    const bounds = calculatePowerBounds([a, b], "opposed", new Map());
    expect(bounds.min).toBeLessThan(0);
    expect(bounds.max).toBeGreaterThan(0);
  });
});

describe("stepTopStrokePaths", () => {
  const identity = (v: number): number => v;

  it("returns empty for short arrays", () => {
    expect(stepTopStrokePaths(new Float64Array([]), new Float64Array([]), new Float64Array([]), identity, identity)).toEqual([]);
    expect(stepTopStrokePaths(new Float64Array([1]), new Float64Array([1]), new Float64Array([1]), identity, identity)).toEqual([]);
  });

  it("generates stroke paths for non-zero segments", () => {
    const times = new Float64Array([0, 1, 2, 3]);
    const upper = new Float64Array([0, 2, 3, 0]);
    const values = new Float64Array([0, 2, 3, 0]);
    const paths = stepTopStrokePaths(times, upper, values, identity, identity);
    expect(paths.length).toBeGreaterThan(0);
    expect(paths[0]).toContain("M");
  });

  it("skips zero-value intervals", () => {
    const times = new Float64Array([0, 1, 2, 3, 4, 5]);
    const upper = new Float64Array([1, 1, 0, 0, 2, 2]);
    const values = new Float64Array([1, 1, 0, 0, 2, 2]);
    const paths = stepTopStrokePaths(times, upper, values, identity, identity);
    // Should get 2 separate paths: one for indices 0-1 and one for indices 4-5
    expect(paths.length).toBe(2);
  });
});
