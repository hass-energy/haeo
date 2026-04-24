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
  if (category.group === "consumption") {
    return category.subgroup === "potential" ? "possible" : "consumed";
  }
  return "consumed";
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

const SECTION_SORT_ORDER: Partial<Record<TooltipSectionId, number>> = {
  produced: 0,
  available: 1,
  consumed: 2,
  possible: 3,
};

export function buildTooltipTotals(
  visibleSeries: ForecastSeries[],
  hoverIndices: Map<string, number>,
  powerValueFn: (series: ForecastSeries, value: number) => number
): Array<{ lane: TooltipSectionId; value: number; unit: string }> {
  const totals = new Map<TooltipSectionId, { value: number; unit: string }>();
  for (const series of visibleSeries) {
    if (series.lane !== "power") {
      continue;
    }
    const idx = hoverIndices.get(series.key) ?? 0;
    const section = tooltipSection(series);
    const existing = totals.get(section) ?? { value: 0, unit: series.unit };
    const value = powerValueFn(series, series.values[idx] ?? 0);
    totals.set(section, {
      value: existing.value + value,
      unit: existing.unit || series.unit,
    });
  }
  return [...totals.entries()]
    .filter(([, total]) => Math.abs(total.value) > 1e-9)
    .sort((a, b) => (SECTION_SORT_ORDER[a[0]] ?? 9) - (SECTION_SORT_ORDER[b[0]] ?? 9))
    .map(([lane, total]) => ({ lane, value: total.value, unit: total.unit }));
}
