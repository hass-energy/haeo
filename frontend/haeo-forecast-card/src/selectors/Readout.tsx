import { mdiChartLine } from "@mdi/js";
import type { JSX } from "preact";

import { Sparkline } from "./Sparkline";

const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumSignificantDigits: 3 });

/** A number short enough for a readout, such as 0.501, 12.3 or 1.23K. */
export function shortNumber(value: number): string {
  return compact.format(value);
}

/** What an input shows of a value in the readout beside it. */
export type ReadoutContent =
  | { kind: "series"; values: number[] }
  | { kind: "value"; text: string; unit: string; fixed: boolean };

/**
 * The same-sized box at the start of every chip and choice, showing the value an
 * input reads: a forecast's sparkline, or a current or fixed value and its unit.
 * Lining them up makes them read as the same thing, a plot or a number.
 */
export function Readout({ content, label }: { content: ReadoutContent; label?: string | undefined }): JSX.Element {
  const labelled: JSX.HTMLAttributes<HTMLSpanElement> =
    label === undefined ? { "aria-hidden": true } : { role: "img", "aria-label": label };
  if (content.kind === "series") {
    return (
      <span class="readout" {...labelled}>
        {content.values.length > 1 ? (
          <Sparkline values={content.values} />
        ) : (
          <svg class="icon" viewBox="0 0 24 24">
            <path d={mdiChartLine} />
          </svg>
        )}
      </span>
    );
  }
  return (
    <span class={`readout value${content.fixed ? " fixed" : ""}`} {...labelled}>
      <span class="readout-value">{content.text}</span>
      {content.unit !== "" && <span class="readout-unit">{content.unit}</span>}
    </span>
  );
}
