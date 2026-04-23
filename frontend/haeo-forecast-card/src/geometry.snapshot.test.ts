import { describe, expect, it } from "vitest";

import { linePath, stepAreaPath, stepPath } from "./geometry";

describe("svg path snapshots", () => {
  it("renders stable step and line path output", () => {
    const times = new Float64Array([0, 1, 2]);
    const values = new Float64Array([1, 2, 1.5]);
    const x = (time: number) => time * 10;
    const y = (value: number) => value * -5;

    expect(stepPath(times, values, x, y)).toMatchInlineSnapshot(`"M 0 -5 L 10 -5 L 10 -10 L 20 -10 L 20 -7.5"`);
    expect(linePath(times, values, x, y)).toMatchInlineSnapshot(`"M 0 -5 L 10 -10 L 20 -7.5"`);

    const lower = new Float64Array([0, 0, 0]);
    const upper = new Float64Array([1, 2, 1.5]);
    expect(stepAreaPath(times, lower, upper, x, y)).toMatchInlineSnapshot(
      `"M 0 -5 L 10 -5 L 10 -10 L 20 -10 L 20 -7.5 L 20 0 L 20 0 L 10 0 L 10 0 L 0 0 Z"`
    );
  });
});
