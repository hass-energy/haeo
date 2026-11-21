/** A configured input, as HAEO stores it and as the selector reports it. */
export type InputValue =
  | { type: "entity"; value: string[]; on_states?: string[]; off_states?: string[] }
  | { type: "constant"; value: number | boolean }
  | { type: "none" };

export type InputKind = InputValue["type"];

/** The `haeo_input` selector config the integration sends. */
export interface InputSelectorConfig {
  /** Kinds of value the field accepts. */
  kinds: InputKind[];
  /** Whether the constant is a number or an on/off value. */
  value_type: "number" | "boolean";
  /** Domains the field's entities come from. */
  domains: string[];
  /** The entities the field offers when it narrows its domains, such as by unit. */
  entities?: string[];
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
}

export interface EntityStateLike {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}

export interface SelectorHass {
  states: Record<string, EntityStateLike | undefined>;
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
