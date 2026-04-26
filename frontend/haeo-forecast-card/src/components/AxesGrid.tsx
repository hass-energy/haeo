import type { JSX } from "preact";
import { t } from "../i18n";

/** Cached Intl.DateTimeFormat for axis tick labels, keyed by locale. */
let cachedTimeFormatter: Intl.DateTimeFormat | undefined;
let cachedTimeFormatterLocale = "";

function formatTickTime(ms: number, locale: string): string {
  if (locale !== cachedTimeFormatterLocale || cachedTimeFormatter === undefined) {
    cachedTimeFormatter = new Intl.DateTimeFormat(locale !== "" ? locale : undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
    cachedTimeFormatterLocale = locale;
  }
  return cachedTimeFormatter.format(ms);
}

interface AxesGridProps {
  locale: string;
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
  xMin: number;
  xMax: number;
  xScale: (time: number) => number;
  yScalePower: (value: number) => number;
  yScalePrice: (value: number) => number;
  yScaleSoc: (value: number) => number;
  powerMin: number;
  powerMax: number;
  priceMin: number;
  priceMax: number;
  socMin: number;
  socMax: number;
}

const TIME_STEPS_MS = [
  60_000,
  2 * 60_000,
  5 * 60_000,
  10 * 60_000,
  15 * 60_000,
  30 * 60_000,
  60 * 60_000,
  2 * 60 * 60_000,
  4 * 60 * 60_000,
  6 * 60 * 60_000,
  12 * 60 * 60_000,
  24 * 60 * 60_000,
];

function niceStep(rawStep: number): number {
  if (!Number.isFinite(rawStep) || rawStep <= 0) {
    return 1;
  }
  const power = 10 ** Math.floor(Math.log10(rawStep));
  const scaled = rawStep / power;
  if (scaled <= 1) {
    return power;
  }
  if (scaled <= 2) {
    return 2 * power;
  }
  if (scaled <= 5) {
    return 5 * power;
  }
  return 10 * power;
}

function niceLinearTicks(min: number, max: number, targetCount: number, includeZero: boolean): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [0];
  }
  if (min === max) {
    return [min];
  }
  const lo = includeZero ? Math.min(min, 0) : min;
  const hi = includeZero ? Math.max(max, 0) : max;
  const step = niceStep((hi - lo) / Math.max(1, targetCount));
  const start = Math.floor(lo / step) * step;
  const end = Math.ceil(hi / step) * step;
  const out: number[] = [];
  for (let value = start; value <= end + step * 0.25; value += step) {
    out.push(Math.abs(value) < step * 1e-6 ? 0 : value);
  }
  return out;
}

function minorFromMajor(major: number[]): number[] {
  if (major.length < 2) {
    return [];
  }
  const first = major[0];
  const second = major[1];
  if (first === undefined || second === undefined) {
    return [];
  }
  const step = second - first;
  const minorStep = step / 5;
  const start = first;
  const end = major[major.length - 1];
  if (!Number.isFinite(minorStep) || minorStep <= 0 || end === undefined) {
    return [];
  }
  const out: number[] = [];
  for (let value = start; value <= end + minorStep * 0.25; value += minorStep) {
    out.push(Math.abs(value) < minorStep * 1e-6 ? 0 : value);
  }
  return out.filter((value) => !major.some((tick) => Math.abs(tick - value) < minorStep * 0.1));
}

function chooseTimeStep(min: number, max: number, targetCount: number): number {
  const range = max - min;
  const desired = range / Math.max(2, targetCount);
  for (const step of TIME_STEPS_MS) {
    if (step >= desired) {
      return step;
    }
  }
  return TIME_STEPS_MS[TIME_STEPS_MS.length - 1] ?? 60 * 60_000;
}

function alignTickStart(min: number, step: number): number {
  const date = new Date(min);
  date.setSeconds(0, 0);
  const minuteMs = 60_000;
  const hourMs = 60 * minuteMs;
  const dayMs = 24 * hourMs;

  if (step >= dayMs) {
    date.setHours(0, 0, 0, 0);
  } else if (step >= hourMs) {
    const hoursPerStep = Math.max(1, Math.round(step / hourMs));
    const hour = date.getHours();
    date.setMinutes(0, 0, 0);
    date.setHours(hour - (hour % hoursPerStep));
  } else {
    const minutesPerStep = Math.max(1, Math.round(step / minuteMs));
    const minute = date.getMinutes();
    date.setMinutes(minute - (minute % minutesPerStep), 0, 0);
  }

  let aligned = date.getTime();
  while (aligned < min) {
    aligned += step;
  }
  return aligned;
}

function timeTicks(min: number, max: number, targetCount: number): number[] {
  if (max <= min) {
    return [min];
  }
  const step = chooseTimeStep(min, max, targetCount);
  const start = alignTickStart(min, step);
  const end = Math.ceil(max / step) * step;
  const out: number[] = [];
  for (let time = start; time <= end + step * 0.25; time += step) {
    if (time >= min - step * 0.01 && time <= max + step * 0.01) {
      out.push(time);
    }
  }
  return out;
}

function hasNearbyLabel(y: number, others: number[], spacing: number): boolean {
  return others.some((other) => Math.abs(other - y) < spacing);
}

