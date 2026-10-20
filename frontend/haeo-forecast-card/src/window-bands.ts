import type { ForecastSeries } from "./types";

/** A span of time a window is open, in epoch milliseconds. */
export interface WindowInterval {
  start: number;
  end: number;
}

/** One window drawn on the chart: a tint across the plot and a strip along its top. */
export interface WindowBand {
  key: string;
  seriesKey: string;
  color: string;
  x: number;
  width: number;
  row: number;
}

/**
 * Return the spans a window series is open, joining consecutive open periods.
 *
 * Each value covers the period from its time to the next one. The last
 * period has no next time, so it is taken to last as long as the one before.
 */
export function windowIntervals(times: ArrayLike<number>, values: ArrayLike<number>): WindowInterval[] {
  const intervals: WindowInterval[] = [];
  const count = Math.min(times.length, values.length);
  for (let idx = 0; idx < count; idx += 1) {
    if ((values[idx] ?? 0) <= 0) {
      continue;
    }
    const start = times[idx] ?? 0;
    const end = idx + 1 < times.length ? (times[idx + 1] ?? start) : start + (start - (times[idx - 1] ?? start));
    const last = intervals.at(-1);
    if (last?.end === start) {
      last.end = end;
    } else {
      intervals.push({ start, end });
    }
  }
  return intervals;
}

/** Return the bands for window series, one strip row per series in the order given. */
export function windowBands(series: ForecastSeries[], xScale: (time: number) => number): WindowBand[] {
  return series.flatMap((item, row) =>
    windowIntervals(item.times, item.values).map((interval, idx) => {
      const x = xScale(interval.start);
      return {
        key: `${item.key}:${idx}`,
        seriesKey: item.key,
        color: item.color,
        x,
        width: Math.max(xScale(interval.end) - x, 0),
        row,
      };
    })
  );
}
