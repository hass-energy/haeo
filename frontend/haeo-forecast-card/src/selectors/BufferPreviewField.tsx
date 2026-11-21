import { useEffect, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import type { SelectorHass, Translate } from "./types";

/** What the integration's `haeo/buffer_preview` command returns. */
export interface BufferPreviewResult {
  /** The horizon's boundaries, in epoch seconds. */
  times: number[];
  /** "reserve" or "headroom". */
  kind: string;
  /** The combined state of charge the buffer keeps the batteries above (reserve) or below (headroom), 0 to 1. */
  buffer: number[];
  /** The combined state of charge the batteries would follow with the buffer, 0 to 1. */
  plan: number[] | null;
  /** The combined state of charge the batteries follow in the hub's plan now, 0 to 1. */
  current: number[] | null;
  /** The local midnights within the horizon. */
  days: number[];
}

export interface BufferPreviewProps {
  hass: SelectorHass | null;
  entryId: string;
  replaces: string | null;
  /** Read the values the rest of the form holds now. */
  readForm: () => Record<string, unknown> | null;
  t: Translate;
}

const WIDTH = 300;
const HEIGHT = 110;
const PAD = 4;
/** How long the form settles after a change before the buffer is planned again. */
const DEBOUNCE_MS = 400;

function linePoints(times: number[], values: number[], x: (time: number) => number, y: (v: number) => number): string {
  return values.map((value, index) => `${x(times[index] ?? 0).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
}

/**
 * What the buffer being configured would do: the line it keeps the batteries
 * above (a reserve) or below (headroom), shaded on the side it protects, the
 * charge the batteries would follow with it, and their charge in the plan now.
 */
export function BufferPreviewField({ hass, entryId, replaces, readForm, t }: BufferPreviewProps): JSX.Element | null {
  const [result, setResult] = useState<BufferPreviewResult | null>(null);
  const last = useRef("");
  const callWS = hass?.callWS;

  useEffect(() => {
    if (callWS === undefined) {
      return undefined;
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    let current = true;
    const plan = (): void => {
      const form = readForm();
      const key = JSON.stringify(form);
      if (form === null || key === last.current) {
        return;
      }
      last.current = key;
      callWS<BufferPreviewResult>({ type: "haeo/buffer_preview", entry_id: entryId, replaces, buffer: form }).then(
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
    };
    const schedule = (): void => {
      clearTimeout(timer);
      timer = setTimeout(plan, DEBOUNCE_MS);
    };
    // Every field reports its changes with a composed value-changed event, which reaches the document
    document.addEventListener("value-changed", schedule);
    schedule();
    return () => {
      current = false;
      clearTimeout(timer);
      document.removeEventListener("value-changed", schedule);
    };
  }, [callWS, entryId, replaces]);

  if (result === null || result.buffer.length < 2) {
    return null;
  }
  const from = result.times[0] ?? 0;
  const to = result.times.at(-1) ?? from + 1;
  const x = (time: number): number => ((time - from) / Math.max(to - from, 1)) * WIDTH;
  const y = (value: number): number => PAD + (1 - Math.min(Math.max(value, 0), 1)) * (HEIGHT - 2 * PAD);
  const bufferLine = linePoints(result.times, result.buffer, x, y);
  const edge = result.kind === "headroom" ? y(1) : y(0);
  const zone = `0,${edge.toFixed(1)} ${bufferLine} ${WIDTH},${edge.toFixed(1)}`;
  const label = [
    t("buffer_preview.options.with_buffer"),
    t("buffer_preview.options.now"),
    t("buffer_preview.options.buffer"),
  ].join(", ");

  return (
    <div class="buffer-preview">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img" aria-label={label}>
        {result.days.map((day) => (
          <line key={day} class="plot-day" x1={x(day)} x2={x(day)} y1={0} y2={HEIGHT} />
        ))}
        <polygon class="buffer-zone" points={zone} />
        <polyline class="buffer-line" points={bufferLine} />
        {result.plan !== null && <polyline class="buffer-plan" points={linePoints(result.times, result.plan, x, y)} />}
        {/* Drawn over the plan with the buffer, so where the buffer changes nothing it shows inside it */}
        {result.current !== null && (
          <polyline class="buffer-now" points={linePoints(result.times, result.current, x, y)} />
        )}
      </svg>
      <div class="buffer-legend" aria-hidden="true">
        <span>
          <i class="swatch buffer-plan" />
          {t("buffer_preview.options.with_buffer")}
        </span>
        <span>
          <i class="swatch buffer-now" />
          {t("buffer_preview.options.now")}
        </span>
        <span>
          <i class="swatch buffer-line" />
          {t("buffer_preview.options.buffer")}
        </span>
      </div>
    </div>
  );
}
