import { mdiArrowRight, mdiClose, mdiPlus } from "@mdi/js";
import { useRef } from "preact/hooks";
import type { JSX } from "preact";

import { NODE_STYLES } from "../element-styles";
import { InputField } from "./InputField";
import type { FieldContext } from "./selector-element";
import type { ConnectedElement, PolicyRule, PolicyRulesConfig, SurfacedRule } from "./types";

function Icon({ path }: { path: string }): JSX.Element {
  return (
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

function elementIcon(elementType: string): string {
  return (NODE_STYLES[elementType] ?? NODE_STYLES["unknown"])?.icon ?? "";
}

function sameNames(names: string[] | null, other: string[]): boolean {
  const left = [...(names ?? [])].sort();
  const right = [...other].sort();
  return left.length === right.length && left.every((name, index) => name === right[index]);
}

/** The element whose own price field a rule stands for, if it is one. */
function surfacedOwner(rule: PolicyRule, surfaced: SurfacedRule[]): SurfacedRule | undefined {
  return surfaced.find((pattern) => sameNames(pattern.source, rule.source) && sameNames(pattern.target, rule.target));
}

/** A blank rule named apart from the others. */
function newRule(rules: PolicyRule[]): PolicyRule {
  const names = new Set(rules.map((rule) => rule.name));
  let number = rules.length + 1;
  while (names.has(`Rule ${number}`)) {
    number += 1;
  }
  return { name: `Rule ${number}`, enabled: true, source: [], target: [], price: { type: "none" } };
}

interface EndProps {
  label: string;
  names: string[];
  options: ConnectedElement[];
  disabled: boolean;
  t: FieldContext<PolicyRulesConfig, PolicyRule[]>["t"];
  onChange: (names: string[]) => void;
}

/** One end of a rule: the elements it names as chips, or any element when it names none. */
function RuleEnd({ label, names, options, disabled, t, onChange }: EndProps): JSX.Element {
  const typeOf = (name: string): string => options.find((option) => option.name === name)?.element_type ?? "";
  const remaining = options.filter((option) => !names.includes(option.name));
  return (
    <div class="rule-end" role="group" aria-label={label}>
      <span class="rule-end-label">{label}</span>
      {names.length === 0 && <span class="bus-element rule-any">{t("policy_rules.options.any")}</span>}
      {names.map((name) => (
        <span key={name} class="chip">
          <span class="chip-body">
            <span aria-hidden="true">{elementIcon(typeOf(name))}</span>
            <span class="entity-name">{name}</span>
          </span>
          <button
            type="button"
            class="chip-remove"
            disabled={disabled}
            aria-label={t("input.options.remove", { name })}
            onClick={() => onChange(names.filter((other) => other !== name))}
          >
            <Icon path={mdiClose} />
          </button>
        </span>
      ))}
      {remaining.length > 0 && (
        <select
          class="rule-add-end"
          disabled={disabled}
          aria-label={t("policy_rules.options.add_endpoint", { end: label })}
          value=""
          onChange={(event) => {
            const name = event.currentTarget.value;
            if (name !== "") {
              onChange([...names, name]);
            }
          }}
        >
          <option value="">+</option>
          {remaining.map((option) => (
            <option key={option.name} value={option.name}>
              {elementIcon(option.element_type)} {option.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

/**
 * Every policy rule as a card: whether it is on, its name, the elements its power
 * comes from and goes to (any element when an end names none), and its price.
 * A rule an element's own price field stands for is marked with that element.
 */
export function PolicyRulesField(props: FieldContext<PolicyRulesConfig, PolicyRule[]>): JSX.Element {
  const { config, value, hass, label, helper, required, disabled, t, onChange } = props;
  const rules = value ?? [];

  // Each rule's card keeps its own key, so a card's open search stays with its rule when another is removed
  const nextKey = useRef(0);
  const newKey = (): number => (nextKey.current += 1);
  const keys = useRef<number[]>([]);
  if (keys.current.length !== rules.length) {
    keys.current = rules.map(() => newKey());
  }
  const cardKeys = keys.current;

  const update = (index: number, change: Partial<PolicyRule>): void => {
    onChange(rules.map((rule, at) => (at === index ? { ...rule, ...change } : rule)));
  };

  return (
    <div class={`field${disabled ? " disabled" : ""}`}>
      <div class="label">
        {label}
        {required ? " *" : ""}
      </div>
      {rules.map((rule, index) => {
        const owner = surfacedOwner(rule, config.surfaced);
        return (
          <div key={cardKeys[index]} class="rule">
            <div class="rule-head">
              <button
                type="button"
                role="switch"
                class={`rule-switch${rule.enabled ? " on" : ""}`}
                aria-checked={rule.enabled}
                aria-label={t("policy_rules.options.enabled", { rule: rule.name })}
                disabled={disabled}
                onClick={() => update(index, { enabled: !rule.enabled })}
              />
              <input
                type="text"
                class="rule-name"
                aria-label={t("policy_rules.options.rule_name")}
                disabled={disabled}
                value={rule.name}
                onInput={(event) => update(index, { name: event.currentTarget.value })}
              />
              {owner !== undefined && (
                <span class="bus-element rule-owner">
                  <span aria-hidden="true">{elementIcon(owner.owner_type)}</span>
                  {owner.owner}
                </span>
              )}
              <button
                type="button"
                class="path-control"
                disabled={disabled}
                aria-label={t("policy_rules.options.remove_rule", { rule: rule.name })}
                onClick={() => {
                  keys.current = cardKeys.filter((_, at) => at !== index);
                  onChange(rules.filter((_, at) => at !== index));
                }}
              >
                <Icon path={mdiClose} />
              </button>
            </div>
            <div class="rule-ends">
              <RuleEnd
                label={t("policy_rules.options.from")}
                names={rule.source}
                options={config.sources}
                disabled={disabled}
                t={t}
                onChange={(source) => update(index, { source })}
              />
              <span class="rule-arrow" aria-hidden="true">
                <Icon path={mdiArrowRight} />
              </span>
              <RuleEnd
                label={t("policy_rules.options.to")}
                names={rule.target}
                options={config.targets}
                disabled={disabled}
                t={t}
                onChange={(target) => update(index, { target })}
              />
            </div>
            <InputField
              config={config.price}
              value={rule.price}
              hass={hass}
              label={t("policy_rules.options.price", { rule: rule.name })}
              labelHidden={true}
              required={true}
              disabled={disabled}
              t={t}
              onChange={(price) => update(index, { price })}
            />
          </div>
        );
      })}
      <button
        type="button"
        class="path-kind rule-add"
        disabled={disabled}
        onClick={() => {
          keys.current = [...cardKeys, newKey()];
          onChange([...rules, newRule(rules)]);
        }}
      >
        <Icon path={mdiPlus} />
        {t("policy_rules.options.add_rule")}
      </button>
      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
