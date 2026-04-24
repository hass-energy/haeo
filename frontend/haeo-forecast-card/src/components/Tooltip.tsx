import type { JSX } from "preact";
import { t } from "../i18n";
import type { TooltipSectionId } from "../tooltip-helpers";

/** Cap rows per tooltip group to prevent the tooltip from obscuring the chart. */
const MAX_TOOLTIP_ROWS_PER_GROUP = 8;

interface TooltipRow {
  key: string;
  label: string;
  value: number;
  unit: string;
  color: string;
  lane: TooltipSectionId;
}

interface TooltipTotal {
  lane: TooltipSectionId;
  value: number;
  unit: string;
}

interface TooltipProps {
  locale: string;
  panelTimeMs: number;
  rows: TooltipRow[];
  totals: TooltipTotal[];
  emphasizedKeys: Set<string>;
}

export function Tooltip(props: TooltipProps): JSX.Element | null {
  if (props.rows.length === 0) {
    return null;
  }
  const groups = new Map<TooltipSectionId, TooltipRow[]>();
  for (const row of props.rows) {
    const rows = groups.get(row.lane) ?? [];
    rows.push(row);
    groups.set(row.lane, rows);
  }
  const laneLabel = (lane: TooltipSectionId): string => {
    const keyByLane: Record<TooltipSectionId, string> = {
      produced: "tooltip.section.produced",
      available: "tooltip.section.available",
      consumed: "tooltip.section.consumed",
      possible: "tooltip.section.possible",
      price: "tooltip.section.price",
      soc: "tooltip.section.soc",
    };
    return t(props.locale, keyByLane[lane]);
  };
  const totalLabel = (lane: TooltipSectionId): string => {
    const keyByLane: Partial<Record<TooltipSectionId, string>> = {
      produced: "tooltip.total.produced",
      available: "tooltip.total.available",
      consumed: "tooltip.total.consumed",
      possible: "tooltip.total.possible",
    };
    const translationKey = keyByLane[lane];
    return translationKey !== undefined
      ? t(props.locale, translationKey)
      : t(props.locale, "tooltip.total.generic", { lane });
  };
  return (
    <div className="tooltip">
      <div className="tooltipTime">{new Date(props.panelTimeMs).toLocaleString(props.locale)}</div>
      {[...groups.entries()].map(([lane, rows]) => (
        <div key={lane} className="tooltipGroup">
          <div className="tooltipGroupTitle">{laneLabel(lane)}</div>
          {rows.slice(0, MAX_TOOLTIP_ROWS_PER_GROUP).map((row) => (
            <div key={row.key} className={`tooltipRow ${props.emphasizedKeys.has(row.key) ? "active" : ""}`}>
              <span className="tooltipDot" style={{ background: row.color }} />
              <span>{row.label}</span>
              <span>
                {row.value.toFixed(2)} {row.unit}
              </span>
            </div>
          ))}
        </div>
      ))}
      {props.totals.length > 0 && (
        <div className="tooltipTotals">
          {props.totals.map((total) => (
            <div key={total.lane}>
              <strong>{totalLabel(total.lane)}:</strong> {total.value.toFixed(2)} {total.unit}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
