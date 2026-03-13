import type { JSX } from "preact";

import { linePath, stepAreaPath } from "../geometry";
import type { ForecastSeries } from "../types";

interface LaneGroupProps {
  lane: string;
  seriesList: ForecastSeries[];
  yScale: (lane: string, value: number) => number;
  xScale: (time: number) => number;
  width: number;
  margins: { left: number; right: number };
  top: number;
  bottom: number;
  highlightedSeries: string | null;
}

export function LaneGroup(props: LaneGroupProps): JSX.Element {
  const { lane, seriesList, top, bottom } = props;
  const stepSeries = seriesList.filter((series) => series.drawType === "step");
  const lineSeries = seriesList.filter((series) => series.drawType === "line");

  return (
    <>
      <text className="axisLabel" x={8} y={(top + bottom) * 0.5}>
        {lane}
      </text>

      {stepSeries.length > 0 &&
        (() => {
          const firstStepSeries = stepSeries[0];
          if (!firstStepSeries) {
            return null;
          }
          const horizonCount = firstStepSeries.times.length;
          const positive = new Float64Array(horizonCount);
          const negative = new Float64Array(horizonCount);

          return stepSeries.map((series) => {
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

            const opacity = props.highlightedSeries && props.highlightedSeries !== series.key ? 0.22 : 0.66;
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
                  (value) => props.yScale(lane, value)
                )}
              />
            );
          });
        })()}

      {lineSeries.map((series) => {
        const opacity = props.highlightedSeries && props.highlightedSeries !== series.key ? 0.25 : 0.78;
        return (
          <path
            key={series.key}
            className="lineSeries"
            stroke={series.color}
            opacity={opacity}
            d={linePath(
              series.points,
              (time) => props.xScale(time),
              (value) => props.yScale(lane, value)
            )}
          />
        );
      })}
    </>
  );
}
