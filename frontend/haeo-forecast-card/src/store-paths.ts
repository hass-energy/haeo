import { linearScale, linePath, stepAreaPath, stepPath } from "./geometry";
import { classifyPowerSeries } from "./power-series-classification";
import type { ForecastSeries, LaneBounds, PowerDisplayMode } from "./types";
import {
  emptySectionStacks,
  powerSection,
  powerValueForDisplay,
  stepTopStrokePaths,
} from "./power-display";

export interface PowerShape {
  key: string;
  color: string;
  d: string;
  isPotential: boolean;
  strokePaths: string[];
}

export interface LineSvgPath {
  key: string;
  color: string;
  d: string;
}

export function computePowerShapes(
  orderedPowerSeries: ForecastSeries[],
  powerBounds: LaneBounds,
  bidirectionalCache: Map<string, boolean>,
  powerDisplayMode: PowerDisplayMode,
  plotTop: number,
  plotBottom: number,
  xScale: (time: number) => number,
): PowerShape[] {
  const firstSeries = orderedPowerSeries[0];
  if (!firstSeries) {
    return [];
  }
  const { min: powerMin, max: powerMax } = powerBounds;
  const yScalePower = (value: number): number => linearScale(value, powerMin, powerMax, plotBottom, plotTop);
  const horizonCount = firstSeries.times.length;
  const stacks = emptySectionStacks(horizonCount);

  return orderedPowerSeries.map((series) => {
    const category = classifyPowerSeries(series);
    const section = powerSection(series);
    const stack = stacks[section];
    const lower = new Float64Array(horizonCount);
    const upper = new Float64Array(horizonCount);
    const displayValues = new Float64Array(horizonCount);
    const isBi = bidirectionalCache.get(series.key) ?? false;
    for (let idx = 0; idx < horizonCount; idx += 1) {
      const value = powerValueForDisplay(series, series.values[idx] ?? 0, powerDisplayMode, isBi);
      displayValues[idx] = value;
      lower[idx] = stack[idx] ?? 0;
      const next = (stack[idx] ?? 0) + value;
      upper[idx] = next;
      stack[idx] = next;
    }
    return {
      key: series.key,
      color: series.color,
      isPotential: category.subgroup === "potential",
      strokePaths: stepTopStrokePaths(series.times, upper, displayValues, xScale, yScalePower),
      d: stepAreaPath(series.times, lower, upper, xScale, yScalePower),
    };
  });
}

export function computeHoveredPowerKeys(
  orderedPowerSeries: ForecastSeries[],
  hoverIndices: Map<string, number>,
  bidirectionalCache: Map<string, boolean>,
  powerDisplayMode: PowerDisplayMode,
  powerBounds: LaneBounds,
  plotTop: number,
  plotBottom: number,
  pointerY: number,
): Set<string> {
  const hovered = new Set<string>();
  if (orderedPowerSeries.length === 0) {
    return hovered;
  }
  const { min: powerMin, max: powerMax } = powerBounds;
  const yScalePower = (value: number): number =>
    linearScale(value, powerMin, powerMax, plotBottom, plotTop);
  const stackedAtHover = new Map([
    ["available" as const, 0],
    ["produced" as const, 0],
    ["consumed" as const, 0],
    ["possible" as const, 0],
  ]);
  for (const s of orderedPowerSeries) {
    const idx = hoverIndices.get(s.key) ?? 0;
    const isBi = bidirectionalCache.get(s.key) ?? false;
    const value = powerValueForDisplay(s, s.values[idx] ?? 0, powerDisplayMode, isBi);
    if (Math.abs(value) < 1e-6) {
      continue;
    }
    const section = powerSection(s);
    const lower = stackedAtHover.get(section) ?? 0;
    const upper = lower + value;
    stackedAtHover.set(section, upper);
    const y1 = yScalePower(lower);
    const y2 = yScalePower(upper);
    const top = Math.min(y1, y2);
    const bottom = Math.max(y1, y2);
    if (pointerY >= top && pointerY <= bottom) {
      hovered.add(s.key);
    }
  }
  return hovered;
}

export function computePricePaths(
  priceSeries: ForecastSeries[],
  powerBounds: LaneBounds,
  priceBounds: LaneBounds,
  plotTop: number,
  plotBottom: number,
  xScale: (time: number) => number,
): LineSvgPath[] {
  const { min: powerMin, max: powerMax } = powerBounds;
  const { min: priceMin, max: priceMax } = priceBounds;
  const zeroY = linearScale(0, powerMin, powerMax, plotBottom, plotTop);
  const yScalePrice = (value: number): number => {
    if (value >= 0) {
      const positiveMax = Math.max(priceMax, 0.001);
      return linearScale(value, 0, positiveMax, zeroY, plotTop);
    }
    const negativeMin = Math.min(priceMin, -0.001);
    return linearScale(value, negativeMin, 0, plotBottom, zeroY);
  };
  return priceSeries.map((series) => ({
    key: series.key,
    color: series.color,
    d: stepPath(series.times, series.values, xScale, yScalePrice),
  }));
}

export function computeSocPaths(
  socSeries: ForecastSeries[],
  powerBounds: LaneBounds,
  socBounds: LaneBounds,
  plotTop: number,
  plotBottom: number,
  xScale: (time: number) => number,
): LineSvgPath[] {
  const { min: powerMin, max: powerMax } = powerBounds;
  const zeroY = linearScale(0, powerMin, powerMax, plotBottom, plotTop);
  const { min: socMin, max: socMax } = socBounds;
  const yScaleSoc = (value: number): number => linearScale(value, socMin, socMax, zeroY, plotTop);
  return socSeries.map((series) => ({
    key: series.key,
    color: series.color,
    d: linePath(series.times, series.values, xScale, yScaleSoc),
  }));
}
