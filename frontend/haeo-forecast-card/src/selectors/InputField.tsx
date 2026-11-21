import { useMemo, useState } from "preact/hooks";
import type { JSX } from "preact";

import { describeEntity, entityOptions, filterOptions, parseConstant } from "./search";
import type { EntityOption } from "./search";
import type { InputSelectorConfig, InputValue, SelectorHass, Translate } from "./types";

/** The most matches the list renders; a narrower search shows the rest. */
const MAX_OPTIONS = 100;

export interface InputFieldProps {
  config: InputSelectorConfig;
  value: InputValue | undefined;
  hass: SelectorHass | null;
  label: string;
  helper?: string | undefined;
  required: boolean;
  disabled: boolean;
  t: Translate;
  onChange: (value: InputValue) => void;
}

/** A choice in the search list, either an entity or a fixed value. */
type Choice =
  | { kind: "constant"; value: number | boolean; text: string }
  | { kind: "add_all"; entityIds: string[]; text: string }
  | { kind: "entity"; option: EntityOption; selected: boolean };

let idCounter = 0;

function selectedEntities(value: InputValue | undefined): string[] {
  return value?.type === "entity" ? value.value : [];
}

/** An entity value listing the given entities, keeping any other details of the current value. */
function withEntities(value: InputValue | undefined, entityIds: string[]): InputValue {
  return value?.type === "entity" ? { ...value, value: entityIds } : { type: "entity", value: entityIds };
}

function emptyValue(config: InputSelectorConfig): InputValue {
  return config.kinds.includes("none") ? { type: "none" } : { type: "entity", value: [] };
}

