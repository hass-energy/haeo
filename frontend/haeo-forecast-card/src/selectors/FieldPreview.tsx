import { useEffect, useState } from "preact/hooks";
import type { JSX } from "preact";

import { Readout, shortNumber } from "./Readout";
import type { InputPreviewConfig, SelectorHass, Translate } from "./types";

/** What the integration's ``haeo/input_preview`` command returns. */
export interface PreviewResult {
  /** The horizon's boundaries, in epoch seconds. */
  times: number[];
  /** The combined value at each boundary, or in each interval. */
  values: number[];
  /** The local midnights within the horizon, in Home Assistant's time zone. */
  days: number[];
}

/** How long entity changes settle before the preview is fetched again. */
const DEBOUNCE_MS = 150;
const WIDTH = 300;
const HEIGHT = 48;
const PAD = 3;
const SECONDS_PER_HOUR = 3600;

/** The plotted path and the local midnights within it, scaled to the plot, and the plot's range and span. */
export function previewGeometry(
  result: PreviewResult,
  boundaries: boolean
): { line: string; area: string; midnights: number[]; zero: number | null; min: number; max: number; hours: number } {
  // Each value starts at its boundary; an interval's value holds until the next boundary
  const starts = result.times.slice(0, result.values.length);
  const ends = boundaries ? starts : result.times.slice(1, result.values.length + 1);
  // The first value is now, shown beside the plot, so the plot is what follows
  const values = result.values.slice(1);
  const from = starts[1] ?? 0;
  const to = ends.at(-1) ?? from + 1;
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const x = (time: number): number => ((time - from) / Math.max(to - from, 1)) * WIDTH;
  const y = (value: number): number => PAD + (1 - (value - min) / Math.max(max - min, 1e-9)) * (HEIGHT - 2 * PAD);
  const points: string[] = [];
  values.forEach((value, index) => {
    points.push(`${x(starts[index + 1] ?? from).toFixed(1)},${y(value).toFixed(1)}`);
    if (!boundaries) {
      points.push(`${x(ends[index + 1] ?? to).toFixed(1)},${y(value).toFixed(1)}`);
    }
  });
  const line = points.join(" ");
  const base = y(Math.max(min, 0)).toFixed(1);
  const area = `0,${base} ${line} ${WIDTH},${base}`;
  const midnights = result.days.filter((day) => day > from && day < to).map(x);
  const hours = Math.round((to - from) / SECONDS_PER_HOUR);
  return { line, area, midnights, zero: min < 0 ? y(0) : null, min, max, hours };
}

export interface FieldPreviewProps {
  hass: SelectorHass | null;
  preview: InputPreviewConfig;
  entityIds: string[];
  unit: string;
  t: Translate;
}

/**
 * What a field's entities combine to on the hub's horizon, as the optimizer will
 * read them: the first interval's value in a readout, then the combined forecast.
 */
export function FieldPreview({ hass, preview, entityIds, unit, t }: FieldPreviewProps): JSX.Element | null {
  const [result, setResult] = useState<PreviewResult | null>(null);
  const callWS = hass?.callWS;
  // A chosen entity's update changes what the field combines to, so it fetches the preview again
  const key = entityIds.map((entityId) => `${entityId}@${hass?.states[entityId]?.last_updated ?? ""}`).join(",");

  useEffect(() => {
    if (callWS === undefined || entityIds.length === 0) {
      setResult(null);
      return undefined;
    }
    let current = true;
    const timer = setTimeout(() => {
      callWS<PreviewResult>({ type: "haeo/input_preview", ...preview, entity_ids: entityIds }).then(
        (answer) => {
          if (current) {
            setResult(answer);
          }
        },
        () => {
          if (current) {
            setResult(null);
          }
        }
      );
    }, DEBOUNCE_MS);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [key, callWS, preview.entry_id, preview.output_type, preview.boundaries, preview.non_negative]);

  if (result === null || result.values.length < 2) {
    return null;
  }
  const geometry = previewGeometry(result, preview.boundaries);
  const withUnit = (value: number): string => `${shortNumber(value, hass?.language)} ${unit}`.trim();
  const now = result.values[0] ?? 0;
  const label = t("input.options.preview", {
    now: withUnit(now),
    min: withUnit(geometry.min),
    max: withUnit(geometry.max),
    hours: String(geometry.hours),
  });

  return (
    <div class="preview-plot" role="img" aria-label={label}>
      <Readout content={{ kind: "value", text: shortNumber(now, hass?.language), unit, fixed: false }} />
      <div class="plot">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" aria-hidden="true">
          {geometry.midnights.map((position) => (
            <line key={position} class="plot-day" x1={position} x2={position} y1={0} y2={HEIGHT} />
          ))}
          {geometry.zero !== null && <line class="plot-zero" x1={0} x2={WIDTH} y1={geometry.zero} y2={geometry.zero} />}
          <polygon class="sparkline-area" points={geometry.area} />
          <polyline class="sparkline-line" points={geometry.line} />
        </svg>
        <span class="plot-max" aria-hidden="true">
          {withUnit(geometry.max)}
        </span>
      </div>
    </div>
  );
}
