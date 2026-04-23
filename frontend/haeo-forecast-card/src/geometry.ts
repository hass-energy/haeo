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

export function nearestArrayIndex(times: Float64Array, timestamp: number): number {
  if (times.length < 2) {
    return 0;
  }
  let low = 0;
  let high = times.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    const t = times[mid]!;
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
  const before = times[low - 1]!;
  const after = times[low]!;
  return Math.abs(before - timestamp) <= Math.abs(after - timestamp) ? low - 1 : low;
}

export function stepPath(
  times: Float64Array,
  values: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number,
): string {
  if (times.length === 0) return "";
  let path = `M ${x(times[0]!)} ${y(values[0]!)}`;
  for (let i = 1; i < times.length; i += 1) {
    path += ` L ${x(times[i]!)} ${y(values[i - 1]!)} L ${x(times[i]!)} ${y(values[i]!)}`;
  }
  return path;
}

export function linePath(
  times: Float64Array,
  values: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number,
): string {
  if (times.length === 0) return "";
  let path = `M ${x(times[0]!)} ${y(values[0]!)}`;
  for (let i = 1; i < times.length; i += 1) {
    path += ` L ${x(times[i]!)} ${y(values[i]!)}`;
  }
  return path;
}

export function stepAreaPath(
  times: Float64Array,
  lower: Float64Array,
  upper: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number
): string {
  if (times.length === 0) {
    return "";
  }

  let path = `M ${x(times[0]!)} ${y(upper[0]!)}`;
  for (let idx = 1; idx < times.length; idx += 1) {
    path += ` L ${x(times[idx]!)} ${y(upper[idx - 1]!)} L ${x(times[idx]!)} ${y(upper[idx]!)}`;
  }

  const last = times.length - 1;
  path += ` L ${x(times[last]!)} ${y(lower[last]!)}`;

  for (let idx = times.length - 1; idx >= 1; idx -= 1) {
    path += ` L ${x(times[idx]!)} ${y(lower[idx - 1]!)} L ${x(times[idx - 1]!)} ${y(lower[idx - 1]!)}`;
  }
  return `${path} Z`;
}
