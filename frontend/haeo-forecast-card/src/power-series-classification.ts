import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption" | "unknown";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

const PRODUCTION_TOKENS = ["export", "discharge", "solar", "pv", "generation", "produce", "feed", "supply"];
const CONSUMPTION_TOKENS = ["import", "load", "demand", "charge", "consume", "use", "request"];
const POTENTIAL_TOKENS = ["available", "limit", "max", "capacity", "potential", "cap", "forecast"];

function hasToken(value: string, tokens: string[]): boolean {
  return tokens.some((token) => value.includes(token));
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const output = series.outputName.toLowerCase();
  const element = series.elementName.toLowerCase();
  const elementType = series.elementType.toLowerCase();
  const entity = series.entityId.toLowerCase();
  const label = series.label.toLowerCase();
  const haystack = `${output} ${element} ${entity} ${label}`;
  const hasConfigInput = series.configMode !== null;

  let subgroup: PowerSubgroup =
    hasConfigInput || series.outputType === "power_limit" || hasToken(haystack, POTENTIAL_TOKENS)
      ? "potential"
      : "utilization";

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
    if (elementType === "solar") {
      group = "production";
    }
  }

  if (group === "unknown") {
    group = hasToken(haystack, PRODUCTION_TOKENS)
      ? "production"
      : hasToken(haystack, CONSUMPTION_TOKENS)
        ? "consumption"
        : "unknown";
  }

  return { group, subgroup };
}
