export type MotionMode = "off" | "reduced" | "smooth";

export interface ForecastCardConfig {
  type: "custom:haeo-forecast-card";
  title?: string;
  entities?: string[];
  height?: number;
  animation_mode?: MotionMode;
  animation_speed?: number;
}

export interface ForecastPoint {
  time: number;
  value: number;
}

export type LaneType = "power" | "price" | "soc" | "shadow" | "other";
export type DrawType = "step" | "line";

export interface ForecastSeries {
  key: string;
  entityId: string;
  label: string;
  outputType: string;
  lane: LaneType;
  drawType: DrawType;
  unit: string;
  color: string;
  times: Float64Array;
  values: Float64Array;
  points: ForecastPoint[];
}

export interface LaneBounds {
  min: number;
  max: number;
}

export interface ChartMargins {
  top: number;
  right: number;
  bottom: number;
  left: number;
}
