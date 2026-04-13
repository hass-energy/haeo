import type { JSX } from "preact";
import { t } from "../i18n";

interface TooltipRow {
  key: string;
  label: string;
  value: number;
  unit: string;
  color: string;
  lane: string;
}

interface TooltipTotal {
  lane: string;
  value: number;
  unit: string;
}

interface TooltipProps {
  locale: string;
  hoverTimeMs: number | null;
  rows: TooltipRow[];
  totals: TooltipTotal[];
  emphasizedKeys: Set<string>;
}

export function Tooltip(props: TooltipProps): JSX.Element | null {
  if (props.hoverTimeMs === null || props.rows.length === 0) {
    return null;
  }
  const groups = new Map<string, TooltipRow[]>();
  for (const row of props.rows) {
    const rows = groups.get(row.lane) ?? [];
    rows.push(row);
    groups.set(row.lane, rows);
  }
  const laneLabel = (lane: string): string => {
    const keyByLane: Record<string, string> = {
      Produced: "tooltip.section.produced",
      Available: "tooltip.section.available",
      Consumed: "tooltip.section.consumed",
      Possible: "tooltip.section.possible",
      Price: "tooltip.section.price",
      "State of charge": "tooltip.section.soc",
    };
    return keyByLane[lane] ? t(props.locale, keyByLane[lane]) : lane;
  };
  const totalLabel = (lane: string): string => {
    if (lane === "Produced") {
      return t(props.locale, "tooltip.total.produced");
    }
    if (lane === "Available") {
      return t(props.locale, "tooltip.total.available");
    }
    if (lane === "Consumed") {
      return t(props.locale, "tooltip.total.consumed");
    }
    if (lane === "Possible") {
      return t(props.locale, "tooltip.total.possible");
    }
    return t(props.locale, "tooltip.total.generic", { lane });
  };
  return (
    <div className="tooltip">
      <div className="tooltipTime">{new Date(props.hoverTimeMs).toLocaleString()}</div>
      {[...groups.entries()].map(([lane, rows]) => (
        <div key={lane} className="tooltipGroup">
          <div className="tooltipGroupTitle">{laneLabel(lane)}</div>
          {rows.slice(0, 8).map((row) => (
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
