import { describe, expect, it } from "vitest";

import { linearScale, linePath, nearestArrayIndex, stepAreaPath, stepPath } from "../src/geometry";

describe("geometry helpers", () => {
  it("scales values linearly between domains", () => {
    expect(linearScale(5, 0, 10, 0, 100)).toBe(50);
    expect(linearScale(0, 0, 10, 0, 100)).toBe(0);
    expect(linearScale(10, 0, 10, 0, 100)).toBe(100);
    expect(linearScale(10, 10, 10, 0, 100)).toBe(0);
  });

  it("selects nearest sample for hover snapping", () => {
    const times = new Float64Array([1000, 2000, 3000, 4000]);
    expect(nearestArrayIndex(times, 900)).toBe(0);
    expect(nearestArrayIndex(times, 2600)).toBe(2);
    expect(nearestArrayIndex(times, 3900)).toBe(3);
  });

  it("returns empty area path for empty times", () => {
    const x = (value: number) => value;
    const y = (value: number) => value;
    expect(stepAreaPath(new Float64Array(), new Float64Array(), new Float64Array(), x, y)).toBe("");
  });
});

describe("stepPath", () => {
  const identity = (v: number): number => v;

  it("returns empty string for empty ForecastPoint array", () => {
    expect(stepPath([], identity, identity)).toBe("");
  });

  it("generates step path from ForecastPoint array", () => {
    const points = [
      { time: 0, value: 1 },
      { time: 10, value: 2 },
      { time: 20, value: 3 },
    ];
    const d = stepPath(points, identity, identity);
    expect(d).toBe("M 0 1 L 10 1 L 10 2 L 20 2 L 20 3");
  });

  it("generates step path from Float64Array pairs", () => {
    const times = new Float64Array([0, 10, 20]);
    const values = new Float64Array([1, 2, 3]);
    const d = stepPath(times, values, identity, identity);
    expect(d).toBe("M 0 1 L 10 1 L 10 2 L 20 2 L 20 3");
  });

  it("returns empty string for empty Float64Array", () => {
    expect(stepPath(new Float64Array([]), new Float64Array([]), identity, identity)).toBe("");
  });
});

describe("linePath", () => {
  const identity = (v: number): number => v;

  it("returns empty string for empty ForecastPoint array", () => {
    expect(linePath([], identity, identity)).toBe("");
  });

  it("generates line path from ForecastPoint array", () => {
    const points = [
      { time: 0, value: 1 },
      { time: 10, value: 2 },
      { time: 20, value: 3 },
    ];
    const d = linePath(points, identity, identity);
    expect(d).toBe("M 0 1 L 10 2 L 20 3");
  });

  it("generates line path from Float64Array pairs", () => {
    const times = new Float64Array([0, 10, 20]);
    const values = new Float64Array([1, 2, 3]);
    const d = linePath(times, values, identity, identity);
    expect(d).toBe("M 0 1 L 10 2 L 20 3");
  });

  it("returns empty string for empty Float64Array", () => {
    expect(linePath(new Float64Array([]), new Float64Array([]), identity, identity)).toBe("");
  });
});
