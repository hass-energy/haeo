import {
  mdiChartLine,
  mdiClose,
  mdiGauge,
  mdiMagnify,
  mdiNumeric,
  mdiToggleSwitch,
  mdiToggleSwitchOffOutline,
} from "@mdi/js";
import { useMemo, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import { describeEntity, filterOptions, offeredEntityIds, readNumber } from "./search";
import { Sparkline } from "./Sparkline";
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

/** A row of the list: a fixed value, or an entity. */
type Choice =
  | { kind: "constant"; value: number | boolean; allowed: boolean }
  | { kind: "entity"; option: EntityOption; selected: boolean };

let idCounter = 0;

function Icon({ path, label }: { path: string; label?: string }): JSX.Element {
  return label === undefined ? (
    <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={path} />
    </svg>
  ) : (
    <svg class="icon" viewBox="0 0 24 24" role="img" aria-label={label}>
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
 * The field is a token input. Typing filters the entities the field offers, and a
 * typed number is offered as a fixed value above them. A chosen value becomes a
 * chip: a fixed value shows its unit, an entity read as a forecast a sparkline of
 * it, and an entity read as its current value a gauge and that value, so how each
 * loads is visible without words.
 */
export function InputField(props: InputFieldProps): JSX.Element {
  const { config, value, hass, label, helper, required, disabled, t, onChange } = props;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [ids] = useState(() => {
    idCounter += 1;
    return { label: `haeo-input-label-${idCounter}`, list: `haeo-input-list-${idCounter}` };
  });
  const input = useRef<HTMLInputElement>(null);

  const allowsEntity = config.kinds.includes("entity");
  const allowsConstant = config.kinds.includes("constant");
  const empty: InputValue = config.kinds.includes("none") ? { type: "none" } : entityValue([]);
  const selected = selectedEntities(value);

  // Sorting is the slow part, and Home Assistant replaces hass on every state change, so the
  // order is kept until the field's config changes; current states are read fresh below.
  const hasHass = hass !== null;
  const offeredIds = useMemo(() => (allowsEntity ? offeredEntityIds(hass, config) : []), [config, hasHass]);
  const matches = useMemo(
    () =>
      filterOptions(
        offeredIds.map((entityId) => describeEntity(hass, entityId)),
        query
      ),
    [offeredIds, hass, query]
  );

  const choices = useMemo((): Choice[] => {
    const result: Choice[] = [];
    const typed = readNumber(query, config);
    if (typed !== null) {
      result.push({ kind: "constant", value: typed.value, allowed: typed.allowed });
    }
    if (allowsConstant && config.value_type === "boolean" && query.trim() === "") {
      result.push({ kind: "constant", value: true, allowed: true }, { kind: "constant", value: false, allowed: true });
    }
    for (const option of matches.slice(0, MAX_OPTIONS)) {
      result.push({ kind: "entity", option, selected: selected.includes(option.entityId) });
    }
    return result;
  }, [query, config, matches, value, allowsConstant]);

  const unselectedMatches = matches.filter((option) => !selected.includes(option.entityId));
  const allChecked = matches.length > 0 && unselectedMatches.length === 0;

  const constantText = (constant: number | boolean): string => {
    if (typeof constant === "boolean") {
      return constant ? t("input.options.on") : t("input.options.off");
    }
    return config.unit !== undefined && config.unit !== "" ? `${constant} ${config.unit}` : String(constant);
  };

  // How the field reads an entity: its forecast, drawn when there is a preview, or its current value, which is shown
  const preview = (entity: EntityOption): number[] | undefined => config.forecasts[entity.entityId];
  const entityKindIcon = (entity: EntityOption): JSX.Element => {
    const values = preview(entity);
    if (values === undefined) {
      return <Icon path={mdiGauge} label={t("input.options.current_value")} />;
    }
    return values.length > 1 ? (
      <Sparkline values={values} label={t("input.options.forecast")} />
    ) : (
      <Icon path={mdiChartLine} label={t("input.options.forecast")} />
    );
  };
  const entityState = (entity: EntityOption): string => (preview(entity) === undefined ? entity.current : "");

  const constantIcon = (constant: number | boolean): string => {
    if (typeof constant === "boolean") {
      return constant ? mdiToggleSwitch : mdiToggleSwitchOffOutline;
    }
    return mdiNumeric;
  };

  // Like an address field, a pick clears the search and closes the list until the next one
  const finishPick = (): void => {
    setQuery("");
    setOpen(false);
  };

  const choose = (choice: Choice): void => {
    if (choice.kind === "constant") {
      if (!choice.allowed) {
        return;
      }
      onChange({ type: "constant", value: choice.value });
      finishPick();
      return;
    }
    const id = choice.option.entityId;
    const next = choice.selected ? selected.filter((entityId) => entityId !== id) : [...selected, id];
    onChange(next.length === 0 ? empty : entityValue(next));
    finishPick();
  };

  const toggleAll = (): void => {
    if (unselectedMatches.length > 0) {
      onChange(entityValue([...selected, ...unselectedMatches.map((option) => option.entityId)]));
    } else {
      const shown = new Set(matches.map((option) => option.entityId));
      const next = selected.filter((entityId) => !shown.has(entityId));
      onChange(next.length === 0 ? empty : entityValue(next));
    }
    finishPick();
  };

  const removeEntity = (entityId: string): void => {
    const next = selected.filter((id) => id !== entityId);
    onChange(next.length === 0 ? empty : entityValue(next));
  };

  // A fixed value's chip goes back into the input to be changed
  const editConstant = (constant: number | boolean): void => {
    onChange(empty);
    if (typeof constant === "number") {
      setQuery(String(constant));
    }
    setOpen(true);
    input.current?.focus();
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
      // Choosing must not also submit the form around the field
      event.preventDefault();
      event.stopPropagation();
      const choice = choices[active];
      if (choice !== undefined) {
        choose(choice);
      }
    } else if (event.key === "Escape" && open) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
    } else if (event.key === "Backspace" && query === "" && value !== undefined && value.type !== "none") {
      const last = selected.at(-1);
      if (last !== undefined) {
        removeEntity(last);
      } else if (value.type === "constant") {
        onChange(empty);
      }
    }
  };

  return (
    <div class={`field${disabled ? " disabled" : ""}`}>
      <div class="label" id={ids.label}>
        {label}
        {required ? " *" : ""}
      </div>

      <div class="tokens" onClick={() => input.current?.focus()}>
        {/* The field is also the search over the entities it offers */}
        {allowsEntity && <Icon path={mdiMagnify} />}
        {value?.type === "constant" && (
          <span class="chip constant">
            <button
              type="button"
              class="chip-body"
              disabled={disabled}
              aria-label={t("input.options.fixed_value", { value: constantText(value.value) })}
              onClick={() => editConstant(value.value)}
            >
              <Icon path={constantIcon(value.value)} />
              <span>{constantText(value.value)}</span>
            </button>
            <button
              type="button"
              class="chip-remove"
              disabled={disabled}
              aria-label={t("input.options.remove", { name: constantText(value.value) })}
              onClick={() => onChange(empty)}
            >
              <Icon path={mdiClose} />
            </button>
          </span>
        )}
        {selected.map((entityId) => {
          const entity = describeEntity(hass, entityId);
          return (
            <span class="chip entity" key={entityId}>
              <span class="chip-body">
                {entityKindIcon(entity)}
                <span class="entity-name">{entity.name}</span>
                {entityState(entity) !== "" && <span class="entity-state">{entityState(entity)}</span>}
              </span>
              <button
                type="button"
                class="chip-remove"
                disabled={disabled}
                aria-label={t("input.options.remove", { name: entity.name })}
                onClick={() => removeEntity(entityId)}
              >
                <Icon path={mdiClose} />
              </button>
            </span>
          );
        })}
        <input
          ref={input}
          type="text"
          role="combobox"
          inputMode={allowsConstant && config.value_type === "number" && !allowsEntity ? "decimal" : "text"}
          aria-label={t(allowsEntity ? "input.options.search" : "input.options.enter_value", { label })}
          aria-expanded={open}
          aria-controls={ids.list}
          aria-autocomplete="list"
          autocomplete="off"
          disabled={disabled}
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
      </div>

      {open && choices.length > 0 && (
        <ul class="options" id={ids.list} role="listbox" aria-multiselectable={true}>
          {choices.map((choice, index) =>
            choice.kind !== "constant" ? null : (
              <li
                key={`constant-${String(choice.value)}`}
                role="option"
                class={`option constant${index === active ? " active" : ""}`}
                aria-selected={false}
                aria-disabled={!choice.allowed}
                aria-label={t("input.options.fixed_value", { value: constantText(choice.value) })}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(choice)}
              >
                <Icon path={constantIcon(choice.value)} />
                <span class="option-text">{constantText(choice.value)}</span>
              </li>
            )
          )}
          {allowsEntity && matches.length > 1 && (
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
          {choices.map((choice, index) =>
            choice.kind !== "entity" ? null : (
              <li
                key={choice.option.entityId}
                role="option"
                class={`option${index === active ? " active" : ""}`}
                aria-selected={choice.selected}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(choice)}
              >
                <input type="checkbox" tabIndex={-1} checked={choice.selected} aria-hidden="true" readOnly />
                {entityKindIcon(choice.option)}
                <span class="option-text">
                  <span class="entity-name">{choice.option.name}</span>
                  <span class="entity-id">{choice.option.entityId}</span>
                </span>
                <span class="entity-state">{entityState(choice.option)}</span>
              </li>
            )
          )}
        </ul>
      )}

      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
