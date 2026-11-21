import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InputField } from "./InputField";
import type { InputFieldProps } from "./InputField";
import { HaeoInputSelector } from "./input-selector";
import type { InputSelectorConfig, InputValue, SelectorHass } from "./types";

const STRINGS: Record<string, string> = {
  "input.options.current_value": "Current value {value}",
  "input.options.forecast": "Forecast",
  "input.options.enter_value": "{label}: enter a value",
  "input.options.fixed": "Fixed value",
  "input.options.fixed_value": "Fixed value {value}",
  "input.options.off": "Off",
  "input.options.on": "On",
  "input.options.remove": "Remove {name}",
  "input.options.search": "{label}: search entities or enter a value",
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
  forecasts: {},
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

function field(): HTMLInputElement {
  const input = container.querySelector<HTMLInputElement>("input[role=combobox]");
  if (input === null) {
    throw new Error("No input");
  }
  return input;
}

function type(text: string): void {
  const input = field();
  act(() => input.dispatchEvent(new FocusEvent("focus")));
  act(() => {
    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function press(key: string): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  act(() => field().dispatchEvent(event));
  return event;
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
  it("shows an unset field as an empty input with no text beyond its label", () => {
    show();
    expect(field().value).toBe("");
    expect(container.textContent).toBe("Forecast");
  });

  it("tells screen readers the field searches entities and takes a value", () => {
    show();
    expect(field().getAttribute("aria-label")).toBe("Forecast: search entities or enter a value");
    show({ config: { ...numberConfig, kinds: ["constant", "none"] } });
    expect(field().getAttribute("aria-label")).toBe("Forecast: enter a value");
  });

  it("offers a typed number as a fixed value above the entities, and picks it with Enter", () => {
    const onChange = show();
    type("0.8");
    expect(options()[0]?.getAttribute("aria-label")).toBe("Fixed value 0.8 kW");
    const enter = press("Enter");
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: 0.8 });
    expect(enter.defaultPrevented).toBe(true);
  });

  it("keeps the form from seeing the Enter that picks a choice", () => {
    show();
    type("0.8");
    const submitted = vi.fn();
    container.addEventListener("keydown", submitted);
    press("Enter");
    expect(submitted).not.toHaveBeenCalled();
  });

  it("offers a number outside the field's range without letting it be picked", () => {
    const onChange = show({ config: { ...numberConfig, min: 0, max: 10 } });
    type("12");
    expect(options()[0]?.getAttribute("aria-disabled")).toBe("true");
    press("Enter");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("shows a fixed value as a chip with its unit, distinct from entity chips", () => {
    show({ value: { type: "constant", value: 0.8 } });
    expect(container.querySelector(".chip.constant .readout.fixed")?.textContent).toBe("0.8kW");
    expect(container.querySelector(".chip.constant")?.textContent).toBe("0.8kWFixed value");
    expect(container.querySelector(".chip.entity")).toBeNull();
  });

  it("puts a fixed value's chip back into the input to change it", () => {
    const onChange = show({ value: { type: "constant", value: 0.8 } });
    act(() => byLabel("Fixed value 0.8 kW").click());
    expect(onChange).toHaveBeenCalledWith({ type: "none" });
    expect(field().value).toBe("0.8");
  });

  it("removes a fixed value with its chip's remove button", () => {
    const onChange = show({ value: { type: "constant", value: 3 } });
    act(() => byLabel("Remove 3 kW").click());
    expect(onChange).toHaveBeenCalledWith({ type: "none" });
  });

  it("adds a picked entity as a chip after the ones already chosen", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.west"] } });
    type("east");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west", "sensor.east"] });
  });

  it("shows chosen entities as chips led by their current values", () => {
    show({ value: { type: "entity", value: ["sensor.east"] } });
    expect(container.querySelector(".chip.entity")?.textContent).toBe("3kWEast solar");
  });

  it("rounds a current value to fit its readout, and tells screen readers the whole value", () => {
    const precise: SelectorHass = {
      ...hass,
      states: {
        "sensor.east": { entity_id: "sensor.east", state: "0.501000", attributes: { unit_of_measurement: "kW" } },
      },
    };
    show({ hass: precise, value: { type: "entity", value: ["sensor.east"] } });
    const readout = container.querySelector(".chip.entity .readout");
    expect(readout?.querySelector(".readout-value")?.textContent).toBe("0.501");
    expect(readout?.getAttribute("aria-label")).toBe("Current value 0.501000 kW");
  });

  it("shows an entity with no reading without a unit", () => {
    const unavailable: SelectorHass = {
      ...hass,
      states: {
        "sensor.east": { entity_id: "sensor.east", state: "unavailable", attributes: { unit_of_measurement: "kW" } },
      },
    };
    show({ hass: unavailable, value: { type: "entity", value: ["sensor.east"] } });
    const readout = container.querySelector(".chip.entity .readout");
    expect(readout?.textContent).toBe("–");
    expect(readout?.getAttribute("aria-label")).toBe("Current value –");
  });

  it("reads an on/off state in the user's words, seen and heard", () => {
    const switched: SelectorHass = {
      ...hass,
      states: { "switch.pump": { entity_id: "switch.pump", state: "on", attributes: {} } },
    };
    show({
      config: { ...numberConfig, value_type: "boolean", entities: ["switch.pump"] },
      hass: switched,
      value: { type: "entity", value: ["switch.pump"] },
    });
    const readout = container.querySelector(".chip.entity .readout");
    expect(readout?.textContent).toBe("On");
    expect(readout?.getAttribute("aria-label")).toBe("Current value On");
  });

  it("leads forecasts with a chart when there is no preview, and others with their current value", () => {
    show({
      config: { ...numberConfig, forecasts: { "sensor.west": [] } },
      value: { type: "entity", value: ["sensor.east", "sensor.west"] },
    });
    const [east, west] = Array.from(container.querySelectorAll(".chip.entity"));
    expect(east?.querySelector("[role=img]")?.getAttribute("aria-label")).toBe("Current value 3 kW");
    expect(east?.textContent).toBe("3kWEast solar");
    expect(west?.querySelector("[role=img]")?.getAttribute("aria-label")).toBe("Forecast");
    expect(west?.querySelector(".readout svg.icon")).not.toBeNull();
    expect(west?.textContent).toBe("West solar");
  });

  it("draws a forecast's preview in place of its chart icon", () => {
    show({
      config: { ...numberConfig, forecasts: { "sensor.west": [1, 3, 2] } },
      value: { type: "entity", value: ["sensor.west"] },
    });
    const readout = container.querySelector(".chip.entity .readout");
    expect(readout?.getAttribute("aria-label")).toBe("Forecast");
    expect(readout?.querySelector("polyline")?.getAttribute("points")).toBe("0.0,16.0 18.0,2.0 36.0,9.0");
  });

  it("lists forecasts and current values together, each marked by how the field reads it", () => {
    show({ config: { ...numberConfig, forecasts: { "sensor.west": [] } } });
    type("solar");
    const marks = options()
      .slice(1)
      .map((option) => option.querySelector("[role=img]")?.getAttribute("aria-label"));
    expect(marks).toEqual(["Current value 3 kW", "Forecast"]);
  });

  it("replaces entities with a picked fixed value", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east"] } });
    type("2");
    act(() => byLabel("Fixed value 2 kW").click());
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: 2 });
  });

  it("checks every match with the select-all row, which shows how many there are", () => {
    const onChange = show();
    type("solar");
    const all = byLabel("Select all 2");
    expect(all.textContent).toBe("2");
    act(() => all.click());
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.east", "sensor.west"] });
  });

  it("unchecks every match with the select-all row when all are checked", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west", "sensor.load"] } });
    type("solar");
    act(() => byLabel("Select all 2").click());
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.load"] });
  });

  it("clears the search and closes the list after a pick", () => {
    show();
    type("east");
    clickOption("East solar");
    expect(field().value).toBe("");
    expect(options()).toHaveLength(0);
  });

  it("marks chosen entities and unchooses one on a second click", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west"] } });
    type("east");
    expect(options()[0]?.getAttribute("aria-selected")).toBe("true");
    clickOption("East solar");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.west"] });
  });

  it("drops the on and off words of entities that are replaced", () => {
    const onChange = show({
      value: { type: "entity", value: ["sensor.west"], on_states: ["Charging"], off_states: ["Idle"] },
    });
    type("east");
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

  it("removes the last chip with Backspace in an empty input", () => {
    const onChange = show({ value: { type: "entity", value: ["sensor.east", "sensor.west"] } });
    type("");
    press("Backspace");
    expect(onChange).toHaveBeenCalledWith({ type: "entity", value: ["sensor.east"] });
  });

  it("offers on and off as fixed values for an on/off field", () => {
    const onChange = show({ config: { ...numberConfig, value_type: "boolean" } });
    type("");
    expect(
      options()
        .slice(0, 2)
        .map((option) => option.getAttribute("aria-label"))
    ).toEqual(["Fixed value On", "Fixed value Off"]);
    clickOption("Off");
    expect(onChange).toHaveBeenCalledWith({ type: "constant", value: false });
  });

  it("closes the list with Escape without letting the dialog see the key", () => {
    show();
    type("");
    const closed = vi.fn();
    container.addEventListener("keydown", closed);
    press("Escape");
    expect(options()).toHaveLength(0);
    expect(closed).not.toHaveBeenCalled();
  });
});

describe("HaeoInputSelector", () => {
  it("reports a change as a composed value-changed event, with text from the integration's translations", () => {
    customElements.define("test-haeo-input", class extends HaeoInputSelector {});
    const element = document.createElement("test-haeo-input") as HaeoInputSelector;
    const localize = vi.fn((key: string, values?: Record<string, string>) =>
      key === "component.haeo.selector.input.options.fixed_value" ? `Fixed ${values?.["value"] ?? ""}` : ""
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

    const input = element.shadowRoot?.querySelector<HTMLInputElement>("input[role=combobox]");
    act(() => input?.dispatchEvent(new FocusEvent("focus")));
    act(() => {
      if (input !== null && input !== undefined) {
        input.value = "2";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    const option = element.shadowRoot?.querySelector<HTMLElement>("[aria-label='Fixed 2 kW']");
    act(() => option?.click());

    const event = changed.mock.calls[0]?.[0] as CustomEvent<{ value: InputValue }>;
    expect(event.detail.value).toEqual({ type: "constant", value: 2 });
    expect(element.value).toEqual({ type: "constant", value: 2 });
    document.body.removeEventListener("value-changed", changed);
    element.remove();
  });
});
