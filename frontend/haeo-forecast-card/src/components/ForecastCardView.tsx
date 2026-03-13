import type { JSX } from "preact";

import { ChartSvg } from "./ChartSvg";
import { Legend } from "./Legend";
import { Tooltip } from "./Tooltip";
import type { ForecastCardStore } from "../store";

interface ForecastCardViewProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

export function ForecastCardView(props: ForecastCardViewProps): JSX.Element {
  const title = props.store.config.title ?? "HAEO forecast";
  if (!props.store.hasData) {
    return (
      <ha-card>
        <div className="title">{title}</div>
        <div className="empty">
          No forecast data found. Add forecast entities in card config or ensure HAEO output sensors are available.
        </div>
      </ha-card>
    );
  }

  return (
    <ha-card>
      <div className="title">{title}</div>
      <ChartSvg store={props.store} onPointerMove={props.onPointerMove} onPointerLeave={props.onPointerLeave} />
      <Legend
        series={props.store.visibleSeries}
        highlightedSeries={props.store.highlightedSeries}
        onHighlight={(key) => props.store.setHighlightedSeries(key)}
      />
      <Tooltip
        hoverTimeMs={props.store.hoverTimeMs}
        rows={props.store.tooltipRows}
        totals={props.store.tooltipTotals}
      />
    </ha-card>
  );
}
