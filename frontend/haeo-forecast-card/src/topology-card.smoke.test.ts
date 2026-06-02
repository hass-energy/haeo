import { afterEach, describe, expect, it } from "vitest";

import scenarioOutputs from "../../../tests/scenarios/scenario1/outputs.json";
import type { HassLike } from "./series";
import { isTopologyData } from "./topology-card-utils";
import "./topology-card";

interface TopologyCardConstructor {
  getStubConfig: (hass?: HassLike) => { title?: string; hub_entry_id?: string };
  getConfigForm: () => { schema: Array<{ name: string }> };
}

interface HaeoTopologyCardElement extends HTMLElement {
  setConfig: (config: { type: "custom:haeo-topology-card"; title?: string; hub_entry_id?: string }) => void;
  hass: HassLike | null;
  getCardSize: () => number;
  getGridOptions: () => {
    rows: number;
    min_rows: number;
    columns: "full";
  };
}

function findScenarioTopologyState(): { entityId: string; state: Record<string, unknown> } | null {
  for (const [entityId, state] of Object.entries(scenarioOutputs)) {
    const topology = (state as { attributes?: Record<string, unknown> }).attributes?.["topology"];
    if (isTopologyData(topology)) {
      return { entityId, state: state as Record<string, unknown> };
    }
  }
  return null;
}

function topologyCardClass(): TopologyCardConstructor {
  const ctor = customElements.get("haeo-topology-card");
  if (ctor === undefined) {
    throw new Error("Expected haeo-topology-card custom element");
  }
  return ctor as unknown as TopologyCardConstructor;
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

async function waitForTopologyController(): Promise<void> {
  await import("./topology-card-controller");
  await new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

describe("haeo-topology-card smoke", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("defines the custom element and accepts config", () => {
    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    document.body.appendChild(element);

    expect(customElements.get("haeo-topology-card")).toBeDefined();
    expect(element).toBeInstanceOf(HTMLElement);
  });

  it("renders svg when topology data is provided", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    element.hass = scenarioHass(scenario, "hub-alpha");
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    const svg = element.shadowRoot?.querySelector("svg");
    expect(svg).toBeTruthy();
    element.remove();
  });

  it("renders configure hub message when no hub is available", async () => {
    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
    });
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });
    expect(element.shadowRoot?.textContent).toContain("Configure a HAEO hub in the card editor");
    element.remove();
  });

  it("builds stub config from hass and exposes the shared config form", () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const cardClass = topologyCardClass();
    expect(cardClass.getStubConfig()).toEqual({ title: "HAEO network topology" });
    expect(cardClass.getStubConfig(undefined)).toEqual({ title: "HAEO network topology" });

    const stub = cardClass.getStubConfig(scenarioHass(scenario, "hub-alpha"));
    expect(stub.hub_entry_id).toBe("hub-alpha");
    expect(cardClass.getConfigForm().schema.some((field) => field.name === "hub_entry_id")).toBe(true);
  });

  it("reports grid options from card size", () => {
    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    document.body.appendChild(element);
    expect(element.getCardSize()).toBe(7);
    expect(element.getGridOptions()).toEqual({
      rows: 7,
      min_rows: 6,
      columns: "full",
    });
    element.remove();
  });

  it("dispatches ll-update when layout height changes", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    const updates: Event[] = [];
    element.addEventListener("ll-update", (event) => {
      updates.push(event);
    });
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    element.hass = scenarioHass(scenario, "hub-alpha");
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    expect(updates.length).toBeGreaterThan(0);
    const initialCount = updates.length;
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });
    expect(updates.length).toBe(initialCount);
    element.remove();
  });

  it("renders topology after switching hub", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    element.hass = {
      states: {
        [scenario.entityId]: scenario.state as unknown as HassLike["states"][string],
        "sensor.other_topology": {
          entity_id: "sensor.other_topology",
          attributes: {
            output_name: "network_optimization_status",
            topology: (scenario.state as { attributes: Record<string, unknown> }).attributes["topology"],
          },
        },
      },
      entities: {
        [scenario.entityId]: { platform: "haeo", device_id: "dev-alpha" },
        "sensor.other_topology": { platform: "haeo", device_id: "dev-beta" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
        "dev-beta": { config_entries: ["hub-beta"] },
      },
    };
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-beta",
    });
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    expect(element.shadowRoot?.querySelector("svg")).toBeTruthy();
    element.remove();
  });

  it("keeps rendering when only the title changes", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
      title: "First title",
      hub_entry_id: "hub-alpha",
    });
    element.hass = scenarioHass(scenario, "hub-alpha");
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    element.setConfig({
      type: "custom:haeo-topology-card",
      title: "Second title",
      hub_entry_id: "hub-alpha",
    });
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });

    expect(element.shadowRoot?.textContent).toContain("Second title");
    expect(element.shadowRoot?.querySelector("svg")).toBeTruthy();
    element.remove();
  });

  it("shows configure hub message when no hub is configured at runtime", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
    });
    element.hass = scenarioHass(scenario, "hub-alpha");
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });

    expect(element.shadowRoot?.textContent).toContain("Configure a HAEO hub in the card editor");
    expect(element.shadowRoot?.querySelector("svg")).toBeNull();
    element.remove();
  });

  it("replays config and hass through the shim after the controller loads", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
      hub_entry_id: "hub-alpha",
    });
    document.body.appendChild(element);
    await waitForTopologyController();

    element.setConfig({
      type: "custom:haeo-topology-card",
      title: "Updated topology",
      hub_entry_id: "hub-alpha",
    });
    element.hass = scenarioHass(scenario, "hub-alpha");
    await new Promise((resolve) => {
      setTimeout(resolve, 20);
    });
    expect(element.hass.states[scenario.entityId]).toBeTruthy();
    expect(element.getGridOptions()).toEqual({
      rows: 7,
      min_rows: 6,
      columns: "full",
    });
    element.remove();
  });
});
