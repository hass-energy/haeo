import { afterEach, describe, expect, it, vi } from "vitest";

import scenarioOutputs from "../../../tests/scenarios/scenario1/outputs.json";
import type { HassLike } from "./series";
import { isTopologyData } from "./topology-card-utils";
import { TopologyCardController } from "./topology-card-controller";
import { topologyCardSize, TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX } from "./topology-layout";

function findScenarioTopologyState(): { entityId: string; state: Record<string, unknown> } | null {
  for (const [entityId, state] of Object.entries(scenarioOutputs)) {
    const topology = (state as { attributes?: Record<string, unknown> }).attributes?.["topology"];
    if (isTopologyData(topology)) {
      return { entityId, state: state as Record<string, unknown> };
    }
  }
  return null;
}

function scenarioHass(scenario: { entityId: string; state: Record<string, unknown> }, hubEntryId: string): HassLike {
  return {
    states: {
      [scenario.entityId]: scenario.state as unknown as HassLike["states"][string],
    },
    entities: {
      [scenario.entityId]: { platform: "haeo", device_id: "dev-alpha" },
    },
    devices: {
      "dev-alpha": { config_entries: [hubEntryId] },
    },
  };
}

describe("TopologyCardController", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders topology data when connected", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new TopologyCardController(host);

    controller.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    controller.setHass(scenarioHass(scenario, "hub-alpha"));
    controller.connected();

    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    expect(host.shadowRoot?.querySelector("svg")).toBeTruthy();
  });

  it("reports grid options from the current layout height", () => {
    const host = document.createElement("div");
    const controller = new TopologyCardController(host);
    const rows = topologyCardSize(TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX);

    expect(controller.getCardSize()).toBe(rows);
    expect(controller.getGridOptions()).toEqual({
      rows,
      min_rows: Math.max(3, rows - 1),
      columns: "full",
    });
  });

  it("disconnects without error after rendering host elements", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new TopologyCardController(host);

    controller.setConfig({ type: "custom:haeo-topology-card" });
    controller.connected();
    expect(host.shadowRoot?.querySelector("#mount")).toBeTruthy();

    expect(() => controller.disconnected()).not.toThrow();
  });

  it("does not dispatch ll-update when layout height keeps the same card size", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new TopologyCardController(host);
    const updates: Event[] = [];
    host.addEventListener("ll-update", (event) => {
      updates.push(event);
    });

    controller.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    controller.setHass(scenarioHass(scenario, "hub-alpha"));
    controller.connected();

    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    const initialCount = updates.length;
    controller.setConfig({
      type: "custom:haeo-topology-card",
      title: "Same card size",
      hub_entry_id: "hub-alpha",
    });

    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    expect(updates.length).toBe(initialCount);
  });

  it("ignores layout height updates that keep the same card size", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new TopologyCardController(host);
    const updates: Event[] = [];
    host.addEventListener("ll-update", (event) => {
      updates.push(event);
    });

    controller.setConfig({ type: "custom:haeo-topology-card" });
    controller.connected();

    const onLayoutHeight = (controller as unknown as { onLayoutHeight: (height: number) => void }).onLayoutHeight;
    onLayoutHeight(349);

    expect(updates.length).toBe(0);
  });

  it("returns early from render when the mount node is missing", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const controller = new TopologyCardController(host);

    controller.setConfig({ type: "custom:haeo-topology-card" });
    controller.connected();
    const shadowRoot = host.shadowRoot;
    expect(shadowRoot).toBeTruthy();
    if (!shadowRoot) {
      throw new Error("Expected shadow root");
    }
    vi.spyOn(shadowRoot, "querySelector").mockReturnValue(null);
    expect(() => controller.setConfig({ type: "custom:haeo-topology-card", title: "Retry" })).not.toThrow();
  });
});
