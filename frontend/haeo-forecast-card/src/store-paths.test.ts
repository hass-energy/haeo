import { describe, expect, it } from "vitest";

import { computeSocPaths } from "./store-paths";
import type { ForecastSeries } from "./types";

function socSeries(overrides: Partial<ForecastSeries>): ForecastSeries {
  return {
    key: "battery:soc",
    entityId: "sensor.battery_soc",
    label: "Battery state of charge",
    elementName: "Battery",
    elementType: "battery",
    outputName: "battery_state_of_charge",
    outputType: "state_of_charge",
    direction: null,
    sourceRole: "output",
    configMode: null,
    fixed: false,
    priority: null,
    lane: "soc",
    drawType: "line",
    unit: "%",
    color: "#22c55e",
    times: new Float64Array([0, 1]),
    values: new Float64Array([50, 40]),
    ...overrides,
  };
}

describe("computeSocPaths", () => {
  it("marks reserves and headroom as threshold lines and leaves battery lines plain", () => {
    const paths = computeSocPaths(
      [
        socSeries({}),
        socSeries({ key: "backup:soc", elementName: "Backup", elementType: "reserve" }),
        socSeries({ key: "room:soc", elementName: "Room", elementType: "headroom" }),
      ],
      { min: -1, max: 1 },
      { min: 0, max: 100 },
      0,
      100,
      (time) => time * 10
    );

    expect(paths.map((path) => path.className)).toEqual([undefined, "thresholdLine", "thresholdLine"]);
  });
});
