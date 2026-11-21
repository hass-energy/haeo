import type { EntityStateLike, InputSelectorConfig, SelectorHass } from "./types";

/** An entity the selector can offer, with what the user recognises it by. */
export interface EntityOption {
  entityId: string;
  name: string;
  /** The entity's current state, or "" when it has none. */
  state: string;
  /** The unit the entity states, or "". */
  unit: string;
}

function friendlyName(entityId: string, state: EntityStateLike | undefined): string {
  const name = state?.attributes["friendly_name"];
  return typeof name === "string" && name !== "" ? name : entityId;
}

function currentState(state: EntityStateLike | undefined): string {
  return state === undefined || state.state === "unknown" || state.state === "unavailable" ? "" : state.state;
}

function stateUnit(state: EntityStateLike | undefined): string {
  const unit = state?.attributes["unit_of_measurement"];
  return typeof unit === "string" ? unit : "";
}

/** Describe an entity for display, whether or not it is currently offered. */
export function describeEntity(hass: SelectorHass | null, entityId: string): EntityOption {
  const state = hass?.states[entityId];
  return { entityId, name: friendlyName(entityId, state), state: currentState(state), unit: stateUnit(state) };
}

/** The IDs of every entity the field offers, sorted by name so the order never shifts while picking. */
export function offeredEntityIds(hass: SelectorHass | null, config: InputSelectorConfig): string[] {
  const ids =
    config.entities ??
    Object.keys(hass?.states ?? {}).filter((entityId) => config.domains.includes(entityId.split(".")[0] ?? ""));
  return ids
    .map((entityId) => describeEntity(hass, entityId))
    .sort((a, b) => a.name.localeCompare(b.name) || a.entityId.localeCompare(b.entityId))
    .map((option) => option.entityId);
}

/** Keep the options whose name or entity ID contains every word of the query. */
export function filterOptions(options: EntityOption[], query: string): EntityOption[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return options;
  }
  return options.filter((option) => {
    const haystack = `${option.name} ${option.entityId}`.toLowerCase();
    return words.every((word) => haystack.includes(word));
  });
}

/** A number typed into a field, and whether the field accepts it. */
export interface TypedNumber {
  value: number;
  allowed: boolean;
}

/** Read a typed number for a field taking numbers, or return null when the text is not one. */
export function readNumber(text: string, config: InputSelectorConfig): TypedNumber | null {
  const trimmed = text.trim();
  if (!config.kinds.includes("constant") || config.value_type !== "number" || trimmed === "") {
    return null;
  }
  const value = Number(trimmed);
  if (!Number.isFinite(value)) {
    return null;
  }
  const allowed =
    (config.min === undefined || value >= config.min) && (config.max === undefined || value <= config.max);
  return { value, allowed };
}
