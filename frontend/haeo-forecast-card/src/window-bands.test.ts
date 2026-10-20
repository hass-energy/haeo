import { describe, expect, it } from "vitest";

import type { ForecastSeries } from "./types";
import { windowBands, windowIntervals } from "./window-bands";

describe("windowIntervals", () => {
  it("joins consecutive open periods into one span", () => {
    expect(windowIntervals([0, 10, 20, 30, 40], [1, 1, 0, 1, 0], 50)).toEqual([
      { start: 0, end: 20 },
      { start: 30, end: 40 },
    ]);
  });

  it("runs the last period to the horizon end, however long the periods before it were", () => {
    expect(windowIntervals([0, 10, 20], [0, 0, 1], 80)).toEqual([{ start: 20, end: 80 }]);
  });

  it("leaves the last period empty when the horizon ends at its start", () => {
    expect(windowIntervals([0, 10, 20], [0, 0, 1], 20)).toEqual([{ start: 20, end: 20 }]);
  });

  it("returns nothing when no period is open", () => {
    expect(windowIntervals([0, 10], [0, 0], 20)).toEqual([]);
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
    const bands = windowBands([series("pump", [1, 1, 0, 0]), series("ev", [0, 0, 1, 1])], (time) => time * 2, 40);

    expect(bands).toEqual([
      { key: "pump:0", seriesKey: "pump", color: "#123456", x: 0, width: 40, row: 0 },
      { key: "ev:0", seriesKey: "ev", color: "#123456", x: 40, width: 40, row: 1 },
    ]);
  });
});
