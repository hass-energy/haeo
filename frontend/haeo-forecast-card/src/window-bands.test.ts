import { describe, expect, it } from "vitest";

import type { ForecastSeries } from "./types";
import { windowBands, windowIntervals } from "./window-bands";

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

describe("windowBands", () => {
  const series = (key: string, values: number[]): ForecastSeries => ({
    key,
    entityId: `number.${key}`,
    label: key,
    elementName: key,
    elementType: "deferrable_load",
    outputName: "in_window",
    outputType: "window",
    direction: null,
    sourceRole: "limit",
    configMode: "driven",
    fixed: false,
    priority: null,
    lane: "window",
    drawType: "step",
    unit: "",
    color: "#123456",
    times: new Float64Array([0, 10, 20, 30]),
    values: new Float64Array(values),
  });

  it("places each open span in its series' row, scaled to the chart", () => {
    const bands = windowBands([series("pump", [1, 1, 0, 0]), series("ev", [0, 0, 1, 1])], (time) => time * 2);

    expect(bands).toEqual([
      { key: "pump:0", seriesKey: "pump", color: "#123456", x: 0, width: 40, row: 0 },
      { key: "ev:0", seriesKey: "ev", color: "#123456", x: 40, width: 40, row: 1 },
    ]);
  });
});
