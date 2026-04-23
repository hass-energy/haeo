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

export function stepPath(
  times: Float64Array,
  values: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number,
): string {
  if (times.length === 0) return "";
  const firstTime = times[0];
  const firstValue = values[0];
  if (firstTime === undefined || firstValue === undefined) return "";
  let path = `M ${x(firstTime)} ${y(firstValue)}`;
  for (let i = 1; i < times.length; i += 1) {
    const prevValue = values[i - 1];
    const currTime = times[i];
    const currValue = values[i];
    if (prevValue === undefined || currTime === undefined || currValue === undefined) continue;
    path += ` L ${x(currTime)} ${y(prevValue)} L ${x(currTime)} ${y(currValue)}`;
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
  const firstTime = times[0];
  const firstValue = values[0];
  if (firstTime === undefined || firstValue === undefined) return "";
  let path = `M ${x(firstTime)} ${y(firstValue)}`;
  for (let i = 1; i < times.length; i += 1) {
    const currTime = times[i];
    const currValue = values[i];
    if (currTime === undefined || currValue === undefined) continue;
    path += ` L ${x(currTime)} ${y(currValue)}`;
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
  const firstTime = times[0];
  const firstUpper = upper[0];
  if (firstTime === undefined || firstUpper === undefined) {
    return "";
  }

  let path = `M ${x(firstTime)} ${y(firstUpper)}`;
  for (let idx = 1; idx < times.length; idx += 1) {
    const currTime = times[idx];
    const prevUpper = upper[idx - 1];
    const currUpper = upper[idx];
    if (currTime === undefined || prevUpper === undefined || currUpper === undefined) {
      continue;
    }
    path += ` L ${x(currTime)} ${y(prevUpper)} L ${x(currTime)} ${y(currUpper)}`;
  }

  const lastTime = times[times.length - 1];
  const lastLower = lower[times.length - 1];
  if (lastTime === undefined || lastLower === undefined) {
    return "";
  }
  path += ` L ${x(lastTime)} ${y(lastLower)}`;

  for (let idx = times.length - 1; idx >= 1; idx -= 1) {
    const currTime = times[idx];
    const prevTime = times[idx - 1];
    const prevLower = lower[idx - 1];
    if (currTime === undefined || prevTime === undefined || prevLower === undefined) {
      continue;
    }
    path += ` L ${x(currTime)} ${y(prevLower)} L ${x(prevTime)} ${y(prevLower)}`;
  }
  return `${path} Z`;
}
