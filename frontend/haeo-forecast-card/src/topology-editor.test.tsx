import { afterEach, describe, expect, it, vi } from "vitest";

import "./topology-editor.tsx";
import type { TopologyCardConfig } from "./types";

type EditorElement = HTMLElement & {
  setConfig: (config: TopologyCardConfig) => void;
  hass: unknown;
};

const TOPOLOGY_STATE = {
  entity_id: "sensor.haeo_optimization_status",
  attributes: {
    output_name: "network_optimization_status",
    topology: { nodes: [], edges: [], groups: {} },
  },
};

function waitForAsync(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

describe("haeo topology card editor", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("defines the editor custom element", () => {
    expect(customElements.get("haeo-topology-card-editor")).toBeDefined();
  });

  it("resolves the optimization status entity when a hub is set and emits config", async () => {
    const editor = document.createElement("haeo-topology-card-editor") as EditorElement;
    const calls: TopologyCardConfig[] = [];
    editor.addEventListener("config-changed", (event) => {
      const customEvent = event as CustomEvent<{ config: TopologyCardConfig }>;
      calls.push(customEvent.detail.config);
    });

    editor.setConfig({ type: "custom:haeo-topology-card", hub_entry_id: "hub-alpha" });
    editor.hass = {
      states: {
        "sensor.haeo_optimization_status": TOPOLOGY_STATE,
      },
      callWS: () =>
        Promise.resolve([
          {
            entity_id: "sensor.haeo_optimization_status",
            platform: "haeo",
            config_entry_id: "hub-alpha",
            disabled_by: null,
          },
        ]),
    };
    document.body.appendChild(editor);

    await vi.waitFor(
      () => {
        expect(calls.length).toBeGreaterThan(0);
      },
      { timeout: 500 }
    );

    const latest = calls[calls.length - 1];
    expect(latest?.hub_entry_id).toBe("hub-alpha");
    expect(latest?.entity).toBe("sensor.haeo_optimization_status");

    await vi.waitFor(
      () => {
        const text = editor.shadowRoot?.textContent ?? "";
        expect(text).toContain("sensor.haeo_optimization_status");
      },
      { timeout: 500 }
    );
  });

  it("reports when no topology sensor is found for the hub", async () => {
    const editor = document.createElement("haeo-topology-card-editor") as EditorElement;
    editor.setConfig({ type: "custom:haeo-topology-card", hub_entry_id: "hub-empty" });
    editor.hass = {
      states: {},
      callWS: () => Promise.resolve([]),
    };
    document.body.appendChild(editor);

    await vi.waitFor(
      () => {
        const text = editor.shadowRoot?.textContent ?? "";
        expect(text).toContain("No optimization status sensor");
      },
      { timeout: 500 }
    );
  });

  it("updates title via form controls", async () => {
    const editor = document.createElement("haeo-topology-card-editor") as EditorElement;
    const calls: TopologyCardConfig[] = [];
    editor.addEventListener("config-changed", (event) => {
      const customEvent = event as CustomEvent<{ config: TopologyCardConfig }>;
      calls.push(customEvent.detail.config);
    });
    editor.setConfig({ type: "custom:haeo-topology-card", title: "Before" });
    editor.hass = {
      states: {},
      callWS: () => Promise.resolve([]),
    };
    document.body.appendChild(editor);
    await waitForAsync();

    const titleInput = editor.shadowRoot?.querySelector<HTMLInputElement>("input[type=text]");
    expect(titleInput).toBeTruthy();

    if (titleInput) {
      titleInput.value = "After";
      titleInput.dispatchEvent(new Event("change", { bubbles: true }));
    }

    expect(calls.some((config) => config.title === "After")).toBe(true);
  });
});
