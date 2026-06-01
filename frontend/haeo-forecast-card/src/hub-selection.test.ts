import { describe, expect, it } from "vitest";

import {
  discoverForecastEntityIds,
  discoverForecastEntityIdsForHub,
  discoverHaeoHubEntryId,
  entityBelongsToHub,
  entityIdsForHub,
  resolveHubEntryId,
} from "./hub-selection";
import type { HassLike } from "./series";

describe("hub-selection", () => {
  it("discovers a HAEO hub from the entity registry", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: { platform: "haeo", forecast: [{ time: "2026-01-01T00:00:00Z", value: 1 }] },
        },
      },
      entities: {
        "sensor.haeo_grid_import_power": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(discoverHaeoHubEntryId(hass)).toBe("hub-alpha");
    expect(discoverForecastEntityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.haeo_grid_import_power"]);
  });

  it("filters forecast entities to the selected hub", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: { platform: "haeo", forecast: [{ time: "2026-01-01T00:00:00Z", value: 1 }] },
        },
        "sensor.other_hub_import_power": {
          entity_id: "sensor.other_hub_import_power",
          attributes: { platform: "haeo", forecast: [{ time: "2026-01-01T00:00:00Z", value: 2 }] },
        },
      },
      entities: {
        "sensor.haeo_grid_import_power": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.other_hub_import_power": { platform: "haeo", device_id: "dev-beta" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
        "dev-beta": { config_entries: ["hub-beta"] },
      },
    };

    expect(discoverForecastEntityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.haeo_grid_import_power"]);
  });

  it("discovers a HAEO hub from forecast attributes without platform on state", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_grid_import_power": {
          entity_id: "sensor.haeo_grid_import_power",
          attributes: { forecast: [{ time: "2026-01-01T00:00:00Z", value: 1 }] },
        },
      },
      entities: {
        "sensor.haeo_grid_import_power": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(discoverHaeoHubEntryId(hass)).toBe("hub-alpha");
  });

  it("returns the configured hub before discovery", () => {
    const hass: HassLike = { states: {}, entities: {} };
    expect(resolveHubEntryId({ hub_entry_id: "configured-hub" }, hass)).toBe("configured-hub");
  });

  it("falls back to the first discovered hub when config is empty", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_status": {
          entity_id: "sensor.haeo_status",
          attributes: { output_name: "network_optimization_status", topology: { nodes: [], edges: [], groups: {} } },
        },
      },
      entities: {
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-zulu" },
        "sensor.other_status": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-zulu": { config_entries: ["hub-zulu"] },
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(resolveHubEntryId({}, hass)).toBe("hub-alpha");
  });

  it("matches hub membership via device config_entries", () => {
    const hass: HassLike = {
      states: {
        "sensor.grid_import_power": {
          entity_id: "sensor.grid_import_power",
          attributes: {
            element_type: "grid",
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
            ],
          },
        },
      },
      entities: {
        "sensor.grid_import_power": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(entityBelongsToHub(hass, "sensor.grid_import_power", "hub-alpha")).toBe(true);
    expect(entityBelongsToHub(hass, "sensor.grid_import_power", "hub-beta")).toBe(false);
    expect(discoverForecastEntityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.grid_import_power"]);
  });

  it("finds forecast entities when registry entries are missing from hass.entities", () => {
    const hass: HassLike = {
      states: {
        "sensor.grid_import_power": {
          entity_id: "sensor.grid_import_power",
          attributes: {
            element_type: "grid",
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
            ],
          },
        },
      },
      entities: {
        "sensor.unrelated_entity": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(discoverForecastEntityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.grid_import_power"]);
  });

  it("treats registry entries without device_id as hub ownership unknown", () => {
    const hass: HassLike = {
      states: {
        "sensor.grid_import_power": {
          entity_id: "sensor.grid_import_power",
          attributes: {
            element_type: "grid",
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
            ],
          },
        },
        "sensor.grid_import_price": {
          entity_id: "sensor.grid_import_price",
          attributes: {
            element_type: "grid",
            field_type: "price",
            output_name: "import_price",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 0.1 },
              { time: "2026-03-14T00:05:00Z", value: 0.2 },
            ],
          },
        },
      },
      entities: {
        "sensor.grid_import_power": { platform: "haeo" },
        "sensor.grid_import_price": { platform: "haeo" },
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(entityBelongsToHub(hass, "sensor.grid_import_power", "hub-alpha")).toBe(true);
    expect(discoverForecastEntityIds(hass, "hub-alpha")).toEqual([
      "sensor.grid_import_power",
      "sensor.grid_import_price",
    ]);
  });

  it("does not fall back to all forecast entities for a different selected hub", () => {
    const hass: HassLike = {
      states: {
        "sensor.alpha_import_power": {
          entity_id: "sensor.alpha_import_power",
          attributes: {
            element_type: "grid",
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1.0 },
              { time: "2026-03-14T00:05:00Z", value: 2.0 },
            ],
          },
        },
        "sensor.beta_import_power": {
          entity_id: "sensor.beta_import_power",
          attributes: {
            element_type: "grid",
            field_type: "power",
            output_name: "import_power",
            direction: "-",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 3.0 },
              { time: "2026-03-14T00:05:00Z", value: 4.0 },
            ],
          },
        },
      },
      entities: {
        "sensor.alpha_import_power": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.beta_import_power": { platform: "haeo", device_id: "dev-beta" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
        "dev-beta": { config_entries: ["hub-beta"] },
      },
    };

    expect(discoverForecastEntityIds(hass, "hub-beta")).toEqual(["sensor.beta_import_power"]);
  });

  it("returns null when the entity registry is unavailable", () => {
    expect(discoverHaeoHubEntryId({ states: {} })).toBeNull();
    expect(resolveHubEntryId({}, null)).toBeNull();
  });

  it("returns null when HAEO entities have no device links", () => {
    const hass: HassLike = {
      states: {},
      entities: {
        "sensor.haeo_status": { platform: "haeo" },
      },
    };

    expect(discoverHaeoHubEntryId(hass)).toBeNull();
  });

  it("lists state entities for a hub", () => {
    const hass: HassLike = {
      states: {
        "sensor.alpha_import_power": {
          entity_id: "sensor.alpha_import_power",
          attributes: { element_type: "grid", forecast: [{ time: "2026-03-14T00:00:00Z", value: 1 }] },
        },
        "sensor.beta_import_power": {
          entity_id: "sensor.beta_import_power",
          attributes: { element_type: "grid", forecast: [{ time: "2026-03-14T00:00:00Z", value: 2 }] },
        },
      },
      entities: {
        "sensor.alpha_import_power": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.beta_import_power": { platform: "haeo", device_id: "dev-beta" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
        "dev-beta": { config_entries: ["hub-beta"] },
      },
    };

    expect(entityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.alpha_import_power"]);
    expect(discoverForecastEntityIds(hass, null)).toEqual(["sensor.alpha_import_power", "sensor.beta_import_power"]);
  });

  it("rejects non-HAEO entities when device ownership is unknown", () => {
    const hass: HassLike = {
      states: {
        "sensor.other": {
          entity_id: "sensor.other",
          attributes: { forecast: [{ time: "2026-03-14T00:00:00Z", value: 1 }] },
        },
      },
      entities: {
        "sensor.other": { platform: "other", device_id: "dev-other" },
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-other": { config_entries: ["hub-other"] },
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(entityBelongsToHub(hass, "sensor.other", "hub-alpha")).toBe(false);
  });

  it("falls back when a device has no config entries", () => {
    const hass: HassLike = {
      states: {
        "sensor.grid_import_power": {
          entity_id: "sensor.grid_import_power",
          attributes: {
            element_type: "grid",
            forecast: [{ time: "2026-03-14T00:00:00Z", value: 1 }],
          },
        },
      },
      entities: {
        "sensor.grid_import_power": { platform: "haeo", device_id: "dev-empty" },
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-empty": { config_entries: [] },
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(entityBelongsToHub(hass, "sensor.grid_import_power", "hub-alpha")).toBe(true);
  });

  it("rejects non-HAEO entities with no state when device config entries are empty", () => {
    const hass: HassLike = {
      states: {},
      entities: {
        "sensor.unknown": { platform: "other", device_id: "dev-empty" },
      },
      devices: {
        "dev-empty": { config_entries: [] },
      },
    };

    expect(entityBelongsToHub(hass, "sensor.unknown", "hub-alpha")).toBe(false);
  });

  it("recognizes HAEO entities from registry platform and state attributes", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_status": {
          entity_id: "sensor.haeo_status",
          attributes: { output_name: "network_optimization_status" },
        },
        "sensor.custom": {
          entity_id: "sensor.custom",
          attributes: { platform: "haeo" },
        },
      },
      entities: {
        "sensor.haeo_status": { device_id: "dev-alpha" },
        "sensor.custom": { device_id: "dev-alpha" },
        "sensor.haeo_registry_only": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    expect(discoverHaeoHubEntryId(hass)).toBe("hub-alpha");
    expect(entityBelongsToHub(hass, "sensor.haeo_registry_only", "hub-alpha")).toBe(true);
  });

  it("skips undefined states and non-HAEO registry entries when discovering hubs", () => {
    const hass: HassLike = {
      states: {
        "sensor.missing_state": undefined as unknown as HassLike["states"][string],
        "sensor.haeo_status": {
          entity_id: "sensor.haeo_status",
          attributes: { element_type: "node" },
        },
      },
      entities: {
        "sensor.missing_state": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.other_platform": { platform: "mqtt", device_id: "dev-other" },
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
        "dev-other": { config_entries: ["hub-other"] },
      },
    };

    expect(entityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.haeo_status"]);
    expect(discoverHaeoHubEntryId(hass)).toBe("hub-alpha");
  });
});
