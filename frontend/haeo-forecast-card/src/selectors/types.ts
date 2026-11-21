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
  /** Whether the field takes several entities. */
  multiple: boolean;
  /** Entities the field offers, already filtered to compatible units. */
  entities: string[];
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