/** One HAEO input: a fixed value, one or more entities, or nothing. */
export function InputField(props: InputFieldProps): JSX.Element {
  const { config, value, hass, label, helper, required, disabled, t, onChange } = props;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [ids] = useState(() => {
    idCounter += 1;
    return { label: `haeo-input-label-${idCounter}`, list: `haeo-input-list-${idCounter}` };
  });

  const allowsEntity = config.kinds.includes("entity");
  const allowsConstant = config.kinds.includes("constant");
  const allowsNone = config.kinds.includes("none");
  const selected = selectedEntities(value);
  const options = useMemo(() => entityOptions(hass, config), [hass, config]);

  const choices = useMemo((): Choice[] => {
    const result: Choice[] = [];
    const constant = parseConstant(query, config);
    if (constant !== null) {
      const shown = config.unit !== undefined && config.unit !== "" ? `${constant} ${config.unit}` : String(constant);
      result.push({ kind: "constant", value: constant, text: t("input.options.use_value", { value: shown }) });
    }
    if (allowsConstant && config.value_type === "boolean" && query.trim() === "") {
      result.push({ kind: "constant", value: true, text: t("input.options.fixed_on") });
      result.push({ kind: "constant", value: false, text: t("input.options.fixed_off") });
    }
    const matches = filterOptions(options, query);
    const unselected = matches.filter((option) => !selected.includes(option.entityId));
    if (config.multiple && query.trim() !== "" && unselected.length > 1) {
      result.push({
        kind: "add_all",
        entityIds: unselected.map((option) => option.entityId),
        text: t("input.options.add_all", { count: String(unselected.length) }),
      });
    }
    for (const option of matches.slice(0, MAX_OPTIONS)) {
      result.push({ kind: "entity", option, selected: selected.includes(option.entityId) });
    }
    return result;
  }, [query, config, options, selected, allowsConstant, t]);

  const choose = (choice: Choice): void => {
    switch (choice.kind) {
      case "constant":
        onChange({ type: "constant", value: choice.value });
        setQuery("");
        setOpen(false);
        return;
      case "add_all":
        onChange(withEntities(value, [...selected, ...choice.entityIds]));
        return;
      case "entity": {
        const id = choice.option.entityId;
        if (!config.multiple) {
          onChange(withEntities(value, [id]));
          setQuery("");
          setOpen(false);
          return;
        }
        const next = choice.selected ? selected.filter((entityId) => entityId !== id) : [...selected, id];
        onChange(next.length === 0 ? emptyValue(config) : withEntities(value, next));
        return;
      }
    }
  };

  const removeEntity = (entityId: string): void => {
    const next = selected.filter((id) => id !== entityId);
    onChange(next.length === 0 ? emptyValue(config) : withEntities(value, next));
  };

  const onKeyDown = (event: KeyboardEvent): void => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((index) => Math.min(index + 1, Math.max(choices.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      const choice = choices[active];
      if (open && choice !== undefined) {
        // Picking a choice must not also submit the form around the field
        event.preventDefault();
        event.stopPropagation();
        choose(choice);
      }
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
    }
  };

  const fixedValueLabel = t("input.options.fixed_value");

  return (
    <div class={`field${disabled ? " disabled" : ""}`}>
      <div class="label" id={ids.label}>
        {label}
        {required ? " *" : ""}
      </div>

      {value?.type === "entity" && value.value.length > 0 && (
        <ul class="entities" aria-label={t("input.options.selected", { label })}>
          {value.value.map((entityId) => {
            const entity = describeEntity(hass, entityId);
            return (
              <li class="entity" key={entityId}>
                <span class="entity-name">{entity.name}</span>
                <span class="entity-state">{entity.current}</span>
                <button
                  type="button"
                  class="icon-button"
                  disabled={disabled}
                  aria-label={t("input.options.remove", { name: entity.name })}
                  onClick={() => removeEntity(entityId)}
                >
                  ×
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {allowsConstant && config.value_type === "number" && (value?.type === "constant" || !allowsEntity) && (
        <div class="constant">
          <input
            type="number"
            aria-label={`${label}: ${fixedValueLabel}`}
            disabled={disabled}
            value={value?.type === "constant" ? String(value.value) : ""}
            {...(config.min !== undefined ? { min: config.min } : {})}
            {...(config.max !== undefined ? { max: config.max } : {})}
            step={config.step ?? "any"}
            onInput={(event) => {
              const text = event.currentTarget.value;
              if (text === "") {
                onChange(emptyValue(config));
                return;
              }
              const number = Number(text);
              if (Number.isFinite(number)) {
                onChange({ type: "constant", value: number });
              }
            }}
          />
          {config.unit !== undefined && config.unit !== "" && <span class="unit">{config.unit}</span>}
        </div>
      )}

      {allowsConstant && config.value_type === "boolean" && value?.type === "constant" && (
        <div class="constant">
          <button
            type="button"
            role="switch"
            class="switch"
            aria-checked={value.value === true}
            aria-label={`${label}: ${fixedValueLabel}`}
            disabled={disabled}
            onClick={() => onChange({ type: "constant", value: value.value !== true })}
          >
            {value.value === true ? t("input.options.on") : t("input.options.off")}
          </button>
        </div>
      )}

      {(value === undefined || value.type === "none" || (value.type === "entity" && value.value.length === 0)) &&
        allowsEntity && <div class="empty">{t("input.options.not_set")}</div>}

      {allowsNone && value !== undefined && value.type !== "none" && (
        <button type="button" class="text-button" disabled={disabled} onClick={() => onChange({ type: "none" })}>
          {t("input.options.clear")}
        </button>
      )}

      {allowsEntity && (
        <div class="search">
          <input
            type="text"
            role="combobox"
            aria-labelledby={ids.label}
            aria-expanded={open}
            aria-controls={ids.list}
            aria-autocomplete="list"
            autocomplete="off"
            disabled={disabled}
            placeholder={
              allowsConstant && config.value_type === "number"
                ? t("input.options.search_or_value")
                : t("input.options.search")
            }
            value={query}
            onFocus={() => setOpen(true)}
            onBlur={() => {
              setOpen(false);
              setQuery("");
            }}
            onInput={(event) => {
              setQuery(event.currentTarget.value);
              setActive(0);
              setOpen(true);
            }}
            onKeyDown={onKeyDown}
          />
          {open && query.trim() === "" && (
            <div class="hint">
              {allowsConstant && config.value_type === "number" && <div>{t("input.options.hint_value")}</div>}
              {config.multiple && <div>{t("input.options.hint_add_all")}</div>}
            </div>
          )}
          {open && (
            <ul class="options" id={ids.list} role="listbox" aria-multiselectable={config.multiple}>
              {choices.length === 0 && <li class="no-matches">{t("input.options.no_matches")}</li>}
              {choices.map((choice, index) => (
                <li
                  key={choice.kind === "entity" ? choice.option.entityId : `${choice.kind}-${index}`}
                  role="option"
                  class={`option${index === active ? " active" : ""}${choice.kind === "entity" ? "" : " action"}`}
                  aria-selected={choice.kind === "entity" ? choice.selected : false}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(choice)}
                >
                  {choice.kind === "entity" ? (
                    <>
                      <span class="check">{choice.selected ? "✓" : ""}</span>
                      <span class="option-text">
                        <span class="entity-name">{choice.option.name}</span>
                        <span class="entity-id">{choice.option.entityId}</span>
                      </span>
                      <span class="entity-state">{choice.option.current}</span>
                    </>
                  ) : (
                    <span class="option-text">{choice.text}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
