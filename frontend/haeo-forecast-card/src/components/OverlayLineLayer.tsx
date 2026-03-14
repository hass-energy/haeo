import type { JSX } from "preact";

interface OverlayLineLayerProps {
  paths: Array<{ key: string; color: string; d: string }>;
  highlightedSeries: string | null;
  focusedSeriesKeys: Set<string>;
  cssClass: string;
}

export function OverlayLineLayer(props: OverlayLineLayerProps): JSX.Element {
  return (
    <>
      {props.paths.map((series) => {
        const hasGroupFocus = props.focusedSeriesKeys.size > 0;
        const groupFocused = props.focusedSeriesKeys.has(series.key);
        let opacity = hasGroupFocus ? (groupFocused ? 0.92 : 0.2) : 0.92;
        if (props.highlightedSeries && props.highlightedSeries !== series.key) {
          opacity = 0.22;
        }
        return (
          <path
            key={series.key}
            className={`lineSeries ${props.cssClass}`}
            stroke={series.color}
            opacity={opacity}
            d={series.d}
          />
        );
      })}
    </>
  );
}
