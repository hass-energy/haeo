import { describe, expect, it } from "vitest";

import scenarioOutputs from "../../../tests/scenarios/scenario1/outputs.json";
import { discoverTopologyEntities, isTopologyData, readTopology, resolveTopologyEntity } from "./topology-card-utils";
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

  it("prefers configured entity when available", () => {
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
      entity: entityId,
    };

    expect(resolveTopologyEntity(config, hass)).toBe(entityId);
  });
});
