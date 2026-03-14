import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption" | "unknown";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const elementType = series.elementType.toLowerCase();
  const hasConfigInput = series.configMode !== null;
  const isPowerLike =
    series.outputType === "power" || series.outputType === "power_flow" || series.outputType === "power_limit";

  if (!isPowerLike) {
    return { group: "unknown", subgroup: "utilization" };
  }

  let subgroup: PowerSubgroup = hasConfigInput || series.outputType === "power_limit" ? "potential" : "utilization";

  // Mirror scenario visualizer semantics: use direction metadata as the source of truth.
  // "+" means production/supply, "-" means consumption/demand.
  let group: PowerGroup = "unknown";
  if (series.direction === "+") {
    group = "production";
  } else if (series.direction === "-") {
    group = "consumption";
  }

  // Input power entities (config_mode set) represent potential forecasts.
  if (hasConfigInput && series.outputType === "power") {
    subgroup = "potential";
    if (elementType === "solar" && group === "unknown") {
      group = "production";
    }
  }

  return { group, subgroup };
}
