import type { JSX } from "preact";

import { stepAreaPath } from "../geometry";
import type { ForecastSeries } from "../types";

interface PowerStackLayerProps {
  seriesList: ForecastSeries[];
  highlightedSeries: string | null;
  xScale: (time: number) => number;
  yScalePower: (value: number) => number;
}

export function PowerStackLayer(props: PowerStackLayerProps): JSX.Element {
  const firstSeries = props.seriesList[0];
  if (!firstSeries) {
    return <></>;
  }
  const horizonCount = firstSeries.times.length;
  const positive = new Float64Array(horizonCount);
  const negative = new Float64Array(horizonCount);

  return (
    <>
      {props.seriesList.map((series) => {
        const lower = new Float64Array(horizonCount);
        const upper = new Float64Array(horizonCount);

        for (let idx = 0; idx < horizonCount; idx += 1) {
          const value = series.values[idx] ?? 0;
          if (value >= 0) {
            lower[idx] = positive[idx] ?? 0;
            upper[idx] = (positive[idx] ?? 0) + value;
            positive[idx] = (positive[idx] ?? 0) + value;
          } else {
            lower[idx] = negative[idx] ?? 0;
            upper[idx] = (negative[idx] ?? 0) + value;
            negative[idx] = (negative[idx] ?? 0) + value;
          }
        }

        const opacity = props.highlightedSeries && props.highlightedSeries !== series.key ? 0.18 : 0.58;
        return (
          <path
            key={series.key}
            className="areaSeries"
            fill={series.color}
            stroke={series.color}
            opacity={opacity}
            d={stepAreaPath(
              series.times,
              lower,
              upper,
              (time) => props.xScale(time),
              (value) => props.yScalePower(value)
            )}
          />
        );
      })}
    </>
  );
}
