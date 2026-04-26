import type { JSX } from "preact";
import { t } from "../i18n";
import type { TooltipSectionId } from "../tooltip-helpers";

/** Cap rows per tooltip group to prevent the tooltip from obscuring the chart. */
const MAX_TOOLTIP_ROWS_PER_GROUP = 8;

interface TooltipRow {
  key: string;
  possibleKey?: string;
  label: string;
  value: number;
  possibleValue?: number;
  unit: string;
  color: string;
  lane: TooltipSectionId;
}

interface TooltipProps {
  locale: string;
  panelTimeMs: number;
  rows: TooltipRow[];
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
  return (
    <div className="tooltip">
      <div className="tooltipTime">{new Date(props.panelTimeMs).toLocaleString(props.locale)}</div>
      {[...groups.entries()].map(([lane, rows]) => (
        <div key={lane} className="tooltipGroup">
          <div className="tooltipGroupTitle">{laneLabel(lane)}</div>
          {rows.slice(0, MAX_TOOLTIP_ROWS_PER_GROUP).map((row) => (
            <div
              key={row.key}
              className={`tooltipRow ${
                props.emphasizedKeys.has(row.key) ||
                (row.possibleKey !== undefined ? props.emphasizedKeys.has(row.possibleKey) : false)
                  ? "active"
                  : ""
              }`}
            >
              <span className="tooltipDot" style={{ background: row.color }} />
              <span>{row.label}</span>
              <span>
                {row.possibleValue === undefined
                  ? row.value.toFixed(2)
                  : `${row.value.toFixed(2)} / ${row.possibleValue.toFixed(2)}`}{" "}
                {row.unit}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
