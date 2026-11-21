import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InputField } from "./InputField";
import type { InputFieldProps } from "./InputField";
import { HaeoInputSelector } from "./input-selector";
import type { InputSelectorConfig, InputValue, SelectorHass } from "./types";

const STRINGS: Record<string, string> = {
  "input.options.add_entities": "Add entities to {label}",
  "input.options.choose_entities": "Choose entities for {label}",
  "input.options.clear": "Clear {label}",
  "input.options.remove": "Remove {name}",
  "input.options.search": "Search entities for {label}",
  "input.options.select_all": "Select all {count}",
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
  domains: ["sensor"],
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

function byLabel(label: string): HTMLElement {
  const element = container.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (element === null) {
    throw new Error(`Nothing labelled ${label}`);
  }
  return element;
}

function numberBox(): HTMLInputElement | null {
  return container.querySelector<HTMLInputElement>("input[type=number]");
}

function type(input: HTMLInputElement, text: string): void {
  act(() => {
    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function search(text: string): void {
  const input = container.querySelector<HTMLInputElement>("input[role=combobox]");
  if (input === null) {
    throw new Error("No search box");
  }
  act(() => input.dispatchEvent(new FocusEvent("focus")));
  type(input, text);
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

function pick(text: string): void {
  act(() => byLabel("Choose entities for Forecast").click());
  search(text);
}

describe("InputField", () => {
  it("shows an unset field as an empty number box, with no text beyond its label", () => {
    show();
    expect(numberBox()?.value).toBe("");
    expect(container.textContent).toBe("ForecastkW");
  });

  it("takes a number typed into the box as a fixed value", () => {
    const onChange = show();
    const box = numberBox();
    if (box !== null) {
      type(box, "0.8");
    }
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: 0.8 });
  });

  it("unsets a field whose box is emptied, keeping the box to type into", () => {
    const onChange = show({ value: { type: "constant", value: 3 } });
    const box = numberBox();
    if (box !== null) {
      type(box, "");
    }
    expect(onChange).toHaveBeenCalledWith({ type: "none" });
    expect(numberBox()).not.toBeNull();
  });

  it("clears a fixed value with its clear button", () => {
    const onChange = show({ value: { type: "constant", value: 3 } });
    act(() => byLabel("Clear Forecast").click());
    expect(onChange).toHaveBeenCalledWith({ type: "none" });
  });

  it("adds a checked entity after the ones already chosen", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.west"] } });
    act(() => byLabel("Add entities to Forecast").click());
    search("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west", "sensor.east"] });
  });

  it("shows chosen entities in place of the number box, each with its current value", () => {
    show({ value: { type: "entity", value: ["sensor.east"] } });
    expect(numberBox()).toBeNull();
    expect(container.querySelector(".entities")?.textContent).toBe("East solar3 kW");
  });

  it("checks every match with the select-all row, which shows how many there are", () => {
    const onChange = show();
    pick("solar");
    const all = byLabel("Select all 2");
    expect(all.textContent).toBe("2");
    act(() => all.click());
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.east", "sensor.west"] });
  });

  it("unchecks every match with the select-all row when all are checked", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west", "sensor.load"] } });
    act(() => byLabel("Add entities to Forecast").click());
    search("solar");
    act(() => byLabel("Select all 2").click());
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.load"] });
  });

  it("marks chosen entities and unchooses one on a second click", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west"] } });
    act(() => byLabel("Add entities to Forecast").click());
    search("east");
    expect(options()[0]?.getAttribute("aria-selected")).toBe("true");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west"] });
  });

  it("drops the on and off words of entities that are replaced", () => {
    const onChange = show({
      value: { type: "entity", value: ["sensor.west"], on_states: ["Charging"], off_states: ["Idle"] },
    });
    act(() => byLabel("Add entities to Forecast").click());
    search("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west", "sensor.east"] });
  });

  it.each<[InputSelectorConfig["kinds"], InputValue]>([
    [["entity", "constant", "none"], { type: "none" }],
    [["entity", "constant"], { type: "entity", value: [] }],
  ])("removing the last entity of a field accepting %j leaves %j", (kinds, expected) => {
    const onChange = show({ config: { ...numberConfig, kinds }, value: { type: "entity", value: ["sensor.east"] } });
    act(() => byLabel("Remove East solar").click());
    expect(onChange).toHaveBeenCalledWith(expected);
  });

  it("shows the search in place of a value box for a field taking only entities", () => {
    show({ config: { ...numberConfig, kinds: ["entity"] }, value: { type: "entity", value: [] } });
    expect(numberBox()).toBeNull();
    expect(container.querySelector("input[role=combobox]")).not.toBeNull();
  });

  it("toggles an on/off field's fixed value with a switch", () => {
    const booleanConfig: InputSelectorConfig = { ...numberConfig, value_type: "boolean" };
    const onChange = show({ config: booleanConfig });
    act(() => container.querySelector<HTMLButtonElement>("[role=switch]")?.click());
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: true });

    const toggled = show({ config: booleanConfig, value: { type: "constant", value: true } });
    act(() => container.querySelector<HTMLButtonElement>("[role=switch]")?.click());
    expect(toggled).toHaveBeenCalledWith({ type: "constant", value: false });
  });

  it("picks the first match with Enter without letting the form see the key", () => {
    const onChange = show();
    pick("west");
    const submitted = vi.fn();
    container.addEventListener("keydown", submitted);
    act(() => {
      container
        .querySelector<HTMLInputElement>("input[role=combobox]")
        ?.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west"] });
    expect(submitted).not.toHaveBeenCalled();
  });

  it("closes the list with Escape without letting the dialog see the key", () => {
    show();
    pick("");
    const closed = vi.fn();
    container.addEventListener("keydown", closed);
    act(() => {
      container
        .querySelector<HTMLInputElement>("input[role=combobox]")
        ?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(options()).toHaveLength(0);
    expect(closed).not.toHaveBeenCalled();
  });
});

describe("HaeoInputSelector", () => {
  it("reports a change as a composed value-changed event, with labels from the integration's translations", () => {
    customElements.define("test-haeo-input", class extends HaeoInputSelector {});
    const element = document.createElement("test-haeo-input") as HaeoInputSelector;
    const localize = vi.fn((key: string, values?: Record<string, string>) =>
      key === "component.haeo.selector.input.options.choose_entities" ? `Pick ${values?.["label"] ?? ""}` : ""
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

    const pickButton = element.shadowRoot?.querySelector<HTMLButtonElement>("[aria-label='Pick Forecast']");
    expect(pickButton).not.toBeNull();
    const box = element.shadowRoot?.querySelector<HTMLInputElement>("input[type=number]");
    act(() => {
      if (box !== null && box !== undefined) {
        box.value = "2";
        box.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });

    const event = changed.mock.calls[0]?.[0] as CustomEvent<{ value: InputValue }>;
    expect(event.detail.value).toEqual({ type: "constant", value: 2 });
    expect(element.value).toEqual({ type: "constant", value: 2 });
    document.body.removeEventListener("value-changed", changed);
    element.remove();
  });
});
