import type { HassLike } from "./series";
import type { TopologyData } from "./topology/types";
import type { TopologyCardConfig } from "./types";

interface EntityRegistryEntryLike {
  config_entry_id?: string | null;
}

interface TopologyHassLike extends HassLike {
  entities?: Record<string, EntityRegistryEntryLike | undefined>;
}

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

function topologyEntitiesForHub(hass: TopologyHassLike, hubEntryId: string): string[] {
  const discovered = discoverTopologyEntities(hass);
  if (hass.entities === undefined) {
    return discovered;
  }
  return discovered.filter((entityId) => hass.entities?.[entityId]?.config_entry_id === hubEntryId);
}

export function resolveTopologyEntity(config: TopologyCardConfig, hass: HassLike | null): string | null {
  const configured = config.entity?.trim();
  if (configured !== undefined && configured !== "" && hass?.states[configured] !== undefined) {
    const topology = hass.states[configured].attributes["topology"];
    if (isTopologyData(topology)) {
      return configured;
    }
  }

  const hubEntryId = config.hub_entry_id?.trim();
  if (hubEntryId === undefined || hubEntryId === "" || hass === null) {
    return null;
  }

  const topologyHass = hass as TopologyHassLike;
  const hubEntities = topologyEntitiesForHub(topologyHass, hubEntryId);

  if (topologyHass.entities !== undefined) {
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
