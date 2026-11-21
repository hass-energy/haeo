import type { JSX } from "preact";

import { InputField } from "./InputField";
import { HaeoSelectorElement } from "./selector-element";
import type { FieldContext } from "./selector-element";
import type { InputSelectorConfig, InputValue } from "./types";

/** The selector key the integration's `InputSelector` serializes under. */
export const INPUT_SELECTOR_TYPE = "haeo_input";

/** Home Assistant renders a selector of type `haeo_input` as this element. */
export class HaeoInputSelector extends HaeoSelectorElement<InputSelectorConfig, InputValue> {
  protected readonly selectorType = INPUT_SELECTOR_TYPE;

  protected renderField(context: FieldContext<InputSelectorConfig, InputValue>): JSX.Element {
    return <InputField {...context} />;
  }
}
