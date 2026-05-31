import type { HassLike } from "./series";
import type { TopologyData } from "./topology/types";
import type { TopologyCardConfig } from "./types";
import { entityBelongsToHub, resolveHubEntryId } from "./hub-selection";

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
    const topology = hass.states[configured].attributes["topology"];
    if (isTopologyData(topology)) {
      return configured;
    }
  }

  if (hass === null) {
    return null;
  }

  const hubEntryId = resolveHubEntryId(config, hass);
  if (hubEntryId === null) {
    const discovered = discoverTopologyEntities(hass);
    if (discovered.length === 1) {
      return discovered[0]!;
    }
    const optimizationStatus = discovered.find(
      (entityId) => hass.states[entityId]?.attributes["output_name"] === "network_optimization_status"
    );
    return optimizationStatus ?? null;
  }

  const hubEntities = discoverTopologyEntities(hass).filter((entityId) =>
    entityBelongsToHub(hass, entityId, hubEntryId)
  );

  if (hass.entities !== undefined) {
    if (hubEntities.length === 1) {
      return hubEntities[0]!;
    }
    const optimizationStatus = hubEntities.find(
      (entityId) => hass.states[entityId]?.attributes["output_name"] === "network_optimization_status"
    );
    return optimizationStatus ?? null;
  }

  const discovered = discoverTopologyEntities(hass);
  if (discovered.length === 1) {
    return discovered[0]!;
  }

  return null;
}

export function readTopology(hass: HassLike | null, entityId: string | null): TopologyData | null {
  if (hass === null || entityId === null) {
    return null;
  }
  const topology = hass.states[entityId]?.attributes["topology"];
  return isTopologyData(topology) ? topology : null;
}
