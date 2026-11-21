import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConnectionPathField } from "./ConnectionPathField";
import type { FieldContext } from "./selector-element";
import type { ConnectionPath, ConnectionPathConfig, InputSelectorConfig } from "./types";

function act(callback: () => void): void {
  void actAsync(callback);
}

const NAMES: Record<string, string> = {
  "input.options.remove": "Remove {name}",
  "connection_path.options.add_segment": "Add a segment here",
  "connection_path.options.cancel": "Cancel",
  "connection_path.options.power_limit": "Limit",
  "connection_path.options.pricing": "Price",
  "connection_path.options.efficiency": "Efficiency",
  "connection_path.options.source": "Source",
  "connection_path.options.target": "Target",
  "connection_path.options.move_earlier": "Move {segment} earlier",
  "connection_path.options.move_later": "Move {segment} later",
  "connection_path.options.remove_segment": "Remove {segment}",
};

const t = (key: string, values: Record<string, string> = {}): string =>
  (NAMES[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");

const input = (unit: string): InputSelectorConfig => ({
  kinds: ["entity", "constant"],
  value_type: "number",
  domains: ["sensor"],
  forecasts: {},
  entities: [],
  unit,
});

const config: ConnectionPathConfig = {
  participants: [
    { name: "Inverter", element_type: "inverter" },
    { name: "Switchboard", element_type: "junction" },
  ],
  segment_types: {
    power_limit: { field: "max_power", input: input("kW") },
    pricing: { field: "price", input: input("$/kWh") },
    efficiency: { field: "efficiency", input: input("%") },
  },
};

const LIMIT = { segment_type: "power_limit", max_power: { type: "constant", value: 10 } };
const LOSS = { segment_type: "efficiency", efficiency: { type: "constant", value: 95 } };
const PATH: ConnectionPath = { source: "Inverter", target: "Switchboard", segments: [LIMIT, LOSS] };

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  render(null, container);
  container.remove();
});

function show(value: ConnectionPath = PATH): ReturnType<typeof vi.fn> {
  const onChange = vi.fn();
  const context: FieldContext<ConnectionPathConfig, ConnectionPath> = {
    config,
    value,
    hass: null,
    label: "Connection",
    helper: undefined,
    required: true,
    disabled: false,
    t,
    onChange,
  };
  act(() => {
    render(<ConnectionPathField {...context} />, container);
  });
  return onChange;
}

function button(label: string, index = 0): HTMLButtonElement {
  const found = Array.from(container.querySelectorAll<HTMLButtonElement>("button")).filter(
    (element) => element.getAttribute("aria-label") === label || element.textContent === label
  )[index];
  if (found === undefined) {
    throw new Error(`No button ${label}`);
  }
  return found;
}

describe("ConnectionPathField", () => {
  it("reads from the source through each segment in order to the target", () => {
    show();
    const order = Array.from(container.querySelectorAll(".path-endpoint select, .path-segment-name")).map((element) =>
      element instanceof HTMLSelectElement ? element.value : element.textContent
    );
    expect(order).toEqual(["Inverter", "Limit", "Efficiency", "Switchboard"]);
  });

  it("inserts a segment of the chosen kind where its link's (+) is", () => {
    const onChange = show();
    act(() => button("Add a segment here", 1).click());
    act(() => button("Price").click());
    expect(onChange).toHaveBeenCalledWith({
      ...PATH,
      segments: [LIMIT, { segment_type: "pricing", price: undefined }, LOSS],
    });
  });

  it("moves a segment earlier or later, and removes it", () => {
    const onChange = show();
    act(() => button("Move Efficiency earlier").click());
    expect(onChange).toHaveBeenLastCalledWith({ ...PATH, segments: [LOSS, LIMIT] });
    act(() => button("Remove Limit").click());
    expect(onChange).toHaveBeenLastCalledWith({ ...PATH, segments: [LOSS] });
  });

  it("can't move the first segment earlier or the last later", () => {
    show();
    expect(button("Move Limit earlier").disabled).toBe(true);
    expect(button("Move Efficiency later").disabled).toBe(true);
  });

  it("changes an endpoint", () => {
    const onChange = show();
    const source = container.querySelector<HTMLSelectElement>("select[aria-label=Source]");
    act(() => {
      if (source !== null) {
        source.value = "Switchboard";
        source.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    expect(onChange).toHaveBeenCalledWith({ ...PATH, source: "Switchboard" });
  });

  it("edits a segment's input with its own input field", () => {
    const onChange = show();
    act(() => button("Remove 10 kW").click());
    expect(onChange).toHaveBeenLastCalledWith({
      ...PATH,
      segments: [{ ...LIMIT, max_power: { type: "entity", value: [] } }, LOSS],
    });
  });
});
