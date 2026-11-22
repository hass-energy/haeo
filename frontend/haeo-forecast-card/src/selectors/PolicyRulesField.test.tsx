import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PolicyRulesField } from "./PolicyRulesField";
import type { FieldContext } from "./selector-element";
import type { PolicyRule, PolicyRulesConfig } from "./types";

function act(callback: () => void): void {
  void actAsync(callback);
}

const STRINGS: Record<string, string> = {
  "input.options.remove": "Remove {name}",
  "policy_rules.options.add_endpoint": "Add an element to {end}",
  "policy_rules.options.add_rule": "Add rule",
  "policy_rules.options.any": "Any",
  "policy_rules.options.enabled": "{rule} on",
  "policy_rules.options.from": "From",
  "policy_rules.options.to": "To",
  "policy_rules.options.price": "{rule} price",
  "policy_rules.options.remove_rule": "Remove {rule}",
  "policy_rules.options.rule_name": "Rule name",
};

const t = (key: string, values: Record<string, string> = {}): string =>
  (STRINGS[key] ?? key).replace(/\{(\w+)\}/g, (_, name: string) => values[name] ?? "");

const config: PolicyRulesConfig = {
  sources: [
    { name: "Battery", element_type: "battery" },
    { name: "Solar", element_type: "solar" },
  ],
  targets: [
    { name: "Grid", element_type: "grid" },
    { name: "Load", element_type: "load" },
  ],
  price: { kinds: ["entity", "constant"], value_type: "number", domains: ["sensor"], forecasts: {}, unit: "$/kWh" },
  surfaced: [{ owner: "Battery", owner_type: "battery", source: ["Battery"], target: null }],
};

const WEAR: PolicyRule = {
  name: "Battery wear",
  enabled: true,
  source: ["Battery"],
  target: [],
  price: { type: "constant", value: 0.01 },
};
const EXPORT: PolicyRule = {
  name: "Solar export",
  enabled: false,
  source: ["Solar"],
  target: ["Grid"],
  price: { type: "constant", value: 0.02 },
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

function show(rules: PolicyRule[] = [WEAR, EXPORT]): ReturnType<typeof vi.fn> {
  const onChange = vi.fn();
  const context: FieldContext<PolicyRulesConfig, PolicyRule[]> = {
    config,
    value: rules,
    hass: null,
    label: "Rules",
    helper: undefined,
    required: true,
    disabled: false,
    t,
    onChange,
  };
  act(() => {
    render(<PolicyRulesField {...context} />, container);
  });
  return onChange;
}

function labelled<T extends HTMLElement>(label: string): T {
  const found = container.querySelector<T>(`[aria-label="${label}"]`);
  if (found === null) {
    throw new Error(`Nothing labelled ${label}`);
  }
  return found;
}

describe("PolicyRulesField", () => {
  it("shows an end naming no elements as any element", () => {
    show();
    const to = container.querySelectorAll<HTMLElement>("[role=group][aria-label=To]")[0];
    expect(to?.querySelector(".rule-any")?.textContent).toBe("Any");
  });

  it("marks a rule an element's own price field stands for with that element", () => {
    show();
    const owners = Array.from(container.querySelectorAll(".rule")).map((card) => card.querySelector(".rule-owner"));
    expect(owners.map((owner) => owner?.textContent ?? null)).toEqual(["🔋Battery", null]);
  });

  it("turns a rule on or off with its switch", () => {
    const onChange = show();
    act(() => labelled<HTMLButtonElement>("Solar export on").click());
    expect(onChange).toHaveBeenCalledWith([WEAR, { ...EXPORT, enabled: true }]);
  });

  it("adds an element to an end, offering only those not on it already", () => {
    const onChange = show();
    const add = container.querySelectorAll<HTMLSelectElement>("select[aria-label='Add an element to To']")[0];
    expect(Array.from(add?.options ?? []).map((option) => option.value)).toEqual(["", "Grid", "Load"]);
    act(() => {
      if (add !== undefined) {
        add.value = "Load";
        add.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    expect(onChange).toHaveBeenCalledWith([{ ...WEAR, target: ["Load"] }, EXPORT]);
  });

  it("removes an element from an end with its chip", () => {
    const onChange = show();
    act(() => labelled<HTMLButtonElement>("Remove Grid").click());
    expect(onChange).toHaveBeenCalledWith([WEAR, { ...EXPORT, target: [] }]);
  });

  it("adds a rule named apart from the others, and removes one", () => {
    const onChange = show([WEAR, { ...EXPORT, name: "Rule 3" }]);
    act(() => container.querySelector<HTMLButtonElement>(".rule-add")?.click());
    expect(onChange).toHaveBeenLastCalledWith([
      WEAR,
      { ...EXPORT, name: "Rule 3" },
      { name: "Rule 4", enabled: true, source: [], target: [], price: { type: "none" } },
    ]);
    act(() => labelled<HTMLButtonElement>("Remove Battery wear").click());
    expect(onChange).toHaveBeenLastCalledWith([{ ...EXPORT, name: "Rule 3" }]);
  });

  it("renames a rule", () => {
    const onChange = show();
    const name = container.querySelectorAll<HTMLInputElement>("input[aria-label='Rule name']")[0];
    act(() => {
      if (name !== undefined) {
        name.value = "Wear";
        name.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    expect(onChange).toHaveBeenCalledWith([{ ...WEAR, name: "Wear" }, EXPORT]);
  });

  it("keeps a rule's name box while its name is typed", () => {
    const onChange = show();
    const before = container.querySelectorAll<HTMLInputElement>("input[aria-label='Rule name']")[0];
    act(() => {
      if (before !== undefined) {
        before.value = "Wea";
        before.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    const rules = onChange.mock.calls[0]?.[0] as PolicyRule[];
    show(rules);
    expect(container.querySelectorAll<HTMLInputElement>("input[aria-label='Rule name']")[0]).toBe(before);
  });
});
