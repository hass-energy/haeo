import { describe, expect, it } from "vitest";

import { discoverForecastEntityIdsForHub, discoverHaeoHubEntryId } from "./hub-selection";
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
        "sensor.haeo_grid_import_power": { config_entry_id: "hub-alpha" },
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
        "sensor.haeo_grid_import_power": { config_entry_id: "hub-alpha" },
        "sensor.other_hub_import_power": { config_entry_id: "hub-beta" },
      },
    };

    expect(discoverForecastEntityIdsForHub(hass, "hub-alpha")).toEqual(["sensor.haeo_grid_import_power"]);
  });
});
