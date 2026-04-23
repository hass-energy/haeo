import { classifyPowerSeries } from "./power-series-classification";
import type { ForecastSeries } from "./types";

export function tooltipSection(series: ForecastSeries): string {
  if (series.lane === "price") {
    return "Price";
  }
  if (series.lane === "soc") {
    return "State of charge";
  }
  const category = classifyPowerSeries(series);
  if (category.group === "production") {
    return category.subgroup === "potential" ? "Available" : "Produced";
  }
  if (category.group === "consumption") {
    return category.subgroup === "potential" ? "Possible" : "Consumed";
  }
  return "Consumed";
}

function prettifyOutput(outputName: string): string {
  return outputName.replace(/_/g, " ").trim().toLowerCase();
}

export function tooltipDisplayLabel(
  series: ForecastSeries,
  section: string,
  duplicateLabel: boolean,
): string {
  const name = series.label.trim();
  if (section === "Price") {
    const output = series.outputName.toLowerCase();
    if (output.includes("import")) {
      return `${name} (import)`;
    }
    if (output.includes("export")) {
      return `${name} (export)`;
    }
    return name;
  }
  if (series.lane !== "power") {
    return duplicateLabel ? `${name} (${prettifyOutput(series.outputName)})` : name;
  }
  const lower = name.toLowerCase();
  if (
    lower.includes("import") ||
    lower.includes("export") ||
    lower.includes("charge") ||
    lower.includes("discharge")
  ) {
    return duplicateLabel ? `${name} (${prettifyOutput(series.outputName)})` : name;
  }
  return duplicateLabel
    ? `${name} (${prettifyOutput(series.outputName)})`
    : `${name} (${section.toLowerCase()})`;
}

interface TooltipRow {
  key: string;
  label: string;
  value: number;
  unit: string;
  color: string;
  lane: string;
}

const LANE_SORT_ORDER = new Map<string, number>([
  ["Produced", 0],
  ["Available", 1],
  ["Consumed", 2],
  ["Possible", 3],
  ["Price", 4],
  ["State of charge", 5],
]);

export function buildTooltipRows(
  visibleSeries: ForecastSeries[],
  hoverIndices: Map<string, number>,
  powerValueFn: (series: ForecastSeries, value: number) => number,
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
      value:
        series.lane === "power"
          ? powerValueFn(series, series.values[idx] ?? 0)
          : (series.values[idx] ?? 0),
      unit: series.unit,
      color: series.color,
      lane: section,
    });
  }
  return rows.sort((a, b) => {
    const la = LANE_SORT_ORDER.get(a.lane) ?? 9;
    const lb = LANE_SORT_ORDER.get(b.lane) ?? 9;
    if (la !== lb) {
      return la - lb;
    }
    return Math.abs(b.value) - Math.abs(a.value);
  });
}

const SECTION_SORT_ORDER = new Map<string, number>([
  ["Produced", 0],
  ["Available", 1],
  ["Consumed", 2],
  ["Possible", 3],
]);

export function buildTooltipTotals(
  visibleSeries: ForecastSeries[],
  hoverIndices: Map<string, number>,
  powerValueFn: (series: ForecastSeries, value: number) => number,
): Array<{ lane: string; value: number; unit: string }> {
  const totals = new Map<string, { value: number; unit: string }>();
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
    .sort((a, b) => (SECTION_SORT_ORDER.get(a[0]) ?? 9) - (SECTION_SORT_ORDER.get(b[0]) ?? 9))
    .map(([lane, total]) => ({ lane, value: total.value, unit: total.unit }));
}
