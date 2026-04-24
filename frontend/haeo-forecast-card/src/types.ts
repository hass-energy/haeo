export type MotionMode = "off" | "reduced" | "smooth";
export type PowerDisplayMode = "opposed" | "overlay";

export interface ForecastCardConfig {
  type: "custom:haeo-forecast-card";
  title?: string;
  hub_entry_id?: string;
  entities?: string[];
  animation_mode?: MotionMode;
  animation_speed?: number;
  power_display_mode?: PowerDisplayMode;
}

export type ElementType =
  | "battery"
  | "battery_section"
  | "connection"
  | "grid"
  | "inverter"
  | "load"
  | "node"
  | "solar"
  | "policy";
export type CardOutputType = "power" | "price" | "state_of_charge";
export type LaneType = "power" | "price" | "soc" | "shadow" | "other";
export type DrawType = "step" | "line";
export type SeriesSourceRole = "output" | "forecast" | "limit";
export type ConfigMode = "editable" | "driven";

export interface ForecastSeries {
  key: string;
  entityId: string;
  label: string;
  elementName: string;
  elementType: ElementType;
  outputName: string;
  outputType: CardOutputType;
  direction: "+" | "-" | null;
  sourceRole: SeriesSourceRole;
  configMode: ConfigMode | null;
  fixed: boolean;
  priority: number | null;
  lane: LaneType;
  drawType: DrawType;
  unit: string;
  color: string;
  times: Float64Array;
  values: Float64Array;
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
