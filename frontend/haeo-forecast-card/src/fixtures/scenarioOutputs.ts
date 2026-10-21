import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { HassEntityState, HassLike } from "../series";

export const DEFAULT_TEST_HUB = "hub-alpha";

function scenarioPath(name: string): string {
  return resolve(import.meta.dirname, "../../../../tests/scenarios", name, "outputs.json");
}

export function withSingleHubRegistry(hass: HassLike, hubEntryId = DEFAULT_TEST_HUB, deviceId = "dev-haeo"): HassLike {
  const entities: NonNullable<HassLike["entities"]> = {};
  for (const entityId of Object.keys(hass.states)) {
    entities[entityId] = { platform: "haeo", device_id: deviceId };
  }
  return {
    ...hass,
    entities,
    devices: {
      [deviceId]: { config_entries: [hubEntryId] },
    },
  };
}

export function loadScenarioHassState(name: string, hubEntryId = DEFAULT_TEST_HUB): HassLike {
  const file = readFileSync(scenarioPath(name), "utf-8");
  const parsed = JSON.parse(file) as Record<string, HassEntityState>;
  return withSingleHubRegistry({ states: parsed }, hubEntryId);
}
