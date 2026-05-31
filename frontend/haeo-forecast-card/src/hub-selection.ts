import type { HassLike } from "./series";

interface EntityRegistryEntryLike {
  config_entry_id?: string | null;
}

interface HassWithEntities extends HassLike {
  entities?: Record<string, EntityRegistryEntryLike | undefined>;
}

export function discoverHaeoHubEntryId(hass: HassLike): string | null {
  const hassWithEntities = hass as HassWithEntities;
  if (hassWithEntities.entities === undefined) {
    return null;
  }
  for (const [entityId, entry] of Object.entries(hassWithEntities.entities)) {
    if (entry?.config_entry_id === undefined || entry.config_entry_id === null) {
      continue;
    }
    const state = hass.states[entityId];
    if (state?.attributes["platform"] === "haeo" || entityId.includes("haeo")) {
      return entry.config_entry_id;
    }
  }
  return null;
}

export function entityIdsForHub(hass: HassLike, hubEntryId: string): string[] {
  const hassWithEntities = hass as HassWithEntities;
  const entityIds: string[] = [];
  for (const [entityId, state] of Object.entries(hass.states)) {
    if (state === undefined) {
      continue;
    }
    if (hassWithEntities.entities !== undefined) {
      const entry = hassWithEntities.entities[entityId];
      if (entry?.config_entry_id !== hubEntryId) {
        continue;
      }
    }
    entityIds.push(entityId);
  }
  return entityIds.sort((a, b) => a.localeCompare(b));
}

export function discoverForecastEntityIdsForHub(hass: HassLike, hubEntryId: string): string[] {
  return entityIdsForHub(hass, hubEntryId).filter((entityId) => {
    const forecast = hass.states[entityId]?.attributes["forecast"];
    return Array.isArray(forecast) && forecast.length > 0;
  });
}
