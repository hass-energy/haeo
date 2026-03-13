import type { JSX } from "preact";

import { linePath, stepPath } from "../geometry";
import type { ForecastSeries } from "../types";

interface OverlayLineLayerProps {
  seriesList: ForecastSeries[];
  highlightedSeries: string | null;
  xScale: (time: number) => number;
  yScale: (value: number) => number;
  cssClass: string;
  forceStep?: boolean;
}

export function OverlayLineLayer(props: OverlayLineLayerProps): JSX.Element {
  return (
    <>
      {props.seriesList.map((series) => {
        const opacity = props.highlightedSeries && props.highlightedSeries !== series.key ? 0.28 : 0.92;
        const d = props.forceStep
          ? stepPath(
              series.points,
              (time) => props.xScale(time),
              (value) => props.yScale(value)
            )
          : linePath(
              series.points,
              (time) => props.xScale(time),
              (value) => props.yScale(value)
            );
        return (
          <path
            key={series.key}
            className={`lineSeries ${props.cssClass}`}
            stroke={series.color}
            opacity={opacity}
            d={d}
          />
        );
      })}
    </>
  );
}
