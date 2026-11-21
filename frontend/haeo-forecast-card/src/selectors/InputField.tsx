import { mdiChartLine, mdiClose, mdiMagnify, mdiPlus } from "@mdi/js";
import { useMemo, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import { describeEntity, filterOptions, offeredEntityIds } from "./search";
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

let idCounter = 0;

function Icon({ path }: { path: string }): JSX.Element {
  return (
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  );
}

function selectedEntities(value: InputValue | undefined): string[] {
  return value?.type === "entity" ? value.value : [];
}

/**
 * An entity value listing the given entities.
 *
 * The words that mean on and off belong to the entities they were read from,
 * so they are dropped when the entities change and the flow asks for them again.
 */
function entityValue(entityIds: string[]): InputValue {
  return { type: "entity", value: entityIds };
}

/**
 * One HAEO input: a fixed value, one or more entities, or nothing.
 *
 * The controls show what the field takes: a number box (or a switch) for a
 * fixed value, a button opening a checklist of entities, and the chosen
 * entities with their current values. An empty number box is a field left unset.
 */
export function InputField(props: InputFieldProps): JSX.Element {
  const { config, value, hass, label, helper, required, disabled, t, onChange } = props;
  const [query, setQuery] = useState("");
  const [picking, setPicking] = useState(false);
  const [ids] = useState(() => {
    idCounter += 1;
    return { label: `haeo-input-label-${idCounter}`, list: `haeo-input-list-${idCounter}` };
  });
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);

  const allowsEntity = config.kinds.includes("entity");
  const allowsConstant = config.kinds.includes("constant");
  const allowsNone = config.kinds.includes("none");
  const empty: InputValue = allowsNone ? { type: "none" } : entityValue([]);
  const selected = selectedEntities(value);
  const showsEntities = selected.length > 0;
  // A field taking only entities shows its search in place of a value box
  const searchInline = allowsEntity && !allowsConstant && !showsEntities;

  // Sorting is the slow part, and Home Assistant replaces hass on every state change, so the
  // order is kept until the field's config changes; current states are read fresh below.
  const hasHass = hass !== null;
  const offeredIds = useMemo(() => offeredEntityIds(hass, config), [config, hasHass]);
  const matches = useMemo(
    () =>
      filterOptions(
        offeredIds.map((entityId) => describeEntity(hass, entityId)),
        query
      ),
    [offeredIds, hass, query]
  );
  const unselectedMatches = matches.filter((option) => !selected.includes(option.entityId));

  const openPicker = (): void => {
    setPicking(true);
    requestAnimationFrame(() => search.current?.focus());
  };

  const closePicker = (): void => {
    setPicking(false);
    setQuery("");
  };

  const toggle = (entityId: string): void => {
    const next = selected.includes(entityId) ? selected.filter((id) => id !== entityId) : [...selected, entityId];
    onChange(next.length === 0 ? empty : entityValue(next));
  };

  const toggleAll = (): void => {
    if (unselectedMatches.length > 0) {
      onChange(entityValue([...selected, ...unselectedMatches.map((option) => option.entityId)]));
      return;
    }
    const shown = new Set(matches.map((option) => option.entityId));
    const next = selected.filter((id) => !shown.has(id));
    onChange(next.length === 0 ? empty : entityValue(next));
  };

  const onFocusOut = (event: FocusEvent): void => {
    if (!(event.relatedTarget instanceof Node && root.current?.contains(event.relatedTarget) === true)) {
      closePicker();
    }
  };

  const onSearchKeyDown = (event: KeyboardEvent): void => {
    if (event.key === "Escape" && picking) {
      event.preventDefault();
      event.stopPropagation();
      closePicker();
    } else if (event.key === "Enter") {
      // Choosing must not also submit the form around the field
      event.preventDefault();
      event.stopPropagation();
      const first = matches[0];
      if (first !== undefined) {
        toggle(first.entityId);
      }
    }
  };

  const allChecked = matches.length > 0 && unselectedMatches.length === 0;

  const searchBox = (
    <label class={`search${searchInline ? " inline" : ""}`}>
      <Icon path={mdiMagnify} />
      <input
        ref={search}
        type="text"
        role="combobox"
        aria-label={t("input.options.search", { label })}
        aria-expanded={picking}
        aria-controls={ids.list}
        autocomplete="off"
        disabled={disabled}
        value={query}
        onFocus={() => setPicking(true)}
        onInput={(event) => setQuery(event.currentTarget.value)}
        onKeyDown={onSearchKeyDown}
      />
    </label>
  );

  return (
    <div class={`field${disabled ? " disabled" : ""}`} ref={root} onFocusOut={onFocusOut}>
      <div class="label" id={ids.label}>
        {label}
        {required ? " *" : ""}
      </div>

      {showsEntities && (
        <ul class="entities" aria-label={t("input.options.selected", { label })}>
          {selected.map((entityId) => {
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
                  onClick={() => toggle(entityId)}
                >
                  <Icon path={mdiClose} />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div class="row">
        {!showsEntities && allowsConstant && config.value_type === "number" && (
          <label class="number">
            <input
              type="number"
              aria-labelledby={ids.label}
              disabled={disabled}
              value={value?.type === "constant" ? String(value.value) : ""}
              {...(config.min !== undefined ? { min: config.min } : {})}
              {...(config.max !== undefined ? { max: config.max } : {})}
              step={config.step ?? "any"}
              onInput={(event) => {
                // A box mid-edit can read empty (a lone "-"); the box stays, so the next keystroke lands
                const text = event.currentTarget.value;
                const number = Number(text);
                if (text === "") {
                  onChange(empty);
                } else if (Number.isFinite(number)) {
                  onChange({ type: "constant", value: number });
                }
              }}
            />
            {config.unit !== undefined && config.unit !== "" && <span class="unit">{config.unit}</span>}
          </label>
        )}

        {!showsEntities && allowsConstant && config.value_type === "boolean" && (
          <button
            type="button"
            role="switch"
            class={`switch${value?.type === "constant" ? "" : " unset"}`}
            aria-checked={value?.type === "constant" && value.value === true}
            aria-labelledby={ids.label}
            disabled={disabled}
            onClick={() => onChange({ type: "constant", value: !(value?.type === "constant" && value.value === true) })}
          >
            <span class="knob" />
          </button>
        )}

        {searchInline && searchBox}

        {allowsEntity && !searchInline && (
          <button
            type="button"
            class={`icon-button pick${picking ? " active" : ""}`}
            disabled={disabled}
            aria-label={t(showsEntities ? "input.options.add_entities" : "input.options.choose_entities", { label })}
            aria-expanded={picking}
            aria-controls={ids.list}
            onClick={() => (picking ? closePicker() : openPicker())}
          >
            <Icon path={showsEntities ? mdiPlus : mdiChartLine} />
          </button>
        )}

        {allowsNone && value?.type === "constant" && (
          <button
            type="button"
            class="icon-button"
            disabled={disabled}
            aria-label={t("input.options.clear", { label })}
            onClick={() => onChange({ type: "none" })}
          >
            <Icon path={mdiClose} />
          </button>
        )}
      </div>

      {picking && (
        <div class="picker">
          {!searchInline && searchBox}
          <ul class="options" id={ids.list} role="listbox" aria-multiselectable={true}>
            {matches.length > 1 && (
              <li
                role="option"
                class="option all"
                aria-selected={allChecked}
                aria-label={t("input.options.select_all", { count: String(matches.length) })}
                onMouseDown={(event) => event.preventDefault()}
                onClick={toggleAll}
              >
                <input type="checkbox" tabIndex={-1} checked={allChecked} aria-hidden="true" readOnly />
                <span class="count">{matches.length}</span>
              </li>
            )}
            {matches.slice(0, MAX_OPTIONS).map((option) => {
              const checked = selected.includes(option.entityId);
              return (
                <li
                  key={option.entityId}
                  role="option"
                  class="option"
                  aria-selected={checked}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => toggle(option.entityId)}
                >
                  <input type="checkbox" tabIndex={-1} checked={checked} aria-hidden="true" readOnly />
                  <span class="option-text">
                    <span class="entity-name">{option.name}</span>
                    <span class="entity-id">{option.entityId}</span>
                  </span>
                  <span class="entity-state">{option.current}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
