import type { ForecastSeries } from "./types";

export type PowerGroup = "production" | "consumption" | "unknown";
export type PowerSubgroup = "potential" | "utilization";

export interface PowerSeriesCategory {
  group: PowerGroup;
  subgroup: PowerSubgroup;
}

const PRODUCTION_TOKENS = ["export", "discharge", "solar", "pv", "generation", "produce", "feed", "supply"];
const CONSUMPTION_TOKENS = ["import", "load", "demand", "charge", "consume", "use", "request"];
const POTENTIAL_TOKENS = ["available", "limit", "max", "capacity", "potential", "cap", "solar", "pv", "forecast"];

function hasToken(value: string, tokens: string[]): boolean {
  return tokens.some((token) => value.includes(token));
}

export function classifyPowerSeries(series: ForecastSeries): PowerSeriesCategory {
  const haystack = `${series.outputName} ${series.elementName} ${series.entityId} ${series.label}`.toLowerCase();
  const group: PowerGroup = hasToken(haystack, PRODUCTION_TOKENS)
    ? "production"
    : hasToken(haystack, CONSUMPTION_TOKENS)
      ? "consumption"
      : "unknown";
  const subgroup: PowerSubgroup = hasToken(haystack, POTENTIAL_TOKENS) ? "potential" : "utilization";
  return { group, subgroup };
}
