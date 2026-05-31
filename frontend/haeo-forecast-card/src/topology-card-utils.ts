import type { HassLike } from "./series";
import type { TopologyData } from "./topology/types";
import type { TopologyCardConfig } from "./types";

export function isTopologyData(value: unknown): value is TopologyData {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    Array.isArray(candidate["nodes"]) && Array.isArray(candidate["edges"]) && typeof candidate["groups"] === "object"
  );
}

export function discoverTopologyEntities(hass: HassLike): string[] {
  const entities: string[] = [];
  for (const [entityId, state] of Object.entries(hass.states)) {
    if (state === undefined) {
      continue;
    }
    if (isTopologyData(state.attributes["topology"])) {
      entities.push(entityId);
    }
  }
  return entities.sort((a, b) => a.localeCompare(b));
}

export function resolveTopologyEntity(config: TopologyCardConfig, hass: HassLike | null): string | null {
  const configured = config.entity?.trim();
  if (configured !== undefined && configured !== "" && hass?.states[configured] !== undefined) {
    return configured;
  }
  if (hass === null) {
    return null;
  }
  const discovered = discoverTopologyEntities(hass);
  return discovered[0] ?? null;
}

export function readTopology(hass: HassLike | null, entityId: string | null): TopologyData | null {
  if (hass === null || entityId === null) {
    return null;
  }
  const topology = hass.states[entityId]?.attributes["topology"];
  return isTopologyData(topology) ? topology : null;
}
