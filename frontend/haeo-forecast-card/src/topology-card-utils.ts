import type { HassLike } from "./series";
import type { TopologyData } from "./topology/types";
import type { TopologyCardConfig } from "./types";
import { entityBelongsToHub, resolveConfiguredHub } from "./hub-selection";

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

function optimizationStatusEntity(hass: HassLike, entityIds: string[]): string | null {
  if (entityIds.length === 1) {
    return entityIds[0]!;
  }
  const optimizationStatus = entityIds.find(
    (entityId) => hass.states[entityId]?.attributes["output_name"] === "network_optimization_status"
  );
  return optimizationStatus ?? null;
}

export type TopologyResolution =
  | { status: "ok"; entityId: string; topology: TopologyData }
  | { status: "not_configured" }
  | { status: "hub_not_found" }
  | { status: "no_entity" }
  | { status: "waiting"; entityId: string };

export function resolveTopology(config: TopologyCardConfig, hass: HassLike | null): TopologyResolution {
  const hub = resolveConfiguredHub(config, hass);
  if (hub.status === "not_configured") {
    return { status: "not_configured" };
  }
  if (hub.status === "not_found" || hass === null || hub.hubEntryId === null) {
    return { status: "hub_not_found" };
  }

  const hubEntryId = hub.hubEntryId;
  const hubEntities = discoverTopologyEntities(hass).filter((entityId) =>
    entityBelongsToHub(hass, entityId, hubEntryId)
  );
  const entityId = optimizationStatusEntity(hass, hubEntities);
  if (entityId === null) {
    return { status: "no_entity" };
  }

  const topology = readTopology(hass, entityId);
  if (topology === null) {
    return { status: "waiting", entityId };
  }
  return { status: "ok", entityId, topology };
}

export function readTopology(hass: HassLike | null, entityId: string | null): TopologyData | null {
  if (hass === null || entityId === null) {
    return null;
  }
  const topology = hass.states[entityId]?.attributes["topology"];
  return isTopologyData(topology) ? topology : null;
}
