import { afterEach, describe, expect, it, vi } from "vitest";

import "./editor.tsx";
import type { ForecastCardConfig } from "./types";

type EditorElement = HTMLElement & {
  setConfig: (config: ForecastCardConfig) => void;
  hass: unknown;
};

function waitForAsync(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

describe("haeo forecast card editor", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("defines the editor custom element", () => {
    const ctor = customElements.get("haeo-forecast-card-editor");
    expect(ctor).toBeDefined();
  });

  it("discovers entities when hub_entry_id is set and emits config", async () => {
    const editor = document.createElement("haeo-forecast-card-editor") as EditorElement;
    const calls: ForecastCardConfig[] = [];
    editor.addEventListener("config-changed", (event) => {
      const customEvent = event as CustomEvent<{ config: ForecastCardConfig }>;
      calls.push(customEvent.detail.config);
    });

    editor.setConfig({ type: "custom:haeo-forecast-card", hub_entry_id: "hub-alpha" });
    editor.hass = {
      states: {
        "sensor.grid_import_power": {
          attributes: {
            forecast: [{ time: "2026-03-14T00:00:00Z", value: 1 }],
            element_name: "Grid",
          },
        },
        "sensor.battery_soc": {
          attributes: {
            forecast: [{ time: "2026-03-14T00:00:00Z", value: 50 }],
            element_name: "Battery",
          },
        },
      },
      callWS: () =>
        Promise.resolve([
          {
            entity_id: "sensor.grid_import_power",
            platform: "haeo",
            config_entry_id: "hub-alpha",
            disabled_by: null,
          },
          {
            entity_id: "sensor.battery_soc",
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
    expect(latest?.entities?.length).toBe(2);

    await vi.waitFor(
      () => {
        const text = editor.shadowRoot?.textContent ?? "";
        expect(text).toContain("2");
      },
      { timeout: 500 }
    );
  });

  it("updates title via form controls", async () => {
    const editor = document.createElement("haeo-forecast-card-editor") as EditorElement;
    const calls: ForecastCardConfig[] = [];
    editor.addEventListener("config-changed", (event) => {
      const customEvent = event as CustomEvent<{ config: ForecastCardConfig }>;
      calls.push(customEvent.detail.config);
    });
    editor.setConfig({ type: "custom:haeo-forecast-card", title: "Before" });
    editor.hass = {
      states: {},
      callWS: () => Promise.resolve([]),
    };
    document.body.appendChild(editor);
    await waitForAsync();

    const titleInput = editor.shadowRoot?.querySelector<HTMLInputElement>("#titleInput");
    expect(titleInput).toBeTruthy();

    if (titleInput) {
      titleInput.value = "After";
      titleInput.dispatchEvent(new Event("change", { bubbles: true }));
    }

    expect(calls.some((config) => config.title === "After")).toBe(true);
  });
});
