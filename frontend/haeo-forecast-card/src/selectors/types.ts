/** A configured input, as HAEO stores it and as the selector reports it. */
export type InputValue =
  | { type: "entity"; value: string[]; on_states?: string[]; off_states?: string[] }
  | { type: "constant"; value: number | boolean }
  | { type: "none" };

export type InputKind = InputValue["type"];

/** How to preview what a field's entities combine to: the `haeo/input_preview` command's arguments. */
export interface InputPreviewConfig {
  entry_id: string;
  output_type: string;
  boundaries: boolean;
  non_negative: boolean;
}

/** The `haeo_input` selector config the integration sends. */
export interface InputSelectorConfig {
  /** Kinds of value the field accepts. */
  kinds: InputKind[];
  /** Whether the constant is a number or an on/off value. */
  value_type: "number" | "boolean";
  /** Domains the field's entities come from. */
  domains: string[];
  /**
   * The offered entities the field reads as forecasts, each with a preview of its values from now,
   * empty when there is none to show. The field reads the rest as their current value.
   */
  forecasts: Record<string, number[]>;
  /** The entities the field offers when it narrows its domains, such as by unit. */
  entities?: string[];
  /** Set for a field feeding a time series input. */
  preview?: InputPreviewConfig;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
}

export interface EntityStateLike {
  entity_id: string;
  state: string;
  last_updated?: string;
  attributes: Record<string, unknown>;
}

export interface SelectorHass {
  states: Record<string, EntityStateLike | undefined>;
  /** The user's language, which numbers are formatted in. */
  language?: string;
  /** Call a websocket command, as Home Assistant's frontend does. */
  callWS?: <T>(message: Record<string, unknown>) => Promise<T>;
  localize: (key: string, values?: Record<string, string>) => string;
}

/** Look up a translated string by key, filling `{name}` placeholders. */
export type Translate = (key: string, values?: Record<string, string>) => string;

/** An element already connected to a connection target. */
export interface ConnectedElement {
  name: string;
  element_type: string;
}

/** An element a connection field can connect to, and what is already connected to it. */
export interface ConnectionTarget {
  name: string;
  element_type: string;
  /** The kind of bus the target is, when HAEO knows it: an inverter's DC bus, or the AC switchboard. */
  bus: "ac" | "dc" | null;
  elements: ConnectedElement[];
}

/** The `haeo_connection` selector config the integration sends. */
export interface ConnectionSelectorConfig {
  /** The kind of element being configured. */
  element_type: string;
  targets: ConnectionTarget[];
}
