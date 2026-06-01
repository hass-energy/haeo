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
    return false;
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
  return attrs["platform"] === "haeo";
}

function deviceConfigEntryIds(hass: HassLike, deviceId: string): string[] {
  return hass.devices?.[deviceId]?.config_entries ?? [];
}

export function isHubConfigured(config: { hub_entry_id?: string }): boolean {
  const configured = config.hub_entry_id?.trim();
  return configured !== undefined && configured !== "";
}

export function hubConfigEntryExists(hass: HassLike, hubEntryId: string): boolean {
  if (hass.devices === undefined) {
    return false;
  }
  for (const device of Object.values(hass.devices)) {
    if (device?.config_entries.includes(hubEntryId) === true) {
      return true;
    }
  }
  return false;
}

export type ConfiguredHubStatus = "ok" | "not_configured" | "not_found";

export interface ConfiguredHubResolution {
  status: ConfiguredHubStatus;
  hubEntryId: string | null;
}

export function resolveConfiguredHub(
  config: { hub_entry_id?: string },
  hass: HassLike | null
): ConfiguredHubResolution {
  if (!isHubConfigured(config)) {
    return { status: "not_configured", hubEntryId: null };
  }
  const hubEntryId = config.hub_entry_id!.trim();
  if (hass === null || !hubConfigEntryExists(hass, hubEntryId)) {
    return { status: "not_found", hubEntryId };
  }
  return { status: "ok", hubEntryId };
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
  if (deviceId === undefined || hass.devices === undefined) {
    return false;
  }
  return deviceConfigEntryIds(hass, deviceId).includes(hubEntryId);
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

/** Used by card editor stub config only — runtime cards require an explicit hub. */
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
  if (hass.entities === undefined || hass.devices === undefined) {
    return [];
  }
  const entityIds: string[] = [];
  for (const [entityId, state] of Object.entries(hass.states)) {
    if (state === undefined) {
      continue;
    }
    if (!entityBelongsToHub(hass, entityId, hubEntryId)) {
      continue;
    }
    entityIds.push(entityId);
  }
  return entityIds.sort((a, b) => a.localeCompare(b));
}

export function discoverForecastEntityIdsForHub(hass: HassLike, hubEntryId: string): string[] {
  return discoverForecastEntityIds(hass, hubEntryId);
}

export function discoverForecastEntityIds(hass: HassLike, hubEntryId: string): string[] {
  return forecastEntityIdsFromStates(hass).filter((entityId) => entityBelongsToHub(hass, entityId, hubEntryId));
}

export function isHubRegistryReady(hass: HassLike | null): boolean {
  return hass?.entities !== undefined && hass.devices !== undefined;
}

export type ForecastEmptyReason = "loading" | "not_configured" | "hub_not_found" | "no_data";

export function forecastEmptyReason(
  hass: HassLike | null,
  config: { hub_entry_id?: string },
  hasData: boolean
): ForecastEmptyReason | null {
  if (hasData) {
    return null;
  }
  if (!isHubConfigured(config)) {
    return "not_configured";
  }
  if (!isHubRegistryReady(hass)) {
    return "loading";
  }
  const hub = resolveConfiguredHub(config, hass);
  if (hub.status === "not_found") {
    return "hub_not_found";
  }
  return "no_data";
}
