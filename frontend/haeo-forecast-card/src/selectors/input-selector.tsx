import { render } from "preact";

import { InputField } from "./InputField";
import { SELECTOR_STYLES } from "./styles";
import type { InputSelectorConfig, InputValue, SelectorHass, Translate } from "./types";

/** The selector key the integration's `InputSelector` serializes under. */
export const INPUT_SELECTOR_TYPE = "haeo_input";

/** Where the integration's selector strings live in Home Assistant's translations. */
const TRANSLATION_PREFIX = "component.haeo.selector.";

/**
 * Home Assistant renders a selector of type `haeo_input` as this element.
 *
 * It takes the properties `ha-selector` passes to every selector and reports a
 * change with a `value-changed` event, as Home Assistant's own selectors do.
 */
export class HaeoInputSelector extends HTMLElement {
  private _hass: SelectorHass | null = null;
  private _selector: Record<string, InputSelectorConfig> | null = null;
  private _value: InputValue | undefined = undefined;
  private _label = "";
  private _helper: string | undefined = undefined;
  private _required = false;
  private _disabled = false;

  set hass(hass: SelectorHass | null) {
    this._hass = hass;
    this.update();
  }
  set selector(selector: Record<string, InputSelectorConfig> | null) {
    this._selector = selector;
    this.update();
  }
  get value(): InputValue | undefined {
    return this._value;
  }
  set value(value: InputValue | undefined) {
    this._value = value;
    this.update();
  }
  set label(label: string | undefined) {
    this._label = label ?? "";
    this.update();
  }
  set helper(helper: string | undefined) {
    this._helper = helper;
    this.update();
  }
  set required(required: boolean) {
    this._required = required;
    this.update();
  }
  set disabled(disabled: boolean) {
    this._disabled = disabled;
    this.update();
  }
  connectedCallback(): void {
    this.update();
  }

  // hass.localize rather than the form's localizeValue, which older frontends call without placeholder values
  private readonly localizeKey: Translate = (key, values) => {
    const text = this._hass?.localize(`${TRANSLATION_PREFIX}${key}`, values) ?? "";
    return text === "" ? key : text;
  };

  private readonly onChange = (value: InputValue): void => {
    this._value = value;
    this.update();
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value }, bubbles: true, composed: true }));
  };

  private update(): void {
    const config = this._selector?.[INPUT_SELECTOR_TYPE];
    if (!this.isConnected || config === undefined) {
      return;
    }
    const root = this.shadowRoot ?? this.attachShadow({ mode: "open" });
    render(
      <>
        <style>{SELECTOR_STYLES}</style>
        <InputField
          config={config}
          value={this._value}
          hass={this._hass}
          label={this._label}
          helper={this._helper}
          required={this._required}
          disabled={this._disabled}
          t={this.localizeKey}
          onChange={this.onChange}
        />
      </>,
      root
    );
  }
}
