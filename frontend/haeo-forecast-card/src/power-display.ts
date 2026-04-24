import { classifyPowerSeries } from "./power-series-classification";
import type { ForecastSeries, LaneBounds, PowerDisplayMode } from "./types";

export type PowerSection = "available" | "produced" | "consumed" | "possible";

const POWER_EPSILON = 1e-6;

export function powerSection(series: ForecastSeries): PowerSection {
  const category = classifyPowerSeries(series);
  if (category.group === "production") {
    return category.subgroup === "potential" ? "available" : "produced";
  }
  return category.subgroup === "potential" ? "possible" : "consumed";
}

export function powerValueForDisplay(series: ForecastSeries, value: number, displayMode: PowerDisplayMode): number {
  const magnitude = Math.abs(value);
  if (displayMode === "overlay") {
    return magnitude;
  }
  const category = classifyPowerSeries(series);
  if (category.group === "consumption") {
    return -magnitude;
  }
  return magnitude;
}

export function emptySectionStacks(length: number): Record<PowerSection, Float64Array> {
  return {
    available: new Float64Array(length),
    produced: new Float64Array(length),
    consumed: new Float64Array(length),
    possible: new Float64Array(length),
  };
}

export function calculatePowerBounds(orderedSeries: ForecastSeries[], displayMode: PowerDisplayMode): LaneBounds {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  const firstSeries = orderedSeries[0];
  if (!firstSeries) {
    return { min: -1, max: 1 };
  }
  const stacks = emptySectionStacks(firstSeries.times.length);
  for (const series of orderedSeries) {
    const section = powerSection(series);
    const stack = stacks[section];
    for (let idx = 0; idx < firstSeries.times.length; idx += 1) {
      const transformed = powerValueForDisplay(series, series.values[idx] ?? 0, displayMode);
      const next = (stack[idx] ?? 0) + transformed;
      stack[idx] = next;
      min = Math.min(min, next);
      max = Math.max(max, next);
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return { min: -1, max: 1 };
  }
  min = Math.min(min, 0);
  max = Math.max(max, 0);
  if (min === max) {
    const delta = Math.max(1, Math.abs(min) * 0.15);
    return { min: min - delta, max: max + delta };
  }
  const padding = Math.max(0.1, (max - min) * 0.08);
  return { min: min - padding, max: max + padding };
}

export function stepTopStrokePaths(
  times: Float64Array,
  upper: Float64Array,
  values: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number
): string[] {
  if (times.length < 2 || upper.length !== times.length || values.length !== times.length) {
    return [];
  }

  const paths: string[] = [];
  const intervalCount = times.length - 1;
  let idx = 0;
  while (idx < intervalCount) {
    while (idx < intervalCount && Math.abs(values[idx] ?? 0) <= POWER_EPSILON) {
      idx += 1;
    }
    if (idx >= intervalCount) {
      break;
    }
    const start = idx;
    while (idx < intervalCount && Math.abs(values[idx] ?? 0) > POWER_EPSILON) {
      idx += 1;
    }
    const end = idx - 1;

    const startTime = times[start];
    const startUpper = upper[start];
    if (startTime === undefined || startUpper === undefined) {
      continue;
    }
    let path = `M ${x(startTime)} ${y(startUpper)}`;
    for (let i = start + 1; i <= end + 1; i += 1) {
      const currTime = times[i];
      const prevUpper = upper[i - 1];
      const currUpper = upper[i];
      if (currTime === undefined || prevUpper === undefined || currUpper === undefined) {
        continue;
      }
      path += ` L ${x(currTime)} ${y(prevUpper)} L ${x(currTime)} ${y(currUpper)}`;
    }
    paths.push(path);
  }
  return paths;
}
