import type { JSX } from "preact";

const WIDTH = 36;
const HEIGHT = 18;
const PADDING = 2;

/** The points of a line through the values, scaled to fill the box; a flat forecast runs through the middle. */
export function sparklinePoints(values: number[]): string {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const x = (index: number): number => (index / (values.length - 1)) * WIDTH;
  const y = (value: number): number =>
    max === min ? HEIGHT / 2 : PADDING + (1 - (value - min) / (max - min)) * (HEIGHT - 2 * PADDING);
  return values.map((value, index) => `${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
}

/** A forecast's shape from now to its end, with no axes. */
export function Sparkline({ values }: { values: number[] }): JSX.Element {
  const line = sparklinePoints(values);
  return (
    <svg class="sparkline" viewBox={`0 0 ${WIDTH} ${HEIGHT}`}>
      <polygon class="sparkline-area" points={`0,${HEIGHT} ${line} ${WIDTH},${HEIGHT}`} />
      <polyline class="sparkline-line" points={line} />
    </svg>
  );
}
