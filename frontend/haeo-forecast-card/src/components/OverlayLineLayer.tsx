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
        const isHighlighted = props.highlightedSeries === series.key;
        const isActive = isHighlighted || groupFocused;
        let opacity = hasGroupFocus ? (groupFocused ? 1 : 0.14) : 0.9;
        if (props.highlightedSeries !== null) {
          opacity = isHighlighted ? 1 : 0.14;
        }
        return (
          <path
            key={series.key}
            className={`lineSeries ${props.cssClass} ${isActive ? "active" : ""}`}
            stroke={series.color}
            opacity={opacity}
            d={series.d}
          />
        );
      })}
    </>
  );
}
