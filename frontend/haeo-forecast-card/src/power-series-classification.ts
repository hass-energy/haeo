import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption" | "unknown";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const hasConfigInput = series.configMode !== null;
  const isPowerLike =
    series.outputType === "power" || series.outputType === "power_flow" || series.outputType === "power_limit";

  if (!isPowerLike) {
    return { group: "unknown", subgroup: "utilization" };
  }

  let subgroup: PowerSubgroup = "utilization";

  // Mirror scenario visualizer semantics: use direction metadata as the source of truth.
  // "+" means production/supply, "-" means consumption/demand.
  let group: PowerGroup = "unknown";
  if (series.direction === "+") {
    group = "production";
  } else if (series.direction === "-") {
    group = "consumption";
  }

  // Input power entities represent forecast/potential series.
  // Direction still defines production vs consumption; subgroup is potential.
  // Output power_limit remains potential as well.
  if (hasConfigInput && series.outputType === "power") {
    subgroup = "potential";
    // Keep solar input forecasts on production side even if metadata regresses.
    if (series.elementType.toLowerCase() === "solar") {
      group = "production";
    }
  } else if (series.outputType === "power_limit") {
    subgroup = "potential";
  }

  return { group, subgroup };
}
