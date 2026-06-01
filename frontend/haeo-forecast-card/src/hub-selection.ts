import type { HassLike } from "./series";

function isTopologyAttribute(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    Array.isArray(candidate["nodes"]) && Array.isArray(candidate["edges"]) && typeof candidate["groups"] === "object"
  );
}

function isHaeoEntity(hass: HassLike, entityId: string, entry: NonNullable<HassLike["entities"]>[string]): boolean {
  if (entry?.platform === "haeo") {
    return true;
  }
  const state = hass.states[entityId];
  if (state === undefined) {
    return entityId.includes("haeo");
  }
  const attrs = state.attributes;
  if (attrs["element_type"] !== undefined) {
    return true;
  }
  if (attrs["output_name"] === "network_optimization_status") {
    return true;
  }
  if (Array.isArray(attrs["forecast"])) {
    return true;
  }
  if (isTopologyAttribute(attrs["topology"])) {
    return true;
  }
  if (attrs["platform"] === "haeo") {
    return true;
  }
  return entityId.includes("haeo");
}

function deviceConfigEntryIds(hass: HassLike, deviceId: string): string[] {
  return hass.devices?.[deviceId]?.config_entries ?? [];
}

function hasForecastAttribute(hass: HassLike, entityId: string): boolean {
  const forecast = hass.states[entityId]?.attributes["forecast"];
  return Array.isArray(forecast) && forecast.length > 0;
}

function forecastEntityIdsFromStates(hass: HassLike): string[] {
  return Object.keys(hass.states)
    .filter((entityId) => hasForecastAttribute(hass, entityId))
    .sort((a, b) => a.localeCompare(b));
}

export function entityBelongsToHub(hass: HassLike, entityId: string, hubEntryId: string): boolean {
  const entry = hass.entities?.[entityId];
  const deviceId = entry?.device_id;
  if (deviceId !== undefined && hass.devices !== undefined) {
    const configEntries = deviceConfigEntryIds(hass, deviceId);
    if (configEntries.length > 0) {
      return configEntries.includes(hubEntryId);
    }
  }

  if (!isHaeoEntity(hass, entityId, entry)) {
    return false;
  }

  const discoveredHub = discoverHaeoHubEntryId(hass);
  return discoveredHub === null || discoveredHub === hubEntryId;
}

export function discoverHaeoHubEntryId(hass: HassLike): string | null {
  if (hass.entities === undefined) {
    return null;
  }
  const hubIds = new Set<string>();
  for (const [entityId, entry] of Object.entries(hass.entities)) {
    if (!isHaeoEntity(hass, entityId, entry)) {
      continue;
    }
    const deviceId = entry?.device_id;
    if (deviceId === undefined) {
      continue;
    }
    for (const hubId of deviceConfigEntryIds(hass, deviceId)) {
      hubIds.add(hubId);
    }
  }
  if (hubIds.size === 0) {
    return null;
  }
  return [...hubIds].sort((a, b) => a.localeCompare(b))[0]!;
}

export function resolveHubEntryId(config: { hub_entry_id?: string }, hass: HassLike | null): string | null {
  const configured = config.hub_entry_id?.trim();
  if (configured !== undefined && configured !== "") {
    return configured;
  }
  if (hass === null) {
    return null;
  }
  return discoverHaeoHubEntryId(hass);
}

export function entityIdsForHub(hass: HassLike, hubEntryId: string): string[] {
  const entityIds: string[] = [];
  for (const [entityId, state] of Object.entries(hass.states)) {
    if (state === undefined) {
      continue;
    }
    if (hass.entities !== undefined && !entityBelongsToHub(hass, entityId, hubEntryId)) {
      continue;
    }
    entityIds.push(entityId);
  }
  return entityIds.sort((a, b) => a.localeCompare(b));
}

export function discoverForecastEntityIdsForHub(hass: HassLike, hubEntryId: string): string[] {
  return discoverForecastEntityIds(hass, hubEntryId);
}

export function discoverForecastEntityIds(hass: HassLike, hubEntryId: string | null): string[] {
  const allForecast = forecastEntityIdsFromStates(hass);
  if (hubEntryId === null) {
    return allForecast;
  }
  return allForecast.filter((entityId) => entityBelongsToHub(hass, entityId, hubEntryId));
}
