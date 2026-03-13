import { describe, expect, it } from "vitest";

import { linearScale, nearestArrayIndex, stepAreaPath } from "../src/geometry";

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
