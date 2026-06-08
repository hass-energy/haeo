import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const subgroup: PowerSubgroup =
    series.sourceRole === "forecast" || series.sourceRole === "limit" ? "potential" : "utilization";

  if (series.direction === "+") {
    return { group: "production", subgroup };
  }
  return { group: "consumption", subgroup };
}

export function powerPairKey(series: ForecastSeries): string {
  return `${series.elementName}:${series.direction ?? ""}`;
}

export function isPowerPotentialSeries(series: ForecastSeries): boolean {
  return series.lane === "power" && (series.sourceRole === "forecast" || series.sourceRole === "limit");
}
