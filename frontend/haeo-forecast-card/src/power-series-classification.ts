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
  const entity = series.entityId.toLowerCase();
  const label = series.label.toLowerCase();
  const haystack = `${output} ${element} ${entity} ${label}`;

  // Explicit HAEO flow semantics: grid export is system consumption; grid import is system production.
  if (output.includes("grid_power_export")) {
    return { group: "consumption", subgroup: "utilization" };
  }
  if (output.includes("grid_power_import")) {
    return { group: "production", subgroup: "utilization" };
  }
  if (output.includes("battery_power_charge")) {
    return { group: "consumption", subgroup: "utilization" };
  }
  if (output.includes("battery_power_discharge")) {
    return { group: "production", subgroup: "utilization" };
  }
  if (output.includes("load_power")) {
    return { group: "consumption", subgroup: "utilization" };
  }
  if (entity.includes("solar_forecast") || output.includes("solar_forecast")) {
    return { group: "production", subgroup: "potential" };
  }
  if (output.includes("solar_power")) {
    return { group: "production", subgroup: "utilization" };
  }

  const group: PowerGroup = hasToken(haystack, PRODUCTION_TOKENS)
    ? "production"
    : hasToken(haystack, CONSUMPTION_TOKENS)
      ? "consumption"
      : "unknown";
  const subgroup: PowerSubgroup = hasToken(haystack, POTENTIAL_TOKENS) ? "potential" : "utilization";
  return { group, subgroup };
}
