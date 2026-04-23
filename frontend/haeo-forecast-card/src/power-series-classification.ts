import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption" | "unknown";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const isPowerLike =
    series.outputType === "power" || series.outputType === "power_flow" || series.outputType === "power_limit";

  if (!isPowerLike) {
    return { group: "unknown", subgroup: "utilization" };
  }

  // Direction metadata is the source of truth for production vs consumption.
  // "+" means production/supply, "-" means consumption/demand.
  let group: PowerGroup = "unknown";
  if (series.direction === "+") {
    group = "production";
  } else if (series.direction === "-") {
    group = "consumption";
  }

  // Source role metadata determines whether a series represents a forecast/limit
  // (potential) or an optimizer output (utilization).
  const subgroup: PowerSubgroup =
    series.sourceRole === "forecast" || series.sourceRole === "limit" ? "potential" : "utilization";

  return { group, subgroup };
}
