import { describe, expect, it } from "vitest";

import scenarioOutputs from "../../../tests/scenarios/scenario1/outputs.json";
import { discoverTopologyEntities, isTopologyData, readTopology, resolveTopology } from "./topology-card-utils";
import type { HassLike } from "./series";
import type { TopologyCardConfig } from "./types";

function findScenarioTopologyEntity(): string | null {
  for (const [entityId, state] of Object.entries(scenarioOutputs)) {
    const topology = (state as { attributes?: Record<string, unknown> }).attributes?.["topology"];
    if (isTopologyData(topology)) {
      return entityId;
    }
  }
  return null;
}

describe("topology-card-utils", () => {
  it("validates topology payloads", () => {
    expect(isTopologyData(null)).toBe(false);
    expect(isTopologyData({ nodes: [], edges: [] })).toBe(false);
    expect(isTopologyData({ nodes: [], edges: [], groups: {} })).toBe(true);
  });

  it("discovers optimization status entities with topology attributes", () => {
    const entityId = findScenarioTopologyEntity();
    expect(entityId).not.toBeNull();
    if (entityId === null) {
      throw new Error("Expected scenario topology entity");
    }

    const hass: HassLike = {
      states: {
        [entityId]: scenarioOutputs[entityId as keyof typeof scenarioOutputs] as HassLike["states"][string],
      },
    };

    expect(discoverTopologyEntities(hass)).toEqual([entityId]);
    expect(readTopology(hass, entityId)).toBeTruthy();
  });

  it("resolves topology for a configured hub", () => {
    const entityId = findScenarioTopologyEntity();
    expect(entityId).not.toBeNull();
    if (entityId === null) {
      throw new Error("Expected scenario topology entity");
    }

    const hass = {
      states: {
        [entityId]: scenarioOutputs[entityId as keyof typeof scenarioOutputs] as HassLike["states"][string],
      },
      entities: {
        [entityId]: { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    } as HassLike;
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    };

    const resolution = resolveTopology(config, hass);
    expect(resolution.status).toBe("ok");
    if (resolution.status !== "ok") {
      return;
    }
    expect(resolution.entityId).toBe(entityId);
    expect(resolution.topology).toBeTruthy();
  });

  it("reports hub_not_found when the configured hub no longer exists", () => {
    const entityId = findScenarioTopologyEntity();
    expect(entityId).not.toBeNull();
    if (entityId === null) {
      throw new Error("Expected scenario topology entity");
    }

    const hass = {
      states: {
        [entityId]: scenarioOutputs[entityId as keyof typeof scenarioOutputs] as HassLike["states"][string],
      },
      entities: {
        [entityId]: { platform: "haeo", device_id: "dev-beta" },
      },
      devices: {
        "dev-beta": { config_entries: ["hub-beta"] },
      },
    } as HassLike;
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-deleted",
    };

    expect(resolveTopology(config, hass)).toEqual({ status: "hub_not_found" });
  });

  it("returns no_entity when multiple hub topology entities cannot be disambiguated", () => {
    const hass: HassLike = {
      states: {
        "sensor.topology_a": {
          entity_id: "sensor.topology_a",
          attributes: {
            topology: { nodes: [], edges: [], groups: {} },
          },
        },
        "sensor.topology_b": {
          entity_id: "sensor.topology_b",
          attributes: {
            topology: { nodes: [], edges: [], groups: {} },
          },
        },
      },
      entities: {
        "sensor.topology_a": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.topology_b": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };

    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    };

    expect(resolveTopology(config, hass)).toEqual({ status: "no_entity" });
  });

  it("reports not_configured when hub is not configured", () => {
    const entityId = findScenarioTopologyEntity();
    expect(entityId).not.toBeNull();
    if (entityId === null) {
      throw new Error("Expected scenario topology entity");
    }

    const hass: HassLike = {
      states: {
        [entityId]: scenarioOutputs[entityId as keyof typeof scenarioOutputs] as HassLike["states"][string],
      },
    };
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
    };

    expect(resolveTopology(config, hass)).toEqual({ status: "not_configured" });
  });

  it("reports hub_not_found when hass is unavailable", () => {
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    };

    expect(readTopology(null, "sensor.example")).toBeNull();
    expect(resolveTopology(config, null)).toEqual({ status: "hub_not_found" });
  });

  it("skips undefined states when discovering topology entities", () => {
    const hass: HassLike = {
      states: {
        "sensor.missing": undefined as unknown as HassLike["states"][string],
        "sensor.haeo_status": {
          entity_id: "sensor.haeo_status",
          attributes: {
            output_name: "network_optimization_status",
            topology: { nodes: [], edges: [], groups: {} },
          },
        },
      },
    };

    expect(discoverTopologyEntities(hass)).toEqual(["sensor.haeo_status"]);
  });

  it("prefers the optimization status entity when multiple hub topology entities exist", () => {
    const hass: HassLike = {
      states: {
        "sensor.haeo_status": {
          entity_id: "sensor.haeo_status",
          attributes: {
            output_name: "network_optimization_status",
            topology: { nodes: [], edges: [], groups: {} },
          },
        },
        "sensor.other_topology": {
          entity_id: "sensor.other_topology",
          attributes: {
            topology: { nodes: [], edges: [], groups: {} },
          },
        },
      },
      entities: {
        "sensor.haeo_status": { platform: "haeo", device_id: "dev-alpha" },
        "sensor.other_topology": { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    };

    const resolution = resolveTopology(config, hass);
    expect(resolution.status).toBe("ok");
    if (resolution.status !== "ok") {
      return;
    }
    expect(resolution.entityId).toBe("sensor.haeo_status");
    expect(resolution.topology).toBeTruthy();
  });

  it("reports no_entity when registry metadata is missing", () => {
    const entityId = findScenarioTopologyEntity();
    expect(entityId).not.toBeNull();
    if (entityId === null) {
      throw new Error("Expected scenario topology entity");
    }

    const hass: HassLike = {
      states: {
        [entityId]: scenarioOutputs[entityId as keyof typeof scenarioOutputs] as HassLike["states"][string],
      },
      entities: {},
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };
    const config: TopologyCardConfig = {
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    };

    expect(resolveTopology(config, hass)).toEqual({ status: "no_entity" });
  });
});
