import type { JSX } from "preact";

interface PowerStackLayerProps {
  shapes: Array<{ key: string; color: string; d: string }>;
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
        let opacity = isHovered ? 0.8 : 0.52;
        if (hasGroupFocus) {
          opacity = groupFocused ? Math.max(opacity, 0.68) : 0.12;
        }
        if (props.highlightedSeries) {
          opacity = props.highlightedSeries === shape.key ? 0.76 : 0.14;
        }
        return (
          <g key={shape.key}>
            <path className="areaSeries" fill={shape.color} stroke={shape.color} opacity={opacity} d={shape.d} />
            {isHovered && <path className="areaSeriesGlow" fill="none" stroke={shape.color} d={shape.d} />}
          </g>
        );
      })}
    </>
  );
}
