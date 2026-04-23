import { nearestArrayIndex } from "./geometry";
import type { ForecastSeries } from "./types";

/**
 * Binary search for the last index where times[idx] <= time (step interpolation).
 */
export function stepArrayIndex(times: Float64Array, time: number): number {
  const length = times.length;
  if (length <= 1) {
    return 0;
  }
  let low = 0;
  let high = length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    const midValue = times[mid] ?? 0;
    if (midValue <= time) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  const idx = low - 1;
  if (idx < 0) {
    return 0;
  }
  if (idx >= length) {
    return length - 1;
  }
  return idx;
}

/**
 * Detect whether all visible series share the same timeline.
 */
export function sharedTimeline(visibleSeries: ForecastSeries[]): Float64Array | null {
  const first = visibleSeries[0];
  if (!first) {
    return null;
  }
  for (let seriesIdx = 1; seriesIdx < visibleSeries.length; seriesIdx += 1) {
    const series = visibleSeries[seriesIdx];
    if (series?.times.length !== first.times.length) {
      return null;
    }
    for (let idx = 0; idx < first.times.length; idx += 1) {
      if (series.times[idx] !== first.times[idx]) {
        return null;
      }
    }
  }
  return first.times;
}

/**
 * Compute the hover index for each visible series at a given time.
 */
export function computeHoverIndices(
  visibleSeries: ForecastSeries[],
  time: number,
): Map<string, number> {
  const shared = sharedTimeline(visibleSeries);
  if (shared) {
    const nearestIdx = nearestArrayIndex(shared, time);
    const stepIdx = stepArrayIndex(shared, time);
    return new Map(
      visibleSeries.map((series) => [series.key, series.drawType === "step" ? stepIdx : nearestIdx]),
    );
  }
  const indices = new Map<string, number>();
  for (const series of visibleSeries) {
    const idx =
      series.drawType === "step" ? stepArrayIndex(series.times, time) : nearestArrayIndex(series.times, time);
    indices.set(series.key, idx);
  }
  return indices;
}
