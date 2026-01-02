/**
 * Flow context parameters extracted from URL query string.
 */
export interface FlowParams {
  /** Config flow ID to configure */
  flowId: string;
  /** Parent config entry ID (for subentry flows) */
  entryId?: string;
  /** Element type being configured */
  subentryType?: string;
  /** Existing subentry ID (for reconfigure) */
  subentryId?: string;
  /** Flow source: user or reconfigure */
  source?: "user" | "reconfigure";
  /** Flow mode: hub, element, or options */
  mode?: "hub" | "element" | "options";
}

/**
 * Element types supported by HAEO.
 */
export type ElementType =
  | "battery"
  | "battery_section"
  | "connection"
  | "grid"
  | "inverter"
  | "load"
  | "node"
  | "solar";

/**
 * Base element configuration shared by all element types.
 */
export interface BaseElementConfig {
  element_type: ElementType;
  name: string;
}

/**
 * Entity metadata from Home Assistant entity registry.
 */
export interface EntityMetadata {
  entity_id: string;
  friendly_name: string;
  device_class?: string;
  unit_of_measurement?: string;
  state?: string;
}

/**
 * Config flow result from Home Assistant API.
 */
export interface FlowResult {
  type: "form" | "create_entry" | "abort" | "external" | "external_step_done";
  flow_id: string;
  handler: string;
  step_id?: string;
  data_schema?: unknown[];
  errors?: Record<string, string>;
  description_placeholders?: Record<string, string>;
  last_step?: boolean;
  result?: {
    entry_id: string;
    title: string;
  };
  reason?: string;
}

/**
 * Horizon tier configuration.
 */
export interface TierConfig {
  tier_1_count: number;
  tier_1_duration: number;
  tier_2_count: number;
  tier_2_duration: number;
  tier_3_count: number;
  tier_3_duration: number;
  tier_4_count: number;
  tier_4_duration: number;
}

/**
 * Hub configuration data.
 */
export interface HubConfig extends TierConfig {
  name: string;
  horizon_preset: string;
  advanced_mode: boolean;
  update_interval_minutes: number;
  debounce_seconds: number;
}

/**
 * Connection configuration for power flow between elements.
 */
export interface ConnectionConfig extends BaseElementConfig {
  element_type: "connection";
  source: string;
  target: string;
  max_power_source_to_target?: string | number;
  max_power_target_to_source?: string | number;
  efficiency?: number;
}

/**
 * Battery configuration.
 */
export interface BatteryConfig extends BaseElementConfig {
  element_type: "battery";
  connection: string;
  capacity: string | number;
  initial_charge_percentage: string | number;
  min_charge_percentage?: number;
  max_charge_percentage?: number;
  efficiency?: number;
  max_charge_power?: string | number;
  max_discharge_power?: string | number;
  early_charge_incentive?: number;
  discharge_cost?: number;
}

/**
 * Grid configuration.
 */
export interface GridConfig extends BaseElementConfig {
  element_type: "grid";
  connection: string;
  import_price?: string[] | number;
  export_price?: string[] | number;
  import_limit?: string | number;
  export_limit?: string | number;
}

/**
 * Solar configuration.
 */
export interface SolarConfig extends BaseElementConfig {
  element_type: "solar";
  connection: string;
  forecast: string[];
  curtailment?: boolean;
}

/**
 * Load configuration.
 */
export interface LoadConfig extends BaseElementConfig {
  element_type: "load";
  connection: string;
  forecast: string[];
}

/**
 * Node (network junction) configuration.
 */
export interface NodeConfig extends BaseElementConfig {
  element_type: "node";
  is_source?: boolean;
  is_sink?: boolean;
}

/**
 * Inverter configuration.
 */
export interface InverterConfig extends BaseElementConfig {
  element_type: "inverter";
  ac_connection: string;
  max_dc_to_ac_power?: string | number;
  max_ac_to_dc_power?: string | number;
  efficiency?: number;
}

/**
 * Union of all element configuration types.
 */
export type ElementConfig =
  | BatteryConfig
  | ConnectionConfig
  | GridConfig
  | InverterConfig
  | LoadConfig
  | NodeConfig
  | SolarConfig;
