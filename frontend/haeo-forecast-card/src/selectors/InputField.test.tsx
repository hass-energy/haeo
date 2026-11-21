import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InputField } from "./InputField";
import type { InputFieldProps } from "./InputField";
import { HaeoInputSelector } from "./input-selector";
import type { InputSelectorConfig, InputValue, SelectorHass } from "./types";

const STRINGS: Record<string, string> = {
  "input.options.add_all": "Add all {count} matches",
  "input.options.use_value": "Use {value} as a fixed value",
  "input.options.remove": "Remove {name}",
  "input.options.not_set": "Not set",
  "input.options.clear": "Clear",
  "input.options.fixed_on": "On (fixed value)",
  "input.options.fixed_off": "Off (fixed value)",
  "input.options.hint_value": "Type a number to use it as a fixed value.",
  "input.options.hint_add_all": "Type to filter the list, then add every match at once.",
};

const t = (key: string, values: Record<string, string> = {}): string =>
  (STRINGS[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");

const hass: SelectorHass = {
  localize: () => "",
  states: {
    "sensor.east": {
      entity_id: "sensor.east",
      state: "3",
      attributes: { friendly_name: "East solar", unit_of_measurement: "kW" },
    },
    "sensor.west": {
      entity_id: "sensor.west",
      state: "2",
      attributes: { friendly_name: "West solar", unit_of_measurement: "kW" },
    },
    "sensor.load": {
      entity_id: "sensor.load",
      state: "1",
      attributes: { friendly_name: "House load", unit_of_measurement: "kW" },
    },
  },
};

const numberConfig: InputSelectorConfig = {
  kinds: ["entity", "constant", "none"],
  value_type: "number",
  multiple: true,
  entities: ["sensor.east", "sensor.west", "sensor.load"],
  unit: "kW",
};

/** Run a synchronous update; act flushes it before returning. */
function act(callback: () => void): void {
  void actAsync(callback);
}

let container: HTMLElement;

beforeEach(() => {
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  render(null, container);
  container.remove();
});

function show(overrides: Partial<InputFieldProps> = {}): ReturnType<typeof vi.fn> {
  const onChange = vi.fn();
  act(() => {
    render(
      <InputField
        config={numberConfig}
        value={{ type: "none" }}
        hass={hass}
        label="Forecast"
        required={false}
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

function search(text: string): void {
  const input = container.querySelector<HTMLInputElement>("input[role=combobox]");
  if (input === null) {
    throw new Error("No search box");
  }
  act(() => {
    input.dispatchEvent(new FocusEvent("focus"));
    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function options(): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>("[role=option]"));
}

function clickOption(text: string): void {
  const option = options().find((element) => element.textContent.includes(text));
  if (option === undefined) {
    throw new Error(`No option ${text}`);
  }
  act(() => option.click());
}

describe("InputField", () => {
  it("says a field without a value is not set", () => {
    show();
    expect(container.textContent).toContain("Not set");
  });

  it("explains how to enter a fixed value and add every match while the search is empty", () => {
    show();
    search("");
    expect(container.querySelector(".hint")?.textContent).toBe(
      "Type a number to use it as a fixed value.Type to filter the list, then add every match at once."
    );
    search("east");
    expect(container.querySelector(".hint")).toBeNull();
  });

  it("offers a typed number as a fixed value", () => {
    const onChange = show();
    search("0.8");
    clickOption("Use 0.8 kW as a fixed value");
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: 0.8 });
  });

  it("adds a picked entity after the ones already chosen", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.west"] } });
    search("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west", "sensor.east"] });
  });

  it("adds every unchosen match at once", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.west"] } });
    search("solar");
    expect(options().map((option) => option.textContent)).not.toContain("Add all 2 matches");
    search("sensor");
    clickOption("Add all 2 matches");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west", "sensor.east", "sensor.load"] });
  });

  it("keeps the states an entity value lists when its entities change", () => {
    const onChange = show({
      value: { type: "entity", value: ["sensor.west"], on_states: ["Charging"], off_states: ["Idle"] },
    });
    search("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({
      type: "entity",
      value: ["sensor.west", "sensor.east"],
      on_states: ["Charging"],
      off_states: ["Idle"],
    });
  });

  it("marks chosen entities and unchooses one on a second click", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west"] } });
    search("east");
    expect(options()[0]?.getAttribute("aria-selected")).toBe("true");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west"] });
  });

  it("replaces the entity of a single-entity field", () => {
    const onChange = show({
      config: { ...numberConfig, multiple: false },
      value: { type: "entity", value: ["sensor.west"] },
    });
    search("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.east"] });
  });

  it.each<[InputSelectorConfig["kinds"], InputValue]>([
    [["entity", "constant", "none"], { type: "none" }],
    [["entity", "constant"], { type: "entity", value: [] }],
  ])("removing the last entity of a field accepting %j leaves %j", (kinds, expected) => {
    const onChange = show({ config: { ...numberConfig, kinds }, value: { type: "entity", value: ["sensor.east"] } });
    const remove = container.querySelector<HTMLButtonElement>("button[aria-label='Remove East solar']");
    act(() => remove?.click());
    expect(onChange).toHaveBeenCalledWith(expected);
  });

  it("clears an optional field", () => {
    const onChange = show({ value: { type: "constant", value: 3 } });
    const clear = Array.from(container.querySelectorAll("button")).find((button) => button.textContent === "Clear");
    act(() => clear?.click());
    expect(onChange).toHaveBeenCalledWith({ type: "none" });
  });

  it("edits a fixed number in place", () => {
    const onChange = show({ value: { type: "constant", value: 3 } });
    const input = container.querySelector<HTMLInputElement>("input[type=number]");
    act(() => {
      if (input !== null) {
        input.value = "4.5";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: 4.5 });
  });

  it("offers fixed on and off for an on/off field, and toggles a fixed value", () => {
    const booleanConfig: InputSelectorConfig = { ...numberConfig, value_type: "boolean" };
    const onChange = show({ config: booleanConfig });
    search("");
    clickOption("On (fixed value)");
    expect(onChange).toHaveBeenLastCalledWith({ type: "constant", value: true });

    const toggled = show({ config: booleanConfig, value: { type: "constant", value: true } });
    act(() => container.querySelector<HTMLButtonElement>("[role=switch]")?.click());
    expect(toggled).toHaveBeenCalledWith({ type: "constant", value: false });
  });

  it("picks the highlighted option with Enter without letting the form see the key", () => {
    const onChange = show();
    search("west");
    const input = container.querySelector<HTMLInputElement>("input[role=combobox]");
    const submitted = vi.fn();
    container.addEventListener("keydown", submitted);
    act(() => {
      input?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west"] });
    expect(submitted).not.toHaveBeenCalled();
  });
});

describe("HaeoInputSelector", () => {
  it("reports a change as a composed value-changed event, with strings from the integration's translations", () => {
    customElements.define("test-haeo-input", class extends HaeoInputSelector {});
    const element = document.createElement("test-haeo-input") as HaeoInputSelector;
    const localize = vi.fn((key: string) =>
      key === "component.haeo.selector.input.options.not_set" ? "Nothing yet" : ""
    );
    element.hass = { ...hass, localize };
    element.selector = { haeo_input: numberConfig };
    element.value = { type: "none" };
    element.label = "Forecast";
    const changed = vi.fn();
    document.body.addEventListener("value-changed", changed);
    act(() => {
      document.body.append(element);
    });

    expect(element.shadowRoot?.textContent).toContain("Nothing yet");
    const input = element.shadowRoot?.querySelector<HTMLInputElement>("input[role=combobox]");
    act(() => {
      input?.dispatchEvent(new FocusEvent("focus"));
    });
    const option = element.shadowRoot?.querySelector<HTMLElement>("[role=option]");
    act(() => option?.click());

    const event = changed.mock.calls[0]?.[0] as CustomEvent<{ value: InputValue }>;
    expect(event.detail.value).toEqual({ type: "entity", value: ["sensor.east"] });
    expect(element.value).toEqual({ type: "entity", value: ["sensor.east"] });
    document.body.removeEventListener("value-changed", changed);
    element.remove();
  });
});
