import { mdiCurrentAc, mdiCurrentDc } from "@mdi/js";
import { useState } from "preact/hooks";
import type { JSX } from "preact";

import { NODE_STYLES } from "../element-styles";
import type { FieldContext } from "./selector-element";
import type { ConnectionSelectorConfig } from "./types";

let idCounter = 0;

function elementIcon(elementType: string): string {
  return (NODE_STYLES[elementType] ?? NODE_STYLES["unknown"])?.icon ?? "";
}

/**
 * Where an element connects: each element it can connect to is shown as a bus,
 * AC or DC, with the elements already on it, and the new element appears on
 * the chosen one. Seeing where similar equipment sits shows where this one goes.
 */
export function ConnectionField(props: FieldContext<ConnectionSelectorConfig, string>): JSX.Element {
  const { config, value, label, helper, required, disabled, t, onChange } = props;
  const [labelId] = useState(() => {
    idCounter += 1;
    return `haeo-connection-label-${idCounter}`;
  });
  const targets = config.targets;
  const selectedIndex = targets.findIndex((target) => target.name === value);

  const onKeyDown = (event: KeyboardEvent): void => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (step === undefined || targets.length === 0) {
      return;
    }
    event.preventDefault();
    const next = targets[(Math.max(selectedIndex, 0) + step + targets.length) % targets.length];
    if (next !== undefined) {
      onChange(next.name);
      const root = (event.currentTarget as HTMLElement).querySelectorAll<HTMLElement>("[role=radio]");
      root[targets.indexOf(next)]?.focus();
    }
  };

  return (
    <div class={`field${disabled ? " disabled" : ""}`}>
      <div class="label" id={labelId}>
        {label}
        {required ? " *" : ""}
      </div>
      <div class="buses" role="radiogroup" aria-labelledby={labelId} onKeyDown={onKeyDown}>
        {targets.map((target, index) => {
          const checked = index === selectedIndex;
          return (
            <button
              key={target.name}
              type="button"
              role="radio"
              class={`bus${checked ? " selected" : ""}`}
              aria-checked={checked}
              aria-label={t(target.dc ? "connection.options.dc_bus" : "connection.options.ac_bus", {
                name: target.name,
              })}
              tabIndex={checked || (selectedIndex === -1 && index === 0) ? 0 : -1}
              disabled={disabled}
              onClick={() => onChange(target.name)}
            >
              <span class="bus-head">
                <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d={target.dc ? mdiCurrentDc : mdiCurrentAc} />
                </svg>
                <span class="bus-name">{target.name}</span>
              </span>
              <span class="bus-elements">
                {target.elements.map((element) => (
                  <span class="bus-element" key={element.name}>
                    <span aria-hidden="true">{elementIcon(element.element_type)}</span>
                    {element.name}
                  </span>
                ))}
                {checked && (
                  <span class="bus-element ghost" aria-hidden="true">
                    {elementIcon(config.element_type)}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </div>
      {helper !== undefined && helper !== "" && <div class="helper">{helper}</div>}
    </div>
  );
}
