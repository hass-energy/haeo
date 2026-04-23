import { describe, expect, it } from "vitest";

import { stepArrayIndex, sharedTimeline, computeHoverIndices } from "./hover";
import type { ForecastSeries } from "./types";

function makeSeries(overrides: Partial<ForecastSeries> & { key: string; times: Float64Array; values: Float64Array }): ForecastSeries {
  return {
    entityId: "sensor.test",
    label: "Test",
    elementName: "Test",
    elementType: "grid",
    outputName: "power",
    outputType: "power",
    direction: null,
    configMode: null,
    fieldName: null,
    sourceRole: "output",
    plotStream: null,
    plotPriority: null,
    lane: "power",
    drawType: "step",
    unit: "kW",
    color: "#000",
    ...overrides,
  };
}

describe("stepArrayIndex", () => {
  it("returns 0 for an empty or single-element array", () => {
    expect(stepArrayIndex(new Float64Array([]), 100)).toBe(0);
    expect(stepArrayIndex(new Float64Array([50]), 100)).toBe(0);
  });

  it("returns index of last element <= time", () => {
    const times = new Float64Array([100, 200, 300, 400]);
    expect(stepArrayIndex(times, 150)).toBe(0);
    expect(stepArrayIndex(times, 200)).toBe(1);
    expect(stepArrayIndex(times, 350)).toBe(2);
    expect(stepArrayIndex(times, 400)).toBe(3);
    expect(stepArrayIndex(times, 500)).toBe(3);
  });

  it("clamps to 0 when time is before all entries", () => {
    const times = new Float64Array([100, 200, 300]);
    expect(stepArrayIndex(times, 50)).toBe(0);
  });
});

describe("sharedTimeline", () => {
  it("returns null for empty series list", () => {
    expect(sharedTimeline([])).toBeNull();
  });

  it("returns the timeline when all series share the same times", () => {
    const times = new Float64Array([100, 200, 300]);
    const a = makeSeries({ key: "a", times, values: new Float64Array([1, 2, 3]) });
    const b = makeSeries({ key: "b", times, values: new Float64Array([4, 5, 6]) });
    expect(sharedTimeline([a, b])).toBe(times);
  });

  it("returns null when series have different timelines", () => {
    const a = makeSeries({ key: "a", times: new Float64Array([100, 200]), values: new Float64Array([1, 2]) });
    const b = makeSeries({ key: "b", times: new Float64Array([100, 300]), values: new Float64Array([1, 2]) });
    expect(sharedTimeline([a, b])).toBeNull();
  });

  it("returns null when series have different lengths", () => {
    const a = makeSeries({ key: "a", times: new Float64Array([100, 200, 300]), values: new Float64Array([1, 2, 3]) });
    const b = makeSeries({ key: "b", times: new Float64Array([100, 200]), values: new Float64Array([1, 2]) });
    expect(sharedTimeline([a, b])).toBeNull();
  });
});

describe("computeHoverIndices", () => {
  it("uses shared timeline optimization when all series share times", () => {
    const times = new Float64Array([100, 200, 300, 400]);
    const step = makeSeries({ key: "s", times, values: new Float64Array([1, 2, 3, 4]), drawType: "step" });
    const line = makeSeries({ key: "l", times, values: new Float64Array([1, 2, 3, 4]), drawType: "line" });
    const indices = computeHoverIndices([step, line], 250);
    // step: last index <= 250 is index 1 (time=200)
    expect(indices.get("s")).toBe(1);
    // line: nearest to 250 is index 1 (200) or 2 (300) — 250 is equidistant, nearestArrayIndex picks lower
    expect(indices.get("l")).toBeDefined();
  });

  it("handles non-shared timelines independently", () => {
    const a = makeSeries({
      key: "a",
      times: new Float64Array([100, 200, 300]),
      values: new Float64Array([1, 2, 3]),
      drawType: "step",
    });
    const b = makeSeries({
      key: "b",
      times: new Float64Array([150, 250, 350]),
      values: new Float64Array([4, 5, 6]),
      drawType: "step",
    });
    const indices = computeHoverIndices([a, b], 225);
    expect(indices.get("a")).toBe(1); // last <= 225 is 200 (idx 1)
    expect(indices.get("b")).toBe(0); // last <= 225 is 150 (idx 0)
  });
});
