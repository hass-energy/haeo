import { render } from "preact";
import type { JSX } from "preact";

import { SELECTOR_STYLES } from "./styles";
import type { SelectorHass, Translate } from "./types";

/** Where the integration's selector strings live in Home Assistant's translations. */
const TRANSLATION_PREFIX = "component.haeo.selector.";

/** What a selector element passes the field it renders. */
export interface FieldContext<Config, Value> {
  config: Config;
  value: Value | undefined;
  hass: SelectorHass | null;
  label: string;
  helper: string | undefined;
  required: boolean;
  disabled: boolean;
  t: Translate;
  onChange: (value: Value) => void;
}

/**
 * A HAEO selector element, which Home Assistant renders for a selector of its type.
 *
 * It takes the properties `ha-selector` passes to every selector and reports a
 * change with a `value-changed` event, as Home Assistant's own selectors do.
 * Each selector renders its own field from them.
 */
export abstract class HaeoSelectorElement<Config, Value> extends HTMLElement {
  protected abstract readonly selectorType: string;
  private _hass: SelectorHass | null = null;
  private _selector: Record<string, Config> | null = null;
  private _value: Value | undefined = undefined;
  private _label = "";
  private _helper: string | undefined = undefined;
  private _required = false;
  private _disabled = false;

  set hass(hass: SelectorHass | null) {
    this._hass = hass;
    this.update();
  }
  set selector(selector: Record<string, Config> | null) {
    this._selector = selector;
    this.update();
  }
  get value(): Value | undefined {
    return this._value;
  }
  set value(value: Value | undefined) {
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

  /** Render the field for the selector's config and value. */
  protected abstract renderField(context: FieldContext<Config, Value>): JSX.Element;

  // hass.localize rather than the form's localizeValue, which older frontends call without placeholder values
  private readonly localizeKey: Translate = (key, values) => {
    const text = this._hass?.localize(`${TRANSLATION_PREFIX}${key}`, values) ?? "";
    return text === "" ? key : text;
  };

  private readonly onChange = (value: Value): void => {
    this._value = value;
    this.update();
    this.dispatchEvent(new CustomEvent("value-changed", { detail: { value }, bubbles: true, composed: true }));
  };

  private update(): void {
    const config = this._selector?.[this.selectorType];
    if (!this.isConnected || config === undefined) {
      return;
    }
    const root = this.shadowRoot ?? this.attachShadow({ mode: "open" });
    render(
      <>
        <style>{SELECTOR_STYLES}</style>
        {this.renderField({
          config,
          value: this._value,
          hass: this._hass,
          label: this._label,
          helper: this._helper,
          required: this._required,
          disabled: this._disabled,
          t: this.localizeKey,
          onChange: this.onChange,
        })}
      </>,
      root
    );
  }
}
