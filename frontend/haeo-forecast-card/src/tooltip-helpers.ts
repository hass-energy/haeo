import { classifyPowerSeries } from "./power-series-classification";
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
  label: string;
  value: number;
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
  powerValueFn: (series: ForecastSeries, value: number) => number
): TooltipRow[] {
  const rows: TooltipRow[] = [];
  const nameCounts = new Map<string, number>();
  for (const series of visibleSeries) {
    const key = series.label.trim().toLowerCase();
    nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
  }
  for (const series of visibleSeries) {
    const idx = hoverIndices.get(series.key) ?? 0;
    const section = tooltipSection(series);
    const duplicated = (nameCounts.get(series.label.trim().toLowerCase()) ?? 0) > 1;
    rows.push({
      key: series.key,
      label: tooltipDisplayLabel(series, section, duplicated),
      value: series.lane === "power" ? powerValueFn(series, series.values[idx] ?? 0) : (series.values[idx] ?? 0),
      unit: series.unit,
      color: series.color,
      lane: section,
    });
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
