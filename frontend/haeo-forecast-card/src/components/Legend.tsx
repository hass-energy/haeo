import type { JSX } from "preact";

import type { ForecastSeries } from "../types";

interface LegendProps {
  series: ForecastSeries[];
  highlightedSeries: string | null;
  onHighlight: (key: string | null) => void;
}

export function Legend(props: LegendProps): JSX.Element {
  return (
    <div className="legend">
      {props.series.map((series) => (
        <div
          key={series.key}
          className={`legendItem ${props.highlightedSeries === series.key ? "active" : ""}`}
          onMouseEnter={() => props.onHighlight(series.key)}
          onMouseLeave={() => props.onHighlight(null)}
        >
          <span className="legendSwatch" style={{ background: series.color }} />
          <span className="legendText">{series.label}</span>
        </div>
      ))}
    </div>
  );
}
