import type { ForecastPoint } from "./types";

export function clamp(value: number, min: number, max: number): number {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

export function linearScale(
  value: number,
  domainMin: number,
  domainMax: number,
  rangeMin: number,
  rangeMax: number
): number {
  if (domainMax <= domainMin) {
    return rangeMin;
  }
  const ratio = (value - domainMin) / (domainMax - domainMin);
  return rangeMin + ratio * (rangeMax - rangeMin);
}

export function nearestPointIndex(points: ForecastPoint[], timestamp: number): number {
  if (points.length < 2) {
    return 0;
  }
  let low = 0;
  let high = points.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    const point = points[mid];
    if (!point) {
      return 0;
    }
    const t = point.time;
    if (t < timestamp) {
      low = mid + 1;
    } else if (t > timestamp) {
      high = mid - 1;
    } else {
      return mid;
    }
  }
  if (low <= 0) {
    return 0;
  }
  if (low >= points.length) {
    return points.length - 1;
  }
  const before = points[low - 1];
  const after = points[low];
  if (!before || !after) {
    return 0;
  }
  return Math.abs(before.time - timestamp) <= Math.abs(after.time - timestamp) ? low - 1 : low;
}

export function nearestArrayIndex(times: Float64Array, timestamp: number): number {
  if (times.length < 2) {
    return 0;
  }
  let low = 0;
  let high = times.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    const t = times[mid];
    if (t === undefined) {
      return 0;
    }
    if (t < timestamp) {
      low = mid + 1;
    } else if (t > timestamp) {
      high = mid - 1;
    } else {
      return mid;
    }
  }
  if (low <= 0) {
    return 0;
  }
  if (low >= times.length) {
    return times.length - 1;
  }
  const before = times[low - 1];
  const after = times[low];
  if (before === undefined || after === undefined) {
    return 0;
  }
  return Math.abs(before - timestamp) <= Math.abs(after - timestamp) ? low - 1 : low;
}

export function stepPath(points: ForecastPoint[], x: (time: number) => number, y: (value: number) => number): string {
  if (points.length === 0) {
    return "";
  }
  const first = points[0];
  if (!first) {
    return "";
  }
  let path = `M ${x(first.time)} ${y(first.value)}`;
  for (let i = 1; i < points.length; i += 1) {
    const prev = points[i - 1];
    const curr = points[i];
    if (!prev || !curr) {
      continue;
    }
    path += ` L ${x(curr.time)} ${y(prev.value)} L ${x(curr.time)} ${y(curr.value)}`;
  }
  return path;
}

export function linePath(points: ForecastPoint[], x: (time: number) => number, y: (value: number) => number): string {
  if (points.length === 0) {
    return "";
  }
  const [first, ...rest] = points;
  if (!first) {
    return "";
  }
  let path = `M ${x(first.time)} ${y(first.value)}`;
  for (const point of rest) {
    path += ` L ${x(point.time)} ${y(point.value)}`;
  }
  return path;
}
