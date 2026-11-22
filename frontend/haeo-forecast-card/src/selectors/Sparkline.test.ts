import { describe, expect, it } from "vitest";

import { sparklinePoints } from "./Sparkline";

describe("sparklinePoints", () => {
  it("scales the values to fill the box, highest at the top", () => {
    expect(sparklinePoints([0, 10, 5])).toBe("0.0,16.0 18.0,2.0 36.0,9.0");
  });

  it("runs a flat forecast through the middle", () => {
    expect(sparklinePoints([4, 4])).toBe("0.0,9.0 36.0,9.0");
  });
});
