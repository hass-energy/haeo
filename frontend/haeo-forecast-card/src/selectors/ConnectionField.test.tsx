import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConnectionField } from "./ConnectionField";
import { HaeoConnectionSelector } from "./connection-selector";
import type { FieldContext } from "./selector-element";
import type { ConnectionSelectorConfig } from "./types";

function act(callback: () => void): void {
  void actAsync(callback);
}

const t = (key: string, values: Record<string, string> = {}): string =>
  ({
    "connection.options.ac_bus": `${values["name"] ?? ""}, AC`,
    "connection.options.dc_bus": `${values["name"] ?? ""}, DC`,
    "connection.options.bus": values["name"] ?? "",
  })[key] ?? key;

const config: ConnectionSelectorConfig = {
  element_type: "solar",
  targets: [
    {
      name: "Switchboard",
      element_type: "junction",
      bus: "ac",
      elements: [
        { name: "Grid", element_type: "grid" },
        { name: "Inverter", element_type: "inverter" },
      ],
    },
    { name: "Inverter", element_type: "inverter", bus: "dc", elements: [{ name: "Battery", element_type: "battery" }] },
    { name: "DC bus", element_type: "node", bus: null, elements: [] },
  ],
};

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  render(null, container);
  container.remove();
});

function show(overrides: Partial<FieldContext<ConnectionSelectorConfig, string>> = {}): ReturnType<typeof vi.fn> {
  const onChange = vi.fn();
  act(() => {
    render(
      <ConnectionField
        config={config}
        value="Inverter"
        hass={null}
        label="Connection"
        helper={undefined}
        required={true}
        disabled={false}
        t={t}
        onChange={onChange}
        {...overrides}
      />,
      container
    );
  });
  return onChange;
}

function bus(name: string): HTMLElement {
  const element = Array.from(container.querySelectorAll<HTMLElement>("[role=radio]")).find(
    (radio) => radio.querySelector(".bus-name")?.textContent === name
  );
  if (element === undefined) {
    throw new Error(`No bus ${name}`);
  }
  return element;
}

describe("ConnectionField", () => {
  it("shows each target as an AC or DC bus with the elements already on it", () => {
    show();
    expect(bus("Switchboard").getAttribute("aria-label")).toBe("Switchboard, AC");
    expect(bus("Inverter").getAttribute("aria-label")).toBe("Inverter, DC");
    expect(bus("Switchboard").querySelector(".bus-elements")?.textContent).toBe("🏭Grid🔄Inverter");
  });

  it("shows a bus of unknown kind by its element's icon, with no AC or DC mark", () => {
    show();
    const unknown = bus("DC bus");
    expect(unknown.getAttribute("aria-label")).toBe("DC bus");
    expect(unknown.querySelector(".bus-icon")?.textContent).toBe("⚡");
    expect(unknown.querySelector("svg")).toBeNull();
  });

  it("marks the chosen bus and shows the new element on it", () => {
    show();
    expect(bus("Inverter").getAttribute("aria-checked")).toBe("true");
    expect(bus("Inverter").querySelector(".ghost")?.textContent).toBe("☀️");
    expect(bus("Switchboard").querySelector(".ghost")).toBeNull();
  });

  it("chooses a bus by clicking it", () => {
    const onChange = show();
    act(() => bus("Switchboard").click());
    expect(onChange).toHaveBeenCalledWith("Switchboard");
  });

  it("moves between buses with the arrow keys, wrapping at the ends", () => {
    const onChange = show({ value: "DC bus" });
    act(() => {
      bus("DC bus").dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith("Switchboard");
  });
});

describe("HaeoConnectionSelector", () => {
  it("reports the chosen bus as a composed value-changed event", () => {
    customElements.define("test-haeo-connection", class extends HaeoConnectionSelector {});
    const element = document.createElement("test-haeo-connection") as HaeoConnectionSelector;
    element.hass = { states: {}, localize: () => "" };
    element.selector = { haeo_connection: config };
    element.value = "Inverter";
    element.label = "Connection";
    const changed = vi.fn();
    document.body.addEventListener("value-changed", changed);
    act(() => {
      document.body.append(element);
    });

    const switchboard = element.shadowRoot?.querySelector<HTMLElement>("[role=radio]");
    act(() => switchboard?.click());

    const event = changed.mock.calls[0]?.[0] as CustomEvent<{ value: string }>;
    expect(event.detail.value).toBe("Switchboard");
    document.body.removeEventListener("value-changed", changed);
    element.remove();
  });
});
