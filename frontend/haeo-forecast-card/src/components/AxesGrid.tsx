import type { JSX } from "preact";

interface AxesGridProps {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
  xMin: number;
  xMax: number;
  xScale: (time: number) => number;
  yScalePower: (value: number) => number;
  powerMin: number;
  powerMax: number;
  priceMin: number;
  priceMax: number;
  socMin: number;
  socMax: number;
}

function ticks(min: number, max: number, count: number): number[] {
  if (count < 2 || max <= min) {
    return [min];
  }
  return Array.from({ length: count }, (_, idx) => min + (idx / (count - 1)) * (max - min));
}

export function AxesGrid(props: AxesGridProps): JSX.Element {
  const xMajor = ticks(props.xMin, props.xMax, 7);
  const xMinor = ticks(props.xMin, props.xMax, 13);
  const yMajor = ticks(props.powerMin, props.powerMax, 6);
  const yMinor = ticks(props.powerMin, props.powerMax, 11);

  return (
    <>
      {xMinor.map((time, idx) => (
        <line
          key={`x-minor-${idx}`}
          className="gridMinor"
          x1={props.xScale(time)}
          y1={props.top}
          x2={props.xScale(time)}
          y2={props.bottom}
        />
      ))}
      {yMinor.map((value, idx) => (
        <line
          key={`y-minor-${idx}`}
          className="gridMinor"
          x1={props.left}
          y1={props.yScalePower(value)}
          x2={props.width - props.right}
          y2={props.yScalePower(value)}
        />
      ))}

      {xMajor.map((time, idx) => (
        <g key={`x-major-${idx}`}>
          <line
            className="gridMajor"
            x1={props.xScale(time)}
            y1={props.top}
            x2={props.xScale(time)}
            y2={props.bottom}
          />
          <text className="axisTickLabel" x={props.xScale(time)} y={props.bottom + 18} textAnchor="middle">
            {new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </text>
        </g>
      ))}

      {yMajor.map((value, idx) => (
        <g key={`y-major-${idx}`}>
          <line
            className="gridMajor"
            x1={props.left}
            y1={props.yScalePower(value)}
            x2={props.width - props.right}
            y2={props.yScalePower(value)}
          />
          <text className="axisTickLabel" x={props.left - 8} y={props.yScalePower(value)} textAnchor="end">
            {value.toFixed(1)}
          </text>
        </g>
      ))}

      <line className="axisBase" x1={props.left} y1={props.bottom} x2={props.width - props.right} y2={props.bottom} />
      <line className="axisBase" x1={props.left} y1={props.top} x2={props.left} y2={props.bottom} />

      <text className="axisLabelStrong" x={props.left} y={props.top - 6} textAnchor="start">
        Power (kW)
      </text>
      <text className="axisLabelStrong" x={props.width - props.right} y={props.top - 6} textAnchor="end">
        Price ({props.priceMin.toFixed(2)} to {props.priceMax.toFixed(2)})
      </text>
      <text className="axisLabelStrong" x={props.width - props.right} y={props.bottom + 26} textAnchor="end">
        SOC ({props.socMin.toFixed(0)} to {props.socMax.toFixed(0)})
      </text>
    </>
  );
}
