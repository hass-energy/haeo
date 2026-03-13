import type { JSX } from "preact";

import type { ForecastCardStore } from "../store";
import { LaneGroup } from "./LaneGroup";

interface ChartSvgProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

export function ChartSvg(props: ChartSvgProps): JSX.Element {
  const { store } = props;
  const lanes = [...store.laneSeries.entries()];
  const ticks = 6;
  const tickMarks = Array.from({ length: ticks }, (_, idx) => {
    const ratio = idx / (ticks - 1);
    const x = store.margins.left + ratio * (store.width - store.margins.left - store.margins.right);
    const time = store.xDomain.min + ratio * (store.xDomain.max - store.xDomain.min);
    return {
      x,
      label: new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
  });

  return (
    <svg
      viewBox={`0 0 ${store.width} ${store.height}`}
      height={store.height}
      onPointerMove={(event) => props.onPointerMove(event as unknown as PointerEvent)}
      onPointerLeave={props.onPointerLeave}
    >
      {tickMarks.map((tick) => (
        <line
          key={`grid-${tick.x}`}
          className="grid"
          x1={tick.x}
          y1={store.margins.top}
          x2={tick.x}
          y2={store.height - store.margins.bottom}
        />
      ))}

      {lanes.map(([lane, seriesList], laneIndex) => {
        const rect = store.laneRects.get(lane);
        if (!rect) {
          return null;
        }
        return (
          <g key={`lane-${lane}`}>
            {laneIndex > 0 && (
              <line
                className="laneDivider"
                x1={store.margins.left}
                y1={rect.top}
                x2={store.width - store.margins.right}
                y2={rect.top}
              />
            )}
            <LaneGroup
              lane={lane}
              seriesList={seriesList}
              yScale={(group, value) => store.yScale(group, value)}
              xScale={(time) => store.xScale(time)}
              width={store.width}
              margins={store.margins}
              top={rect.top}
              bottom={rect.bottom}
              highlightedSeries={store.highlightedSeries}
            />
          </g>
        );
      })}

      {tickMarks.map((tick) => (
        <text
          key={`tick-${tick.x}`}
          className="axisLabel"
          x={tick.x}
          y={store.height - store.margins.bottom + 18}
          textAnchor="middle"
        >
          {tick.label}
        </text>
      ))}

      {store.hoverX !== null && (
        <line
          className="hoverLine"
          x1={store.hoverX}
          y1={store.margins.top}
          x2={store.hoverX}
          y2={store.height - store.margins.bottom}
        />
      )}
    </svg>
  );
}
