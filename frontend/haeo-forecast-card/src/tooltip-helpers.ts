import { classifyPowerSeries, isPowerPotentialSeries, powerPairKey } from "./power-series-classification";
import type { ForecastSeries } from "./types";

export type TooltipSectionId = "produced" | "available" | "consumed" | "possible" | "price" | "soc";

export function tooltipSection(series: ForecastSeries): TooltipSectionId {
  if (series.lane === "price") {
    return "price";
  }
  if (series.lane === "soc") {
    return "soc";
  }
  const category = classifyPowerSeries(series);
  if (category.group === "production") {
    return category.subgroup === "potential" ? "available" : "produced";
  }
  return category.subgroup === "potential" ? "possible" : "consumed";
}

function prettifyOutput(outputName: string): string {
  return outputName.replace(/_/g, " ").trim().toLowerCase();
}

export function tooltipDisplayLabel(
  series: ForecastSeries,
  _section: TooltipSectionId,
  duplicateLabel: boolean
): string {
  const name = series.label.trim();
  if (duplicateLabel) {
    return `${name} – ${prettifyOutput(series.outputName)}`;
  }
  return name;
}

interface TooltipRow {
  key: string;
  possibleKey?: string;
  label: string;
  value: number;
  possibleValue?: number;
  unit: string;
  color: string;
  lane: TooltipSectionId;
}

const LANE_SORT_ORDER: Record<TooltipSectionId, number> = {
  produced: 0,
  available: 1,
  consumed: 2,
  possible: 3,
  price: 4,
  soc: 5,
};

export function buildTooltipRows(
  visibleSeries: ForecastSeries[],
  hoverIndices: Map<string, number>,
  potentialSeries: ForecastSeries[],
  potentialIndices: Map<string, number>,
  powerValueFn: (series: ForecastSeries, value: number) => number
): TooltipRow[] {
  const rows: TooltipRow[] = [];
  const nameCounts = new Map<string, number>();
  const potentialByPair = new Map<string, ForecastSeries>();
  for (const series of visibleSeries) {
    const key = series.label.trim().toLowerCase();
    nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
  }
  for (const series of potentialSeries) {
    if (isPowerPotentialSeries(series)) {
      const pairKey = powerPairKey(series);
      const existing = potentialByPair.get(pairKey);
      if (!existing || (existing.sourceRole === "limit" && series.sourceRole === "forecast")) {
        potentialByPair.set(pairKey, series);
      }
    }
  }
  for (const series of visibleSeries) {
    if (isPowerPotentialSeries(series)) {
      continue;
    }
    const idx = hoverIndices.get(series.key) ?? 0;
    const section = tooltipSection(series);
    const duplicated = (nameCounts.get(series.label.trim().toLowerCase()) ?? 0) > 1;
    const potential = series.lane === "power" ? potentialByPair.get(powerPairKey(series)) : undefined;
    const potentialIdx = potential ? (potentialIndices.get(potential.key) ?? 0) : 0;
    const row: TooltipRow = {
      key: series.key,
      label: tooltipDisplayLabel(series, section, duplicated),
      value: series.lane === "power" ? powerValueFn(series, series.values[idx] ?? 0) : (series.values[idx] ?? 0),
      unit: series.unit,
      color: series.color,
      lane: section,
    };
    if (potential !== undefined) {
      row.possibleKey = potential.key;
      row.possibleValue = powerValueFn(potential, potential.values[potentialIdx] ?? 0);
    }
    rows.push(row);
  }
  return rows.sort((a, b) => {
    const la = LANE_SORT_ORDER[a.lane];
    const lb = LANE_SORT_ORDER[b.lane];
    if (la !== lb) {
      return la - lb;
    }
    return Math.abs(b.value) - Math.abs(a.value);
  });
}
