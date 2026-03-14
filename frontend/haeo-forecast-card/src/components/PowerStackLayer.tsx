import type { JSX } from "preact";

interface PowerStackLayerProps {
  shapes: Array<{ key: string; color: string; d: string; isPotential: boolean }>;
  highlightedSeries: string | null;
  hoveredSeriesKeys: Set<string>;
  focusedSeriesKeys: Set<string>;
}

export function PowerStackLayer(props: PowerStackLayerProps): JSX.Element {
  if (props.shapes.length === 0) {
    return <></>;
  }

  return (
    <>
      {props.shapes.map((shape) => {
        const isHovered = props.hoveredSeriesKeys.has(shape.key);
        const hasGroupFocus = props.focusedSeriesKeys.size > 0;
        const groupFocused = props.focusedSeriesKeys.has(shape.key);
        const isActiveStroke = isHovered || props.highlightedSeries === shape.key;
        let opacity = shape.isPotential ? 0.24 : 0.52;
        if (isHovered) {
          opacity = shape.isPotential ? 0.38 : 0.8;
        }
        if (hasGroupFocus) {
          opacity = groupFocused ? Math.max(opacity, shape.isPotential ? 0.32 : 0.68) : 0.12;
        }
        if (props.highlightedSeries) {
          opacity = props.highlightedSeries === shape.key ? (shape.isPotential ? 0.34 : 0.76) : 0.14;
        }
        const className = isActiveStroke ? "areaSeries active" : "areaSeries";
        return (
          <path
            key={shape.key}
            className={className}
            fill={shape.color}
            stroke={isActiveStroke ? shape.color : "none"}
            opacity={opacity}
            d={shape.d}
          />
        );
      })}
    </>
  );
}
