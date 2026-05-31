import { afterEach, describe, expect, it } from "vitest";

import scenarioOutputs from "../../../tests/scenarios/scenario1/outputs.json";
import { isTopologyData } from "./topology-card-utils";
import "./topology-card";

interface HaeoTopologyCardElement extends HTMLElement {
  setConfig: (config: { type: "custom:haeo-topology-card"; hub_entry_id?: string; entity?: string }) => void;
  hass: unknown;
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
      entity: scenario.entityId,
    });
    element.hass = {
      states: {
        [scenario.entityId]: scenario.state,
      },
    };
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

  it("renders topology preview using the first discovered hub", async () => {
    const scenario = findScenarioTopologyState();
    expect(scenario).not.toBeNull();
    if (scenario === null) {
      throw new Error("Expected scenario topology state");
    }

    const element = document.createElement("haeo-topology-card") as HaeoTopologyCardElement;
    element.setConfig({
      type: "custom:haeo-topology-card",
    });
    element.hass = {
      states: {
        [scenario.entityId]: scenario.state,
      },
      entities: {
        [scenario.entityId]: { platform: "haeo", device_id: "dev-alpha" },
      },
      devices: {
        "dev-alpha": { config_entries: ["hub-alpha"] },
      },
    };
    document.body.appendChild(element);
    await new Promise((resolve) => {
      setTimeout(resolve, 500);
    });

    expect(element.shadowRoot?.textContent).not.toContain("Configure a HAEO hub in the card editor");
    expect(element.shadowRoot?.querySelector("svg")).toBeTruthy();
    element.remove();
  });
});
