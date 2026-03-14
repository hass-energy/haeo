export type MotionMode = "off" | "reduced" | "smooth";
export type PowerDisplayMode = "opposed" | "overlay";

export interface ForecastCardConfig {
  type: "custom:haeo-forecast-card";
  title?: string;
  hub_entry_id?: string;
  entities?: string[];
  height?: number;
  animation_mode?: MotionMode;
  animation_speed?: number;
  power_display_mode?: PowerDisplayMode;
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
  elementName: string;
  elementType: string;
  outputName: string;
  outputType: string;
  direction: string | null;
  configMode: string | null;
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