function priceAtY(y: number, top: number, bottom: number, zeroY: number, priceMin: number, priceMax: number): number {
  const positiveMax = Math.max(priceMax, 0.001);
  const negativeMin = Math.min(priceMin, -0.001);
  if (y <= zeroY) {
    const span = Math.max(1e-6, zeroY - top);
    const t = (y - top) / span;
    return positiveMax * (1 - t);
  }
  const span = Math.max(1e-6, bottom - zeroY);
  const t = (y - zeroY) / span;
  return negativeMin * t;
}

function dedupeClose(values: number[], epsilon: number): number[] {
  const out: number[] = [];
  for (const value of values) {
    if (!out.some((existing) => Math.abs(existing - value) < epsilon)) {
      out.push(value);
    }
  }
  return out;
}

export function AxesGrid(props: AxesGridProps): JSX.Element {
  const clampYAxisLabelY = (y: number): number => Math.min(props.bottom - 2, Math.max(props.top + 10, y));
  const isVisibleY = (y: number): boolean => y >= props.top - 0.5 && y <= props.bottom + 0.5;
  const rightAxisX = props.width - props.right;
  const rightMarginEndX = props.width - 4;
  const xMajor = timeTicks(props.xMin, props.xMax, 7);
  const xMinor = timeTicks(props.xMin, props.xMax, 13);
  const yMajor = niceLinearTicks(props.powerMin, props.powerMax, 6, true).filter((value) =>
    isVisibleY(props.yScalePower(value))
  );
  const yMinor = minorFromMajor(yMajor).filter((value) => isVisibleY(props.yScalePower(value)));
  const zeroY = props.yScalePower(0);
  const priceMajor = dedupeClose(
    yMajor
      .map((value) => props.yScalePower(value))
      .map((y) => priceAtY(y, props.top, props.bottom, zeroY, props.priceMin, props.priceMax))
      .filter((value) => value >= props.priceMin - 1e-6 && value <= props.priceMax + 1e-6),
    1e-3
  );
  const socMajor = [0, 20, 40, 60, 80, 100];
  const priceLabelYs = priceMajor.map((value) => props.yScalePrice(value));
  const socVisible = socMajor.filter((value) => !hasNearbyLabel(props.yScaleSoc(value), priceLabelYs, 12));

  return (
    <>
      {xMinor.map((time, idx) => (
        <line
          key={`x-minor-${idx}`}
          className="gridMinor"
          x1={props.xScale(time)}
          y1={props.top}
          x2={props.xScale(time)}
          y2={props.bottom}
        />
      ))}
      {yMinor.map((value, idx) => (
        <line
          key={`y-minor-${idx}`}
          className="gridMinor"
          x1={props.left}
          y1={props.yScalePower(value)}
          x2={props.width - props.right}
          y2={props.yScalePower(value)}
        />
      ))}

      {xMajor.map((time, idx) => (
        <g key={`x-major-${idx}`}>
          <line
            className="gridMajor"
            x1={props.xScale(time)}
            y1={props.top}
            x2={props.xScale(time)}
            y2={props.bottom}
          />
          <text className="axisTickLabel" x={props.xScale(time)} y={props.bottom + 16} textAnchor="middle">
            {formatTickTime(time, props.locale)}
          </text>
        </g>
      ))}

      {yMajor.map((value, idx) => (
        <g key={`y-major-${idx}`}>
          <line
            className="gridMajor"
            x1={props.left}
            y1={props.yScalePower(value)}
            x2={props.width - props.right}
            y2={props.yScalePower(value)}
          />
          <text
            className="axisTickLabel"
            x={props.left - 8}
            y={clampYAxisLabelY(props.yScalePower(value))}
            textAnchor="end"
            dominantBaseline="middle"
          >
            {value.toFixed(Math.abs(value) >= 10 ? 0 : 1)}
          </text>
        </g>
      ))}

      {priceMajor.map((value, idx) => (
        <text
          key={`price-major-${idx}`}
          className="axisTickLabel"
          x={rightAxisX + 6}
          y={clampYAxisLabelY(props.yScalePrice(value))}
          textAnchor="start"
          dominantBaseline="middle"
        >
          {value.toFixed(Math.abs(value) >= 10 ? 0 : 2)}
        </text>
      ))}

      {socVisible.map((value, idx) => (
        <text
          key={`soc-major-${idx}`}
          className="axisTickLabel"
          x={rightMarginEndX}
          y={clampYAxisLabelY(props.yScaleSoc(value))}
          textAnchor="end"
          dominantBaseline="middle"
        >
          {value}%
        </text>
      ))}

      <line
        className="axisZero"
        x1={props.left}
        y1={props.yScalePower(0)}
        x2={props.width - props.right}
        y2={props.yScalePower(0)}
      />
      <line className="axisBase" x1={props.left} y1={props.bottom} x2={props.width - props.right} y2={props.bottom} />
      <line className="axisBase" x1={props.left} y1={props.top} x2={props.left} y2={props.bottom} />
      <line className="axisBase" x1={rightAxisX} y1={props.top} x2={rightAxisX} y2={props.bottom} />

      <text className="axisLabelStrong" x={props.left - 8} y={props.top - 6} textAnchor="end">
        {t(props.locale, "axis.power")}
      </text>
      <text className="axisLabelStrong" x={rightAxisX + 6} y={props.top - 6} textAnchor="start">
        {t(props.locale, "axis.price")}
      </text>
      <text className="axisLabelStrong" x={rightMarginEndX} y={props.bottom + 20} textAnchor="end">
        {t(props.locale, "axis.soc")}
      </text>
    </>
  );
}
