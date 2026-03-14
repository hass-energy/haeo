import type { JSX } from "preact";

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
    if (lane === "power") {
      return "Power";
    }
    if (lane === "price") {
      return "Price";
    }
    if (lane === "soc") {
      return "State of charge";
    }
    return lane;
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
      <div className="tooltipTotals">
        {props.totals.map((total) => (
          <div key={total.lane}>
            <strong>{total.lane} total:</strong> {total.value.toFixed(2)} {total.unit}
          </div>
        ))}
      </div>
    </div>
  );
}
