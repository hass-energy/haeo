import { describe, expect, it } from "vitest";

import { windowIntervals } from "./window-bands";

describe("windowIntervals", () => {
  it("joins consecutive open periods into one span", () => {
    expect(windowIntervals([0, 10, 20, 30, 40], [1, 1, 0, 1, 0])).toEqual([
      { start: 0, end: 20 },
      { start: 30, end: 40 },
    ]);
  });

  it("takes the last period to last as long as the one before", () => {
    expect(windowIntervals([0, 10, 25], [0, 0, 1])).toEqual([{ start: 25, end: 40 }]);
  });

  it("returns nothing when no period is open", () => {
    expect(windowIntervals([0, 10], [0, 0])).toEqual([]);
  });
});
